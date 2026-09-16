import io
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import cast

import pytest

from ai_dev_doctor.core.config import ConfigError, load_config, parse_config
from ai_dev_doctor.core.engine import Check, Context, Registry
from ai_dev_doctor.core.logging import write_event
from ai_dev_doctor.core.redaction import MASK, Redactor
from ai_dev_doctor.diagnostics.builtin import registry
from ai_dev_doctor.models import CheckResult, Status, exit_code
from ai_dev_doctor.reporting import render_html, render_json, render_terminal


def test_model_contract() -> None:
    result = CheckResult("demo", "Demo", "system", Status.PASS, "OK")
    with pytest.raises(FrozenInstanceError):
        result.__setattr__("summary", "changed")
    with pytest.raises(ValueError):
        replace(result, id="not valid")
    with pytest.raises(ValueError):
        replace(result, summary="")
    assert exit_code((result,)) == 0
    assert exit_code((replace(result, status=Status.FAIL),)) == 1


@pytest.mark.parametrize(
    "source",
    [
        b"network_timeout = 0",
        b"network_timeout = nan",
        b"command_timeout = true",
        b"network_timeout = 31",
        b"verbose = 'true'",
        b"enabled_categories = ['unknown']",
        b"disabled_checks = 'a'",
        b"report_redaction = false",
        b"network = true",
        b"bad = [",
        b"\xff",
        pytest.param(b"a" * 65537, id="oversized"),
    ],
)
def test_invalid_config(source: bytes) -> None:
    with pytest.raises(ConfigError):
        parse_config(source)


def test_config_loading(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    assert load_config(path).network_timeout == 4
    with pytest.raises(ConfigError):
        load_config(path, required=True)
    path.write_text('network_timeout = 2\nenabled_categories = ["system"]', encoding="utf-8")
    assert load_config(path).enabled_categories == ("system",)


def test_registry_isolates_exception_and_identity(context: Context) -> None:
    def broken(ctx: Context) -> CheckResult:
        raise RuntimeError("password=should-never-leak")

    first = Check("broken", "Broken", "system", "fixture", broken)
    second = registry().get("windows-system")
    results = Registry((first, second)).run(context)
    assert [r.status for r in results] == [Status.ERROR, Status.INFO]
    assert "should-never-leak" not in str(results)
    invalid = replace(first, run=lambda _: second.result(Status.PASS, "bad identity"))
    assert Registry((invalid,)).run(context)[0].status == Status.ERROR
    with pytest.raises(ValueError):
        Registry((second, second))


def test_selection_and_consent(context: Context) -> None:
    checks = registry()
    network = checks.run(context, "network")
    assert len(network) == 9
    assert [r.status for r in network[-3:]] == [Status.SKIPPED] * 3
    assert checks.run(replace(context, config=replace(context.config, enabled_categories=()))) == ()
    cfg = replace(context.config, disabled_checks=("git-version",))
    assert checks.run(replace(context, config=cfg), "developer-tools")[0].status == Status.SKIPPED
    with pytest.raises(ConfigError):
        checks.run(replace(context, config=replace(cfg, disabled_checks=("typo",))))


@pytest.mark.parametrize(
    "text,secret",
    [
        ("OPENAI_API_KEY=abc-secret-value", "abc-secret-value"),
        ("GITHUB_TOKEN=ghp_123456789", "ghp_123456789"),
        ("Authorization: Bearer sensitive-token", "sensitive-token"),
        ('password="two words"', "two words"),
        ("passwd='private text'", "private text"),
        ("Cookie: SID=private-cookie; next=ignored", "private-cookie"),
        ("Cookie: SID=first; other=second-private-cookie", "second-private-cookie"),
        ("Set-Cookie: account=private-account; Secure", "private-account"),
        ("https://name:private-pass@proxy.example:8080", "private-pass"),
        ("https://example.com/?custom=private-query", "private-query"),
        ("mail person@example.com", "person@example.com"),
        ("token=\x1b[31mcolored-secret\x1b[0m", "colored-secret"),
    ],
)
def test_secret_corpus_all_outputs(text: str, secret: str) -> None:
    redactor = Redactor()
    result = CheckResult(
        "privacy",
        text,
        "system",
        Status.INFO,
        text,
        details=(text,),
        evidence=(("detail", text),),
        recommendations=(text,),
    )
    for output in (
        render_json((result,), redactor),
        render_html((result,), redactor),
        render_terminal((result,), redactor, verbose=True),
    ):
        assert secret not in output
    log = io.StringIO()
    write_event(log, redactor, "test", detail=text)
    assert secret not in log.getvalue()


def test_recursive_redaction() -> None:
    redact = Redactor.from_environment({"PRIVATE_TOKEN": "opaque-canary"}, r"C:\Users\Person")
    cleaned = redact.clean(
        {
            "nested": [{"apiKey": "anything", "text": "opaque-canary"}],
            "path": r"C:\Users\Person\config",
        }
    )
    assert "anything" not in str(cleaned)
    assert "opaque-canary" not in str(cleaned)
    assert "Person" not in str(cleaned)
    assert MASK in str(cleaned)


def test_report_contract_and_html_escaping(context: Context) -> None:
    results = registry().run(context)
    doc = json.loads(render_json(results, Redactor()))
    assert doc["schema_version"] == 1
    assert doc["version"] == "0.1.0.dev0"
    assert doc["timestamp"].endswith("+00:00")
    assert sum(doc["summary"].values()) == len(results)
    hostile = replace(results[0], summary='<script>alert("bad")</script>')
    output = render_html((hostile,), Redactor())
    assert "<script>" not in output
    assert "&lt;script&gt;" in output
    assert "default-src 'none'" in output
    assert "\x1b" not in render_terminal(results, Redactor())


def test_malformed_plugin_result_is_isolated(context: Context) -> None:
    def malformed(ctx: Context) -> CheckResult:
        return CheckResult("malformed", "Malformed", "system", Status.INFO, cast(str, 42))

    check = Check("malformed", "Malformed", "system", "fixture", malformed)
    results = Registry((check, registry().get("windows-system"))).run(context)
    assert [r.status for r in results] == [Status.ERROR, Status.INFO]
    assert json.loads(render_json(results, Redactor()))["results"][0]["status"] == "ERROR"
