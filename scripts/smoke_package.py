"""Smoke-test a relocated portable bundle; never print host evidence."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

NETWORK_CHECKS = {"github-auth", "network-dns", "network-tcp", "network-https"}


def main() -> None:
    source = Path(sys.argv[1]).resolve()
    expected = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]["version"]
    with tempfile.TemporaryDirectory(prefix="doctor-smoke-\u6d4b\u8bd5 ") as directory:
        root = Path(directory)
        bundle = root / "portable bundle"
        shutil.copytree(source.parent, bundle)
        executable = bundle / source.name
        config = root / "config.toml"
        config.write_text("command_timeout = 1.0\n", encoding="utf-8")
        environment = dict(os.environ)
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
        environment["OPENAI_API_KEY"] = "smoke-private-canary"

        def run(
            arguments: list[str], *, diagnostic: bool = True
        ) -> subprocess.CompletedProcess[str]:
            result = subprocess.run(
                [str(executable), *arguments],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
                timeout=90,
            )
            assert result.returncode in ((0, 1) if diagnostic else (0,))
            assert not result.stderr
            assert "smoke-private-canary" not in result.stdout
            assert str(Path.home()).casefold() not in result.stdout.casefold()
            return result

        run(["--help"], diagnostic=False)
        version = run(["version"], diagnostic=False).stdout.strip()
        assert version == expected
        run(["diagnose", "--config", str(config)])
        document = run(["diagnose", "--json", "--config", str(config)])
        report = json.loads(document.stdout)
        assert report["schema_version"] == 1 and report["version"] == version
        assert len(report["results"]) == 36
        assert all(item["status"] != "ERROR" for item in report["results"])
        assert all(
            item["status"] == "SKIPPED"
            for item in report["results"]
            if item["id"] in NETWORK_CHECKS
        )
        for extension in ("json", "html"):
            destination = root / ("report." + extension)
            run(["report", "--config", str(config), "--output", str(destination)])
            content = destination.read_text(encoding="utf-8")
            assert "smoke-private-canary" not in content
            if extension == "json":
                assert json.loads(content)["schema_version"] == 1
            else:
                assert "<!doctype html>" in content and "<script" not in content
            original = destination.read_bytes()
            refused = subprocess.run(
                [str(executable), "report", "--config", str(config), "--output", str(destination)],
                cwd=root,
                env=environment,
                capture_output=True,
                timeout=90,
            )
            assert refused.returncode == 2 and destination.read_bytes() == original
    print(
        "Relocated Unicode/spaced-path bundle: help/version/offline/JSON/HTML/privacy/no-overwrite passed"
    )


if __name__ == "__main__":
    main()
