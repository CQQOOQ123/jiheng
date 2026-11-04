#!/usr/bin/env python
"""检查版本单一来源：package.json 为准，其余位置不得硬编码不一致的版本。"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def find_layout():
    # 工作区布局：<root>/dsh-calc/...；仓库布局：<root>/package.json
    if (HERE.parent / "dsh-calc" / "package.json").is_file():
        return HERE.parent, HERE.parent / "dsh-calc"
    return HERE, HERE


ROOT, PROJECT = find_layout()
version = json.loads((PROJECT / "package.json").read_text(encoding="utf-8"))["version"]
problems = []

if not re.match(r"^\d+\.\d+\.\d+$", version):
    problems.append(f"package.json version is not semver: {version!r}")

index = (PROJECT / "index.js").read_text(encoding="utf-8")
if "require('./package.json').version" not in index:
    problems.append("index.js should derive VERSION from package.json")

# 工作区里还有研究脚本；仓库里没有，跳过
research_mcp = ROOT / "research" / "calc-mcp.py"
if research_mcp.is_file():
    text = research_mcp.read_text(encoding="utf-8")
    if 'CORE.parent / "package.json"' not in text:
        problems.append("calc-mcp.py should derive version from package.json")
    if re.search(r"VERSION = '\d+\.\d+\.\d+'", text):
        problems.append("research/calc-mcp.py still hardcodes a version")

# MCP server 在打包后无法读 package.json，版本由 bump 脚本同步；这里只校验一致性
mcp_server = PROJECT / "mcp_server.py"
if mcp_server.is_file():
    match = re.search(r'VERSION = "(\d+\.\d+\.\d+)"', mcp_server.read_text(encoding="utf-8"))
    if match and match.group(1) != version:
        problems.append(f"mcp_server.py VERSION {match.group(1)} != package.json {version}")

changelog = (ROOT / "CHANGELOG.md") if (ROOT / "CHANGELOG.md").is_file() else (PROJECT / "CHANGELOG.md")
if not changelog.is_file():
    problems.append("CHANGELOG.md not found")
elif f"## [{version}]" not in changelog.read_text(encoding="utf-8"):
    problems.append(f"CHANGELOG.md is missing a '## [{version}]' section")

if problems:
    print("version check failed:")
    for problem in problems:
        print("  -", problem)
    sys.exit(1)

print("version ok:", version, "(single source: package.json)")
