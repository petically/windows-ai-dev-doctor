"""Check tracked/reviewable source for recognizable credentials and local build paths.

This deterministic check complements canary tests and manual diff review; it is not
proof that arbitrary text contains no unknown secret. Findings never print values.
"""

import os
import re
import subprocess
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
        timeout=15,
    )
    token = re.compile(
        rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{60,}|sk-[A-Za-z0-9_-]{40,})"
    )
    paths = {str(root), str(Path.home())}
    paths.update(value for key in ("USERPROFILE", "VIRTUAL_ENV") if (value := os.environ.get(key)))
    needles = {
        variant.casefold().encode("utf-8")
        for path in paths
        for variant in (path, path.replace("\\", "/"), path.replace("\\", "\\\\"))
    }
    failures = []
    count = 0
    for name in sorted(set(result.stdout.decode("utf-8").split("\0")) - {""}):
        file = root / name
        if not file.is_file():
            continue
        data = file.read_bytes()
        count += 1
        if token.search(data):
            failures.append(name + ": recognizable credential pattern")
        lowered = data.decode("utf-8", errors="replace").casefold().encode("utf-8")
        if any(needle in lowered for needle in needles):
            failures.append(name + ": local machine path")
    if failures:
        print("\n".join(failures))
        return 1
    print(
        f"Source credential/local-path scan passed ({count} files); synthetic privacy tests remain required"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
