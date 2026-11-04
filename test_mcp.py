"""MCP 冒烟测试（仓库内版本，CI 用）。"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER = HERE / "mcp_server.py"

REQUESTS = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize",
     "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "smoke", "version": "0"}}},
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
     "params": {"name": "calc", "arguments": {"expr": "sqrt(2)"}}},
    {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
     "params": {"name": "calc", "arguments": {"expr": "npv(0.08, [623,644,431,286], 1)"}}},
    {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
     "params": {"name": "calc", "arguments": {"expr": "weekday('2026-02-30')"}}},
]

payload = "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in REQUESTS)
proc = subprocess.run(
    [sys.executable, "-u", str(SERVER)],
    input=payload, capture_output=True, text=True, encoding="utf-8", timeout=120,
)
responses = {}
for line in proc.stdout.splitlines():
    if line.strip().startswith("{"):
        msg = json.loads(line)
        if "id" in msg:
            responses[msg["id"]] = msg

checks = [
    ("initialize", responses[1]["result"]["serverInfo"]["name"] == "jiheng-mcp"),
    ("tools/list", any(t["name"] == "calc" for t in responses[2]["result"]["tools"])),
    ("sqrt(2)", "1.41421356237" in responses[3]["result"]["content"][0]["text"]),
    ("npv", "1681.338" in responses[4]["result"]["content"][0]["text"]),
    ("invalid date isError", responses[5]["result"]["isError"] is True),
    ("stdout is protocol only", "Traceback" not in proc.stdout),
]
passed = 0
for name, ok in checks:
    print(("ok   " if ok else "FAIL ") + name)
    passed += 1 if ok else 0
print("%d/%d passed" % (passed, len(checks)))
sys.exit(0 if passed == len(checks) else 1)
