from __future__ import annotations

import argparse
import re
from pathlib import Path

FORBIDDEN_PATTERNS = [
    re.compile(r"if\s+.*(?:\.mp4|\.mov|\.avi|\.mkv).*:", re.I),
    re.compile(r"(?:test|challenge).*?(?:\d{1,2}:\d{2}|\d+\.\d+)\s*[sS]?", re.I),
]


def main():
    p = argparse.ArgumentParser(description="Static audit for accidental filename/timestamp behaviour rules.")
    p.add_argument("root", nargs="?", default=".")
    args = p.parse_args()
    root = Path(args.root)
    findings = []
    for path in root.rglob("*.py"):
        if ".venv" in path.parts or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), 1):
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(line):
                    findings.append(f"{path}:{line_no}: {line.strip()}")
    if findings:
        print("Potential hard-coded video/timestamp logic found:")
        print("\n".join(findings))
        raise SystemExit(1)
    print("PASS: no obvious filename-driven or challenge-timestamp-driven behaviour rules found.")


if __name__ == "__main__":
    main()
