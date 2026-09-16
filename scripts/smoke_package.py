"""Run offline smoke checks on a built executable without printing host evidence."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    executable = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix="doctor-smoke-") as directory:
        root = Path(directory)
        config = root / "config.toml"
        config.write_text("", encoding="utf-8")
        for arguments in (
            ["--help"],
            ["version"],
            ["diagnose", "--config", str(config)],
            ["diagnose", "--json", "--config", str(config)],
        ):
            result = subprocess.run(
                [str(executable), *arguments],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            if result.returncode not in (0, 1) or result.stderr:
                raise RuntimeError("Packaged CLI smoke check failed")
            if "--json" in arguments:
                report = json.loads(result.stdout)
                assert report["schema_version"] == 1
                assert len(report["results"]) == 36
                assert all(
                    r["status"] == "SKIPPED"
                    for r in report["results"]
                    if r["id"] in ("network-dns", "network-https")
                )
        for extension in ("json", "html"):
            destination = root / ("report." + extension)
            result = subprocess.run(
                [str(executable), "report", "--config", str(config), "--output", str(destination)],
                capture_output=True,
                timeout=30,
            )
            assert result.returncode in (0, 1)
            content = destination.read_text(encoding="utf-8")
            if extension == "json":
                assert json.loads(content)["schema_version"] == 1
            else:
                assert "<!doctype html>" in content and "<script" not in content
    print("Packaged help/version/diagnose/JSON/HTML smoke checks passed")


if __name__ == "__main__":
    main()
