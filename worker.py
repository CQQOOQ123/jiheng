#!/usr/bin/env python
"""dsh-calc worker: 常驻进程，按 JSON 行接收 {id, expr, defs}，回 {id, v} 或 {id, e, msg}。

常驻的意义：宿主只在第一次调用时启动它（~400ms），之后每次求值 1-2ms，
避免每次调用都付一次进程启动成本。
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calc_core as cp  # noqa: E402

try:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def calc_home() -> Path:
    env = os.environ.get("CALC_HOME") or os.environ.get("DSH_CALC_HOME")
    if env:
        return Path(env)
    local = Path.cwd() / ".calc"
    if local.exists():
        return local
    return Path.home() / ".calc"


def load_env():
    env, funcs = {}, {}
    pd = calc_home() / "packs"
    if pd.is_dir():
        for p in sorted(pd.glob("*.json")):
            try:
                cp.load_lib(str(p), env, funcs)
            except Exception as ex:  # 坏包不影响其他公式
                print("skip bad pack %s: %s" % (p, ex), file=sys.stderr)
    return env, funcs


def _log_history(expr, out):
    try:
        path = calc_home() / "history.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        value = out.get("v")
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value)
        entry = {
            "time": int(time.time() * 1000),
            "expr": str(expr or "")[:2000],
            "v": str(value)[:2000] if value is not None else None,
            "exact": out.get("exact"),
            "e": out.get("e"),
            "msg": (str(out.get("msg"))[:500] if out.get("msg") else None),
        }
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        if path.stat().st_size > 2_000_000:
            lines = path.read_text(encoding="utf-8").splitlines()[-1000:]
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass


def _text(value):
    rendered = cp.format_result(value)["v"]
    if isinstance(rendered, list):
        return ", ".join(str(item) for item in rendered)
    return str(rendered)


_BUILTIN_FUNCS = dict(cp.FUNCS)
_pack_sig = None


def _pack_dirs():
    dirs = []
    builtin = os.environ.get("DSH_CALC_BUILTIN_PACKS")
    if builtin:
        dirs.append(Path(builtin))
    dirs.append(calc_home() / "plugins")
    return dirs


def ensure_packs():
    """目录变化时自动重载能力包（新增/修改/删除都生效，无需重启 worker）。"""
    global _pack_sig
    dirs = _pack_dirs()
    try:
        sig = tuple(
            tuple(sorted((p.name, p.stat().st_mtime_ns) for p in root.glob("*.py"))) if root.is_dir() else ()
            for root in dirs
        )
    except Exception:
        sig = ()
    if sig == _pack_sig:
        return
    cp.FUNCS.clear()
    cp.FUNCS.update(_BUILTIN_FUNCS)
    loaded = []
    for root in dirs:
        loaded.extend(cp.load_packs(root))
    _pack_sig = sig
    if loaded:
        print("calc packs loaded: %s" % ", ".join(loaded), file=sys.stderr)


def load_limits():
    try:
        data = json.loads((calc_home() / "settings.json").read_text(encoding="utf-8"))
        return data.get("limits") or {}
    except Exception:
        return {}


def main():
    ensure_packs()
    sys.stdout.write(json.dumps({"ready": True}) + "\n")
    sys.stdout.flush()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        rid = req.get("id")
        out = {"id": rid}
        try:
            ensure_packs()
            cp.reset_assumptions()
            cp.apply_limits(load_limits())
            env, funcs = load_env()
            defs = req.get("defs")
            if isinstance(defs, str) and defs.strip():
                try:
                    defs = json.loads(defs)
                except Exception as ex:
                    raise ValueError("bad defs JSON: %s" % ex)
            if isinstance(defs, dict):
                cp.apply_defs(defs, env, funcs)
            steps = req.get("steps") or []
            expr = req.get("expr", "")
            if steps:
                v, step_results = cp.eval_steps(steps, expr, env, funcs)
                out.update(cp.format_result(v))
                out["steps"] = [{"name": name, "v": _text(val)}
                                for name, val in step_results]
            else:
                v = cp.calc(expr, env, funcs)
                out.update(cp.format_result(v))
        except Exception as ex:
            out["e"] = type(ex).__name__
            out["msg"] = str(ex)
        _log_history(req.get("expr"), out)
        sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
