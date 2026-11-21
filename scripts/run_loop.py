#!/usr/bin/env python3
"""Active AI-in-the-Loop Runner: invokes an AI CLI/agent, runs a deterministic Gate,
feeds EXPECTED vs SAW back on failure, and enforces same-result-twice exit (code 2)."""
import argparse
import datetime
import json
import shlex
import subprocess
import sys
from pathlib import Path


def read_text(path: Path, max_chars: int = 6000) -> str:
    if not path.exists():
        return ""
    txt = path.read_text(encoding="utf-8", errors="replace")
    return txt[-max_chars:] if len(txt) > max_chars else txt


def build_prompt(run_dir: Path, node: str, attempt: int, prev_feedback: str) -> str:
    contract = read_text(run_dir / "contract.yaml", 4000)
    progress = read_text(run_dir / "PROGRESS.md", 3000)
    dead_ends = read_text(run_dir / "DEAD_ENDS.md", 3000)
    parts = [
        f"你正在执行 Mission Orchestrator 节点 `{node}`（第 {attempt} 次尝试）。",
        "严格遵守 contract.yaml 中的 constraints/fence 与 done_when，禁止触碰 forbidden 路径。",
        "\n=== contract.yaml ===\n" + contract,
        "\n=== PROGRESS.md ===\n" + progress,
        "\n=== DEAD_ENDS.md（严禁重蹈覆辙）===\n" + dead_ends,
    ]
    if prev_feedback:
        parts.append("\n=== 上一轮 Gate 失败反馈（必须针对性修复）===\n" + prev_feedback)
    return "\n".join(parts)


def append_dead_end(run_dir: Path, node: str, attempt: int, saw: str) -> None:
    p = run_dir / "DEAD_ENDS.md"
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean_saw = saw.replace("\n", " ").replace("|", "\\|")[:160]
    with p.open("a", encoding="utf-8") as f:
        f.write(f"| {ts} | {node} (attempt {attempt}) | 自动循环尝试 | {clean_saw} |\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an AI-in-the-loop node with deterministic Gate.")
    parser.add_argument("--run-dir", required=True, help="Path to .kb/runs/<run-id>/")
    parser.add_argument("--node", required=True, help="Node name")
    parser.add_argument("--ai-cmd", required=True, help="Command to invoke AI (reads prompt from stdin)")
    parser.add_argument("--gate-cmd", required=True, help="Deterministic verification command (exit 0 = pass)")
    parser.add_argument("--max-attempts", type=int, default=3, help="Max attempts before escalating")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    log_script = Path(__file__).resolve().parent / "log_trace.py"
    if not run_dir.exists():
        print(f"[run_loop] ERROR: run_dir not found: {run_dir}", file=sys.stderr)
        sys.exit(1)

    prev_feedback = ""
    for attempt in range(1, args.max_attempts + 1):
        prompt = build_prompt(run_dir, args.node, attempt, prev_feedback)

        ai_proc = subprocess.run(
            args.ai_cmd, shell=True, input=prompt, text=True, capture_output=True
        )
        if ai_proc.returncode != 0:
            saw = f"AI_CMD_CRASH rc={ai_proc.returncode}: {(ai_proc.stderr or ai_proc.stdout).strip()[:200]}"
            log_rc = subprocess.run(
                [sys.executable, str(log_script), str(run_dir),
                 "--phase", "exec", "--node", args.node,
                 "--action", f"attempt {attempt}: {args.ai_cmd}",
                 "--expected", "AI exit 0", "--saw", saw, "--status", "crash"],
            ).returncode
            if log_rc == 2:
                sys.exit(2)
            prev_feedback = f"FAILED {args.node}\nEXPECTED AI exit 0\nSAW {saw}"
            continue

        gate_proc = subprocess.run(
            args.gate_cmd, shell=True, text=True, capture_output=True
        )
        if gate_proc.returncode == 0:
            subprocess.run(
                [sys.executable, str(log_script), str(run_dir),
                 "--phase", "exec", "--node", args.node,
                 "--action", f"attempt {attempt}: {args.gate_cmd}",
                 "--expected", "gate exit 0", "--saw", "gate passed",
                 "--status", "pass", "--evidence", f"attempt={attempt}, rc=0"],
                check=False,
            )
            print(f"[run_loop] NODE {args.node} PASSED on attempt {attempt} -> [FROZEN]")
            sys.exit(0)

        err_out = (gate_proc.stderr or gate_proc.stdout).strip()
        saw_sig = (err_out.splitlines()[-1] if err_out else f"gate rc={gate_proc.returncode}")[:200]
        append_dead_end(run_dir, args.node, attempt, saw_sig)

        log_rc = subprocess.run(
            [sys.executable, str(log_script), str(run_dir),
             "--phase", "exec", "--node", args.node,
             "--action", f"attempt {attempt}: {args.gate_cmd}",
             "--expected", "gate exit 0", "--saw", saw_sig, "--status", "fail"],
        ).returncode
        if log_rc == 2:
            print(f"[run_loop] Escalating {args.node} after same-result-twice.", file=sys.stderr)
            sys.exit(2)

        prev_feedback = (
            f"FAILED   {args.node}\n"
            f"EXPECTED gate command `{args.gate_cmd}` exit 0\n"
            f"SAW      {err_out[-800:]}"
        )

    print(f"[run_loop] Escalating {args.node}: exhausted max_attempts={args.max_attempts}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
