#!/usr/bin/env python3
"""Initialize a traceable orchestrator mission run under <project_root>/.kb/runs/<run-id>/."""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

# python3 -I（3.11+ 隐含 -P）不会把脚本目录放进 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from init_kb import init_kb  # noqa: E402


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", text.strip()).strip("-")
    return (s[:40] or "mission").lower()


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize a traceable orchestrator mission run.")
    parser.add_argument("project_root", help="Target project root directory")
    parser.add_argument("--goal", required=True, help="Mission goal")
    parser.add_argument("--undo-tier", default="cleanup", choices=["one-click", "cleanup", "no-undo"])
    parser.add_argument("--run-id", default="", help="Optional custom run ID")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    init_kb(str(root))

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = args.run_id or f"{ts}-{slugify(args.goal)}"
    if Path(run_id).name != run_id or run_id in (".", ".."):
        parser.error(f"--run-id 不能含路径分隔符或是 . / ..：{run_id!r}")
    run_dir = root / ".kb" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    contract_path = run_dir / "contract.yaml"
    if not contract_path.exists():
        contract_path.write_text(
            # JSON 字符串是合法的 YAML 双引号标量，目标里带引号/冒号也不会写坏契约
            f"run_id: {json.dumps(run_id, ensure_ascii=False)}\n"
            f"goal: {json.dumps(args.goal, ensure_ascii=False)}\n"
            f'root_cause: "⏳ Phase 0 第一性原理定位后填写"\n'
            f"inputs:\n"
            f'  - "⏳ 待补充：输入文件/Issue/日志"\n'
            f'output: "⏳ 待补充：期望交付物"\n'
            f"constraints:\n"
            f"  fence:\n"
            f'    - ".kb/"\n'
            f'    - "⏳ 待补充：允许修改的文件或目录"\n'
            f"  forbidden:\n"
            f'    - "migrations/"\n'
            f"done_when:\n"
            f'  - "检查 1：修改前先复现失败（Red）"\n'
            f'  - "检查 2：修复/实现后同一检查在隔离环境通过（Green）"\n'
            f'  - "检查 3：独立上下文四关审核（含二/三阶影响与红队）+ 四维交付实测通过"\n'
            f'undo_tier: "{args.undo_tier}"\n'
            f"max_attempts_per_node: 3\n",
            encoding="utf-8",
        )

    progress_path = run_dir / "PROGRESS.md"
    if not progress_path.exists():
        progress_path.write_text(
            f"# PROGRESS — {run_id}\n\n"
            f"- **Goal**: {args.goal}\n"
            f"- **Undo Tier**: `{args.undo_tier}`\n"
            f"- **Topology**: `loop` (默认单循环；仅在通过 Early-Start Test 或需独立上下文隔离后升级 `graph`)\n\n"
            f"## 节点状态\n\n"
            f"- [ ] Phase 0: 第一性原理、真伪需求辨析与 3 方案对齐\n"
            f"- [ ] Phase 1: 独立 Worktree 隔离 + 契约签字 (`contract.yaml`)\n"
            f"- [ ] Phase 2: 先写失败检查 (Red)\n"
            f"- [ ] Phase 3: 执行与证据闭环 (`log_trace.py`)\n"
            f"- [ ] Phase 4: 独立上下文四关审核 (`review_report.md`)\n"
            f"- [ ] Phase 5: 历史包袱/慢节点/共性根因固化 + `.kb/` 更新与 Obsidian 同步\n",
            encoding="utf-8",
        )

    dead_ends_path = run_dir / "DEAD_ENDS.md"
    if not dead_ends_path.exists():
        dead_ends_path.write_text(
            f"# DEAD ENDS — {run_id}\n\n"
            f"> 已证伪方案与特征报错记录。后续轮次禁止重复尝试下列路径。\n\n"
            f"| 时间 | 节点 | 尝试方案 | 实见错误 (SAW) |\n"
            f"|---|---|---|---|\n",
            encoding="utf-8",
        )

    trace_path = run_dir / "trace.jsonl"
    if not trace_path.exists():
        trace_path.write_text("", encoding="utf-8")

    review_path = run_dir / "review_report.md"
    if not review_path.exists():
        review_path.write_text(
            f"# 审核与交付就绪报告 — {run_id}\n\n"
            f"## 门 1：契约与围栏核对\n- [ ] 基于干净基准独立 Worktree\n- [ ] `git diff --name-only` 100% 落在 `fence` 内\n- [ ] `done_when` 全项均有 `trace.jsonl` 实测证据\n\n"
            f"## 门 2：独立上下文深度审核（代码质量 + 二/三阶影响 + 钢人红队 + 新人认知成本）\n- 评审者上下文：独立只读子代理\n- 结论：待评审\n\n"
            f"## 门 3：交付就绪实测审计（4 维度 + 跨环境）\n\n"
            f"| 维度 / 能力 | 结论 (`ready`/`needs-config`/`blocked`) | 实测能用的 | 交付前必办阻碍 | 实测证据 |\n"
            f"|---|---|---|---|---|\n",
            encoding="utf-8",
        )

    eval_path = run_dir / "evaluation_report.md"
    if not eval_path.exists():
        eval_path.write_text(
            f"# 评估与根因分析报告 — {run_id}\n\n"
            f"> ⏳ Phase 0 / 调研节点完成后填写第一性原理根因、二/三阶影响与历史包袱审计。\n",
            encoding="utf-8",
        )

    print(f"[init_mission] run_dir={run_dir}")


if __name__ == "__main__":
    main()
