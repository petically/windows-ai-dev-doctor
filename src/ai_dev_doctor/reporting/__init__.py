"""One sanitized document feeds every renderer."""

import html
import json
from collections import Counter
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

from ai_dev_doctor import __version__
from ai_dev_doctor.core.redaction import MASK, SENSITIVE, Redactor
from ai_dev_doctor.models import CheckResult


def sanitize_result(result: CheckResult, redactor: Redactor) -> CheckResult:
    """Sensitive evidence labels carry semantics, unlike ordinary free text."""
    return replace(
        result,
        name=redactor.text(result.name) or "[empty]",
        category=redactor.text(result.category) or "[empty]",
        summary=redactor.text(result.summary) or "[empty]",
        details=tuple(redactor.text(v) for v in result.details),
        evidence=tuple(
            (redactor.text(k), MASK if SENSITIVE.search(k) else redactor.text(v))
            for k, v in result.evidence
        ),
        recommendations=tuple(redactor.text(v) for v in result.recommendations),
        documentation_url=redactor.text(result.documentation_url)
        if result.documentation_url
        else None,
    )


def document(results: tuple[CheckResult, ...], redactor: Redactor) -> dict[str, object]:
    results = tuple(sanitize_result(r, redactor) for r in results)
    raw: dict[str, object] = {
        "schema_version": 1,
        "application": "Windows AI Dev Doctor",
        "version": __version__,
        "timestamp": datetime.now(UTC).isoformat(),
        "summary": dict(Counter(r.status.value for r in results)),
        "system_summary": [dict(r.evidence) for r in results if r.id == "windows-system"],
        "results": [asdict(r) for r in results],
    }
    cleaned = redactor.clean(raw)
    assert isinstance(cleaned, dict)
    return cleaned


def render_json(results: tuple[CheckResult, ...], redactor: Redactor) -> str:
    return json.dumps(document(results, redactor), ensure_ascii=True, indent=2) + "\n"


def render_terminal(
    results: tuple[CheckResult, ...],
    redactor: Redactor,
    *,
    verbose: bool = False,
    color: bool = False,
) -> str:
    results = tuple(sanitize_result(r, redactor) for r in results)
    lines = [f"Windows AI Dev Doctor {__version__}", ""]
    category = ""
    for result in results:
        if result.category != category:
            category = result.category
            lines.append(category.replace("-", " ").title())
        line = f"  [{result.status.value}] {result.name}: {result.summary}"
        # Sanitize untrusted text before adding our own terminal control codes.
        line = redactor.text(line)
        if color:
            code = {"PASS": "32", "WARNING": "33", "FAIL": "31", "ERROR": "31"}.get(
                result.status.value, "36"
            )
            line = f"\033[{code}m{line}\033[0m"
        lines.append(line)
        if verbose:
            lines.extend(redactor.text(f"    {k}: {v}") for k, v in result.evidence)
            lines.extend(redactor.text(f"    {v}") for v in result.details)
        lines.extend(redactor.text(f"    Action: {v}") for v in result.recommendations)
    counts = Counter(r.status.value for r in results)
    lines.extend(["", "Summary: " + ", ".join(f"{k}={v}" for k, v in counts.items())])
    return "\n".join(lines) + "\n"


def render_html(results: tuple[CheckResult, ...], redactor: Redactor) -> str:
    doc = document(results, redactor)
    cards = []
    clean_results = doc["results"]
    assert isinstance(clean_results, list)
    for result in clean_results:
        ev = "".join(
            f"<dt>{html.escape(k)}</dt><dd>{html.escape(v)}</dd>" for k, v in result["evidence"]
        )
        actions = "".join(f"<li>{html.escape(v)}</li>" for v in result["recommendations"])
        details = "".join(f"<p>{html.escape(v)}</p>" for v in result["details"])
        cards.append(
            f"<article><small>{html.escape(result['category'])}</small>"
            f"<h2>{html.escape(result['name'])} <span>{html.escape(result['status'])}</span></h2>"
            f"<p>{html.escape(result['summary'])}</p>{details}<dl>{ev}</dl><ul>{actions}</ul></article>"
        )
    summary = html.escape(json.dumps(doc["summary"]))
    timestamp = html.escape(str(doc["timestamp"]))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>Windows AI Dev Doctor report</title><style>
body{{margin:0;background:#eef2f6;color:#172b40;font:16px/1.6 system-ui,sans-serif}}
main{{max-width:960px;margin:auto;padding:32px 20px}}h1{{font-size:2rem;line-height:1.2}}
article{{background:white;border:1px solid #cad6e2;border-radius:12px;padding:20px;margin:16px 0}}
h2{{font-size:1.2rem;margin:4px 0}}span{{font-size:.8rem;border:1px solid #64748b;padding:3px 8px;border-radius:4px}}
small{{text-transform:uppercase;letter-spacing:.08em;color:#465b70}}dt{{font-weight:600}}dd{{margin:0 0 8px;overflow-wrap:anywhere}}
footer{{color:#465b70}}@media(max-width:500px){{main{{padding:20px 12px}}h2 span{{display:inline-block}}}}
</style></head><body><main><h1>Windows AI Dev Doctor</h1>
<p>Local diagnostic report · {__version__} · {timestamp}</p><p>{summary}</p>
{"".join(cards)}<footer>Secrets redacted. No report data was uploaded. Review before sharing.</footer>
</main></body></html>"""


def export(path: Path, content: str) -> None:
    """An explicit user-selected export may create a file, never overwrite one."""
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(content)
