# 01 · Harness 与契约规范（Contract, Isolation, Map, Walls, Memory）

## 1. 隔离工作区铁律（Worktree First）

对于任何修改代码、跨多文件重构或准备提 PR 的任务：
- **必须在独立的 `git worktree`**（切自干净基准分支如 `main`）中执行，严禁在用户正打开/其他会话正在使用的共享工作树里直接开发和提交。
- 若执行过程中因新增发现需要扩大修改范围，**必须先更新 `contract.yaml` 的 `fence`** 并记录到 `trace.jsonl`，再动手改文件。

## 2. 任务契约（`contract.yaml`）模板

```yaml
run_id: "2026-11-22-fix-auth-482"
goal: "明确、可验证的单一任务目标（经过 Phase 0 根因确认）"
root_cause: "第一性原理定位到的最本质原因"
inputs:
  - "相关 issue / 源码路径 / 日志"
output: "可审阅的 PR / 产物路径 / 报告"
constraints:
  fence:
    - ".kb/"   # 任务档案自己也是改动，必须在围栏内
    - "允许修改的目录或文件白名单"
  forbidden:
    - "禁止触碰的目录（如只读源码、migrations/、他人未跟踪目录）"
done_when:
  - "检查 1：修改前先复现失败（Red）"
  - "检查 2：修复/实现后同一检查在干净隔离环境通过（Green）"
  - "检查 3：独立上下文四关审核 + 交付就绪实测通过"
undo_tier: "cleanup"   # one-click | cleanup | no-undo
max_attempts_per_node: 3
```

## 3. 上下文地图（Map, Not a Manual）

- 根目录只放轻量索引（`AGENTS.md` / `CLAUDE.md` / `.kb/README.md`），控制在 200 行以内，按需（JIT）读取细节。
- 长命令输出重定向到文件再用 `grep` / `tail` 提取，不直接灌满上下文窗口。

## 4. Write It Twice（写两遍铁律）

每条重要规矩必须成对存在：
1. **GUIDE**（人/模型可读）：写在 `AGENTS.md` / `contract.yaml`，说明**为什么**。
2. **CHECK**（机检硬墙）：写在单测 / Lint / Git Hook / CI / `仓库自检.py` 里，模型无法绕过。

## 5. 外置记忆与防路径泄露

- `PROGRESS.md`（进度与 `[FROZEN]` 节点）与 `DEAD_ENDS.md`（已证伪思路 + `saw` 报错）必须持续落盘。
- `.kb/.gitignore` 屏蔽 `.obsidian-sync.json` 等本机路径文件；严禁将 `/Users/<name>/` 本机绝对路径提交进共享仓库。
