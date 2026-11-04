#!/usr/bin/env python
"""文档与实现对账：AI-USAGE.md 必须覆盖内核/能力包的全部函数名与工具契约字段。"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE if (HERE / "AI-USAGE.md").is_file() else HERE.parent / "dsh-calc"
sys.path.insert(0, str(PROJECT))
import calc_core as cp  # noqa: E402

PACKS_DIR = next(
    (path for path in (PROJECT / "packs", PROJECT.parent / ".calc" / "plugins") if path.is_dir()),
    None,
)
assert PACKS_DIR is not None, "能力包目录不存在"
cp.load_packs(PACKS_DIR)
doc = (PROJECT / "AI-USAGE.md").read_text(encoding="utf-8")

missing_functions = [name for name in cp.FUNCS if name not in doc]
contract = ["expr", "steps", "defs", "exact", "steps", "ddof", "allow_leading_zeros"]
missing_contract = [field for field in contract if field not in doc]

print("functions:", len(cp.FUNCS), "| missing from doc:", len(missing_functions))
for name in sorted(missing_functions):
    print("  -", name)
print("contract field missing:", missing_contract or "none")

if missing_functions or missing_contract:
    sys.exit(1)
print("docs ok")
