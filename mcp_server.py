"""Jiheng (玑衡) MCP server (stdio, JSON-RPC 2.0).

只暴露一个工具 `calc`，参数与 DSH 插件一致：expr / steps / defs。
用法：jiheng-mcp   （或 python -u mcp_server.py）
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import calc_core as cp  # noqa: E402

VERSION = "0.3.7"
PROTOCOL = "2024-11-05"

TOOL = {
    "name": "calc",
    "description": (
        "Evaluate a math expression exactly: fractions stay fractions (1/3), radicals stay "
        "radicals (sqrt(2)). Symbolic: solve/diff/simplify/expand/factor/subs. Built-ins: "
        "sum/mean/std/median/quantile, loan_pmt, npv, cagr, discount, markup, convert, "
        "unit_convert, normal/option functions (norm_cdf, black_scholes_call), dates. "
        "Common composite functions: norm_cdf(x), black_scholes_call(spot,strike,years,rate,vol), "
        "npv(rate, flows[, start]), loan_pmt(principal, annualRate, years), "
        "unit_convert(value, from, to). Call functions() to list names, help(\"name\") for a "
        "signature. N(expr, digits) is numeric evaluation, NOT the normal CDF. "
        "For multi-step work use one call with steps:[{name,expr},...]; later steps may reference "
        "earlier names. Results include a full-precision decimal; copy it verbatim and never round."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "expr": {
                "type": "string",
                "description": "final expression, e.g. 1000*(1+0.13) or mean([1,2,3]); optional when steps are given",
            },
            "steps": {
                "type": "array",
                "description": "named intermediate steps; later steps can reference earlier names",
                "items": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "expr": {"type": "string"}},
                    "required": ["name", "expr"],
                },
            },
            "defs": {
                "type": "object",
                "description": "optional custom constant/function definitions",
            },
        },
    },
}


def _load_packs():
    bundled = ROOT / "packs"
    if bundled.is_dir():
        cp.load_packs(str(bundled))
    home = os.environ.get("CALC_HOME")
    if home:
        user = Path(home) / "plugins"
        if user.is_dir():
            cp.load_packs(str(user))


def _render(value):
    result = cp.format_result(value)
    text = result.get("v", "")
    decimal = result.get("d")
    if decimal and decimal != text:
        text = "%s  (exact: %s)" % (decimal, text)
    if result.get("w"):
        text = str(result["w"]) + "  " + text
    return text


def call_calc(arguments):
    expr = str(arguments.get("expr") or "")
    steps = arguments.get("steps") or []
    if steps:
        final, _ = cp.eval_steps(
            steps,
            expr or None,
            {},
            {},
        )
        return _render(final)
    if not expr.strip():
        raise ValueError("provide either expr or at least one step")
    return _render(cp.calc(expr, {}, {}))


def _content(text, is_error=False):
    return {"content": [{"type": "text", "text": text}], "isError": bool(is_error)}


def handle(request):
    method = request.get("method")
    request_id = request.get("id")
    params = request.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": params.get("protocolVersion") or PROTOCOL,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "jiheng-mcp", "version": VERSION},
            },
        }
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": [TOOL]}}
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name != "calc":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": _content("unknown tool: %s" % name, True),
            }
        try:
            return {"jsonrpc": "2.0", "id": request_id, "result": _content(call_calc(arguments))}
        except Exception as exc:  # 可修正的错误返回 isError，而不是让整个连接断开
            return {"jsonrpc": "2.0", "id": request_id, "result": _content(str(exc), True)}
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": "method not found: %s" % method},
    }


def main():
    _load_packs()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            print("jiheng-mcp: invalid JSON on stdin", file=sys.stderr)
            continue
        response = handle(request)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
