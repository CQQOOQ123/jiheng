#!/usr/bin/env python
"""检查版本单一来源：package.json 为准，其余位置不得硬编码版本。"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
version = json.loads((ROOT / "dsh-calc" / "package.json").read_text(encoding="utf-8"))["version"]
problems = []

if not re.match(r"^\d+\.\d+\.\d+$", version):
    problems.append(f"package.json version is not semver: {version!r}")

index = (ROOT / "dsh-calc" / "index.js").read_text(encoding="utf-8")
if "require('./package.json').version" not in index:
    problems.append("index.js should derive VERSION from package.json")

mcp = (ROOT / "research" / "calc-mcp.py").read_text(encoding="utf-8")
if 'CORE.parent / "package.json"' not in mcp:
    problems.append("calc-mcp.py should derive version from package.json")

for rel in ("dsh-calc/index.js", "research/calc-mcp.py"):
    text = (ROOT / rel).read_text(encoding="utf-8")
    if re.search(r"VERSION = '\d+\.\d+\.\d+'", text) or re.search(r'"version": "\d+\.\d+\.\d+"', text):
        problems.append(f"{rel} still hardcodes a version")

changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
if f"## [{version}]" not in changelog:
    problems.append(f"CHANGELOG.md is missing a '## [{version}]' section")

if problems:
    print("version check failed:")
    for problem in problems:
        print("  -", problem)
    sys.exit(1)

print("version ok:", version, "(single source: package.json)")
