---
name: mission-orchestrator
description: >
  第一性原理驱动的长复杂任务编排器、工程质检标准与项目知识库超级技能（Phase 0 元认知对齐 +
  Harness + Loop + Graph + 红队/二三阶影响/新人认知多环节独立审核 + 历史包袱与根因固化 + .kb/Obsidian 全链路可溯源）。
  整合并全面升级自 kb-manager 与 delivery-readiness-audit。
  触发于：长复杂任务、需求架构设计与方案对比、仓库工程体检与改良、多代理编排、代码/交付质检审核、
  历史包袱与返因复盘、初始化或维护 .kb/ 知识库、同步 Obsidian、以及判断"做完了吗/能交付了吗"。
---

# Mission Orchestrator v2.0 — 长复杂任务编排与工程质检标准

> **核心信条**：先问清问题真伪（Phase 0），再用 Harness 赋予能力、用 Loop 逼出实证、用 Graph 隔离并发与评审，最后把每次失败与返工固化成自动化门禁与 `.kb/` 溯源资产。

## 零、铁律（STOP 红线）

1. **先判真伪需求与第一性原理，再立契约**：禁止盲从表面提问；设计/模糊任务必须先对齐偏好并给 3 版方案（[00-first-principles-and-alignment.md](references/00-first-principles-and-alignment.md)）。
2. **无 `done_when` 不开工，且代码任务必须独立 Worktree 隔离**：未签订 `contract.yaml` 禁止改业务代码；涉及多文件改造或提 PR 的任务必须从干净基准切出独立 `git worktree`，严禁在共享工作树与其它会话互踩。
3. **上下文是 RAM，`.kb/` 是硬盘**：决策、`DEAD_ENDS.md`、`PROGRESS.md`、`trace.jsonl` 必须落盘；`.kb/.gitignore` 默认屏蔽 `.obsidian-sync.json` 等本机路径文件。
4. **禁止无 AI 介入的空壳编排器与空壳门禁**：执行/评审节点必须明确 **Mode A（独立上下文子代理真跑）** 或 **Mode B（`run_loop.py` 调 AI CLI 闭环）**；门禁必须验证真实内容与实测输出，禁止只查文件存在性。
5. **先写失败检查，再写实现（Red → Green）**：可机检目标必须在修复前看到测试/检查失败一次。
6. **不许自己审自己，且必须过红队 + 二/三阶影响 + 新人认知审**：生成者与审核者上下文物理隔离；禁止把 `"looks good / should pass"` 当证据。
7. **同错两次即停（`exit 2`）**：`log_trace.py` 检测到同一 `saw` 错误重复出现时立即熔断升级人类。
8. **CI 绿 ≠ 可交付，且根因必须沉淀成基础设施**：收尾前必过四维实测交付审计（`ready / needs-config / blocked`），并将共性 Bug/返工固化成单测、Hook、CI 或 Skill 规则。

---

## 一、技能地图（Map，按需加载）

| 阶段 | 职责 | 参考文档（按需读） | 确定性脚本 / 模板 |
|---|---|---|---|
| **Phase 0** | 第一性原理、真伪需求辨析、提问对齐、3 方案、跨领域类比 | [00-first-principles-and-alignment.md](references/00-first-principles-and-alignment.md) | — |
| **Phase 1** | Worktree 隔离、`contract.yaml`（`done_when`/`fence`/`undo_tier`）、`Write It Twice` | [01-harness-contract.md](references/01-harness-contract.md) | `scripts/init_mission.py` |
| **Phase 2–3** | Loop vs Graph、Early-Start 并行、Evidence、`EXPECTED vs SAW`、同错两次退出 | [02-loop-and-graph.md](references/02-loop-and-graph.md) | `scripts/run_loop.py`, `scripts/log_trace.py` |
| **Phase 4** | 三道门审核 + **二/三阶影响、钢人红队反驳、新人认知成本、四维实测交付审计** | [03-multi-stage-review.md](references/03-multi-stage-review.md) | `scripts/readiness-audit.workflow.js` |
| **Phase 5** | **Git 历史包袱清理、慢节点/卡顿复盘、Bug 根因固化**、`.kb/` 更新与 Obsidian 同步 | [04-kb-and-obsidian.md](references/04-kb-and-obsidian.md) | `scripts/init_kb.py`, `scripts/sync_obsidian.py` |
| **实战参考** | 完整脱敏端到端范例（`higgsfield-case-library` PR #6） | [CASE_STUDY.md](examples/higgsfield-case-library-pr6/CASE_STUDY.md) | — |

---

## 二、六阶段标准工作流

```text
[Phase 0: 第一性原理与 3 方案对齐] ──▶ [Phase 1: 隔离 Worktree + 契约/内存] ──▶ [Phase 2-3: Loop / Graph 证据闭环]
                                                                                           │
[Phase 5: 历史/慢点/根因固化 + KB/Obsidian] ◀── [Phase 4: 三道门 + 红队/二三阶/认知/实测审计] ◀─┘
```

1. **Phase 0（先想透再立靶）**：
   - 判断用户是否在把**症状当原因**、**手段当目标**；用第一性原理拆到底层约束；
   - 遇到架构/选型/存在歧义的需求：先提 2–4 个关键澄清问题对齐偏好，再给出 **3 版差异化方案**（极简止血 / 平衡工程 / 彻底重构，含各自二/三阶影响与钢人反驳点）供拍板。*（注：若用户需求高度明确、边界清晰或已给出完整规范，可精简提问直接进入 Phase 1，但仍须完成真伪需求自检。）*
2. **Phase 1（隔离 + 契约）**：
   - 跑 `python3 <skill_dir>/scripts/init_mission.py <project_root> --goal "<目标>"`；代码/PR 任务切出独立 `git worktree`；填写 `contract.yaml`（若执行中发现需扩展修复范围，**必须先显式修订 `contract.yaml` 再改文件**）。
3. **Phase 2–3（Loop / Graph 执行）**：
   - 默认单 Loop；仅在通过 Early-Start Test（无真实依赖可并行）、需独立上下文隔离或需冻结通过节点时拆 Graph；
   - 先写失败检查（Red）→ 实现修复（Green）→ 每步用 `log_trace.py` 记账，遇 `exit 2` 立刻升级。
4. **Phase 4（多环节独立质检）**：
   - 派出**独立上下文只读 Reviewer** 执行三道门：契约围栏核对 → **红队反驳 + 二/三阶推演 + 新人认知审查** → **四维度实测交付审计**（`ready / needs-config / blocked`，覆盖干净隔离环境如 `python3 -I`、`LC_ALL=C`、`无可选二进制` 场景）。
5. **Phase 5（复盘沉淀与同步）**：
   - 审视 Git 演变与历史包袱（识别可安全删除的死代码/旧补丁）、排查流程慢点（如轮询空转/重复扫全库）、将本次暴露的共性根因固化进 `tests/` / Hook / CI / Skill；
   - 更新 `.kb/` 与 `changelog.md`，按需调用 `sync_obsidian.py`（提交前确认无本机路径文件入暂存区）。
