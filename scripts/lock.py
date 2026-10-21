"""Adds sha256 hashes to the pinned requirements files, using only the standard library.

Run it after changing a pin: it keeps every `name==version` line and rewrites it with the hashes
of ALL files PyPI publishes for that version (every Python version and platform), so the same
file installs on a dev machine and in the Lambda package. Hashes come from PyPI at the moment
you run this (trust on first use); later installs are verified against them.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = ["requirements.txt", "requirements-dev.txt"]
PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;\\]+)")


def hashes_for(name, version):
    normalized = re.sub(r"[-_.]+", "-", name).lower()
    url = f"https://pypi.org/pypi/{normalized}/{version}/json"
    with urllib.request.urlopen(url, timeout=30) as resp:
        files = json.load(resp)["urls"]
    digests = sorted({f["digests"]["sha256"] for f in files})
    if not digests:
        sys.exit(f"no files found on PyPI for {name}=={version}")
    return digests


def main():
    for filename in FILES:
        path = ROOT / filename
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            match = PIN.match(line)
            if not match:
                if line.strip() and not line.startswith((" ", "-r")):
                    sys.exit(f"{filename}: unexpected line {line!r}")
                if line.startswith("-r"):
                    out.append(line)
                continue
            name, version = match.groups()
            digests = hashes_for(name, version)
            out.append(f"{name}=={version} \\")
            out.append(" \\\n".join(f"    --hash=sha256:{d}" for d in digests))
            print(f"{filename}: {name}=={version} ({len(digests)} hashes)")
        path.write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
