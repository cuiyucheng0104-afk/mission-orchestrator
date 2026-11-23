# Mission Orchestrator — 长复杂任务编排器、工程质检标准与项目知识库超级技能

> 原 `kb-manager-skill`（含 `kb-manager` 与 `delivery-readiness-audit`）全面进化升级版：融合 **Phase 0（第一性原理与 3 方案对齐）+ Harness + Loop + Graph + 多环节独立对抗评审（红队/二三阶影响/新人认知/四维交付实测）+ 全链路 `.kb/` 可溯源与 Obsidian 同步**。

---

## 为什么从 `kb-manager` 升级为 `mission-orchestrator`？

| 维度 | 原 `kb-manager` + `delivery-readiness-audit` | 升级后 `mission-orchestrator` v2.0 |
|---|---|---|
| **需求与根因把关** | 直接按指令开工 | **Phase 0**：辨析症状 vs 根因、手段 vs 目标；模糊/架构任务先提澄清问题 + 给 3 版差异化方案对齐 |
| **执行隔离与契约** | 无任务级契约与分支隔离 | **Phase 1**：强制 `contract.yaml`（`done_when` + `fence` + `undo_tier`）+ 代码任务强制**独立 `git worktree`** |
| **Loop 与 Graph 编排** | 无主动闭环与熔断 | **Phase 2–3**：`run_loop.py` AI-in-the-Loop 闭环 + `log_trace.py` 强制 `EXPECTED vs SAW` + **同错两次 `exit 2` 熔断**；按 Early-Start Test 拆分并行 Graph |
| **多环节独立质检** | 仅终点做一次交付审计 | **Phase 4 三道门**：门 1 契约围栏 → 门 2 独立上下文代码审 + **二/三阶影响 + 钢人红队反驳 + 新人认知审计** → 门 3 四维实测审计（`ready / needs-config / blocked`） |
| **历史沉淀与 Obsidian** | `.kb/` 11 份静态文档 + Obsidian 同步 | **Phase 5**：历史包袱清理、慢节点卡顿复盘、共性根因固化成 `tests/`/Hook/CI；`.kb/runs/<run-id>/` 全程轨迹入库并支持 `--no-record` 同步 Obsidian |

---

## 目录结构

```text
mission-orchestrator/
├── SKILL.md                             # 技能地图与 8 条 STOP 红线
├── README.md                            # 本说明
├── references/                          # 按需加载的方法论参考（Progressive Disclosure）
│   ├── 00-first-principles-and-alignment.md
│   ├── 01-harness-contract.md
│   ├── 02-loop-and-graph.md
│   ├── 03-multi-stage-review.md
│   ├── 04-kb-and-obsidian.md
│   ├── audit-dimensions.md
│   └── kb-best-practices.md
├── scripts/                             # 零依赖 Python 3.9+ 确定性脚本
│   ├── init_kb.py                       # 初始化 .kb/ + .kb/.gitignore + runs/
│   ├── init_mission.py                  # 生成 contract.yaml / PROGRESS / DEAD_ENDS / trace / review
│   ├── log_trace.py                     # 追加 JSONL 轨迹 + 同错两次 exit 2 熔断（按去噪指纹比对）
│   ├── check_fence.py                   # 门 1 硬墙：改动文件必须在 fence 内、forbidden 外
│   ├── run_loop.py                      # Mode B 无人值守 AI-Gate-Feedback 循环引擎
│   ├── sync_obsidian.py                 # 同步 .kb/ 与 runs/ 到 Obsidian（支持 --no-record）
│   └── readiness-audit.workflow.js      # 并行交付就绪审计 Workflow 模板
├── assets/templates/                    # 11 份标准化 .kb/ 中文文档模板
├── examples/
│   └── higgsfield-case-library-pr6/     # 真实复杂仓库实战案例（脱敏）
├── tests/
│   └── test_mission_orchestrator.py     # 自动化回归测试（自举门禁）
└── evals/
    └── evals.json                       # 触发与行为断言评测集
```

---

## 安装

### Claude Code
```bash
git clone https://github.com/cuiyucheng0104-afk/mission-orchestrator.git ~/.claude/skills/mission-orchestrator
```

### Antigravity（全局 Skill 软链）
```bash
ln -sfn ~/.claude/skills/mission-orchestrator ~/.gemini/antigravity/skills/mission-orchestrator
```

### 自检（零依赖，兼容 Python 3.9+）
```bash
python3 -B -m unittest discover -s tests -v
```

---

## 实战验证案例

详见 [examples/higgsfield-case-library-pr6/CASE_STUDY.md](examples/higgsfield-case-library-pr6/CASE_STUDY.md)：用 `mission-orchestrator` 对 5,654 个文件的复杂研究库做三节点并行调研 → 先写红灯测试（8 failures, 1 error）→ 修复 6 处脚本与多处断链 → 独立上下文 `G_REV` 拦截共享分支污染（`P0-1`）与门禁盲区（`P1-1`/`P1-2`）→ 隔离 worktree 二审通过 → 创建 PR #6 并 10 秒跑通 GitHub Actions CI。
