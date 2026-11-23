#!/usr/bin/env python3
"""Append a structured trace event to trace.jsonl and enforce same-result-twice exit."""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path


def fingerprint(saw: str) -> str:
    """熔断比对用的指纹：抹掉每次重跑都会变的噪声（地址、目录前缀、数字、空白）。

    shortcut: 只差数字或只差目录的两个不同错误会被并成一个而提前熔断——宁可早停问人，
    也不放过换了时间戳的同一个错；误停变多时再细分规则。带空格的路径不处理。
    """
    s = re.sub(r"0x[0-9a-fA-F]+", "H", saw)
    s = re.sub(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", "H", s)  # UUID
    s = re.sub(r"\b(?=[0-9a-fA-F]*\d)[0-9a-fA-F]{8,}\b", "H", s)  # 提交号/哈希（至少含一个数字）
    # /tmp/tmpab12/t.py 和 C:\Users\a\t.py 都只留 t.py
    s = re.sub(r"(?:[A-Za-z]:)?(?:[\\/][^\s\\/:\"']+)+[\\/]", "", s)
    s = re.sub(r"\d+", "N", s)
    return " ".join(s.split())


def main() -> None:
    parser = argparse.ArgumentParser(description="Log traceable step evidence and detect repeated failures.")
    parser.add_argument("run_dir", help="Path to .kb/runs/<run-id>/")
    parser.add_argument("--phase", required=True, help="contract | exec | review | kb")
    parser.add_argument("--node", required=True, help="Node or step identifier")
    parser.add_argument("--action", required=True, help="What was executed")
    parser.add_argument("--expected", default="", help="Expected outcome")
    parser.add_argument("--saw", default="", help="Observed outcome / error signature")
    parser.add_argument("--status", required=True, choices=["pass", "fail", "crash", "frozen"])
    parser.add_argument("--evidence", default="", help="Command exit code, file:line, or artifact path")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    trace_path = run_dir / "trace.jsonl"
    if not run_dir.exists():
        print(f"[log_trace] ERROR: run_dir does not exist: {run_dir}", file=sys.stderr)
        sys.exit(1)

    prior_saws = []
    if trace_path.exists():
        for line in trace_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
                if rec.get("node") == args.node and rec.get("status") in ("fail", "crash") and rec.get("saw"):
                    prior_saws.append(fingerprint(rec["saw"]))
            except json.JSONDecodeError:
                pass

    event = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "phase": args.phase,
        "node": args.node,
        "action": args.action,
        "expected": args.expected,
        "saw": args.saw,
        "status": args.status,
        "evidence": args.evidence,
    }
    with trace_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    if args.status in ("fail", "crash") and args.saw.strip() and fingerprint(args.saw) in prior_saws:
        print(
            f"[log_trace] SAME-RESULT-TWICE DETECTED on node={args.node}: {args.saw.strip()!r}. "
            "Stop retrying and escalate to human!",
            file=sys.stderr,
        )
        sys.exit(2)

    print(f"[log_trace] recorded {args.phase}/{args.node} status={args.status}")


if __name__ == "__main__":
    main()
