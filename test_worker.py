#!/usr/bin/env python
"""集成测试：驱动 worker.py（JSON 行协议），覆盖表达式、steps、defs、能力包、热加载、错误与安全。"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

tmp = Path(tempfile.mkdtemp(prefix="calc-test-"))
(tmp / "plugins").mkdir(parents=True, exist_ok=True)
for pack in (ROOT / ".calc" / "plugins").glob("*.py"):
    shutil.copy(pack, tmp / "plugins" / pack.name)

ENV = dict(os.environ)
ENV["CALC_HOME"] = str(tmp)

PASS, FAIL = 0, 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print("ok   %-44s %s" % (name, detail))
    else:
        FAIL += 1
        print("FAIL %-44s %s" % (name, detail))


proc = subprocess.Popen(
    [sys.executable, "-u", str(HERE / "worker.py")],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, encoding="utf-8", env=ENV, cwd=str(ROOT),
)


ready_line = proc.stdout.readline()
check("ready handshake", json.loads(ready_line).get("ready") is True, ready_line)


def rpc(payload):
    proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError("worker closed: " + proc.stderr.read())
    return json.loads(line)


r = rpc({"id": 1, "expr": "1/3"})
check("expr 1/3", r.get("v") == "1/3" and r.get("exact") is True, str(r))

r = rpc({"id": 2, "expr": "b", "steps": [
    {"name": "a", "expr": "1/3"}, {"name": "b", "expr": "a*3"}]})
check("steps", r.get("v") == "1" and [s["name"] for s in r.get("steps", [])] == ["a", "b"], str(r))

r = rpc({"id": 3, "expr": "含税(1000)",
         "defs": json.dumps({"fn": {"含税": {"p": ["x"], "e": "x*(1+0.13)"}}})})
check("defs", r.get("v") == "1130", str(r))

r = rpc({"id": 4, "expr": "corr([1,2,3,4],[2,4,5,4])"})
check("pack corr", "sqrt(95)" in str(r.get("v")), str(r))

r = rpc({"id": 5, "expr": "solve_real(x^2-5*x+6, x)"})
check("solve_real", r.get("v") == ["2", "3"], str(r))

r = rpc({"id": 6, "expr": "last(series(x, x, 1, 5))"})
check("first/last", r.get("v") == "5", str(r))

# 热加载：写入新能力包，不重启 worker 直接调用
hot = tmp / "plugins" / "hot.py"
hot.write_text(
    "NAME='hot'\ndef register(reg):\n"
    "    reg.func('triple', ['x'], lambda x: x * 3)\n",
    encoding="utf-8",
)
r = rpc({"id": 7, "expr": "triple(7)"})
check("pack hot load", r.get("v") == "21", str(r))

# 删除后应失效（重载后 FUNCS 回到内置 + 现有包）
hot.unlink()
r = rpc({"id": 8, "expr": "triple(7)"})
check("pack hot unload", r.get("e") == "ValueError" and "unknown function" in r.get("msg", ""), str(r))

r = rpc({"id": 9, "expr": "1/0"})
check("division by zero", r.get("e") == "ValueError" and "division" in r.get("msg", ""), str(r))

r = rpc({"id": 10, "expr": "__import__('os')"})
check("injection rejected", "e" in r, str(r))

r = rpc({"id": 11, "expr": "sqrt(2)"})
check("radical preserved", r.get("v") == "sqrt(2)" and r.get("d", "").startswith("1.414"), str(r))

proc.stdin.close()
proc.wait(timeout=10)
shutil.rmtree(tmp, ignore_errors=True)

print("\n%d passed, %d failed" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
