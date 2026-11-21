#!/usr/bin/env python3
"""Append a structured trace event to trace.jsonl and enforce same-result-twice exit."""
import argparse
import datetime
import json
import sys
from pathlib import Path


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
                    prior_saws.append(rec["saw"].strip())
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

    if args.status in ("fail", "crash") and args.saw.strip() and args.saw.strip() in prior_saws:
        print(
            f"[log_trace] SAME-RESULT-TWICE DETECTED on node={args.node}: {args.saw.strip()!r}. "
            "Stop retrying and escalate to human!",
            file=sys.stderr,
        )
        sys.exit(2)

    print(f"[log_trace] recorded {args.phase}/{args.node} status={args.status}")


if __name__ == "__main__":
    main()
