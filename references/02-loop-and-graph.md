# 02 · Loop 与 Graph 编排规范

## 1. 证据强度金字塔（只认硬证据）

| 等级 | 证据类型 | 示例 |
|---|---|---|
| 1（最强） | 确定性机检 | 单测/端到端测试 `exit 0`、Lint/Typecheck 通过、Schema 校验通过 |
| 2（次强） | 可观测轨迹 | `.kb/runs/<run-id>/trace.jsonl` 记录了真实命令与输出 |
| 3（中等） | 独立上下文评审 | 独立子代理（未参与编写）的审查意见与 Playwright/curl 实测 |
| 4（禁止单独使用） | 模型自评 | `"looks good"`、`"should pass"`、`"I'm confident"` |

## 2. 反馈格式（Feedback, Not Verdicts）

禁止只返回 `"Failed"` 或 `"Red"`。每次失败反馈必须包含四要素：

```text
FAILED    <检查项或节点名>
EXPECTED  <期望行为/状态码/输出>
SAW       <实际观测到的错误/返回值/file:line>
FENCE     <本轮允许修改的文件范围>
DEAD ENDS <已证伪、禁止再试的方案>
```

## 3. 两种合法执行模式（拒绝空壳编排器）

1. **Mode A（对话内多代理编排）**：主 Agent 必须真实派出 `invoke_subagent` / `swarm` 在独立上下文执行调研、编写与评审（禁止主 Agent 自己脑补跳过），Python 只负责 `log_trace.py` 记账与真实内容门禁。
2. **Mode B（脱离对话的无人值守 Runner）**：使用 `scripts/run_loop.py` 真正把 `contract.yaml` + `PROGRESS.md` + `DEAD_ENDS.md` + 上一轮 `EXPECTED vs SAW` 喂给 AI CLI（如 `claude -p`）：
   ```bash
   python3 <skill_dir>/scripts/run_loop.py \
     --run-dir .kb/runs/<run-id> \
     --node fix-auth \
     --ai-cmd "claude -p" \
     --gate-cmd "pytest tests/test_auth.py" \
     --max-attempts 3
   ```

## 4. 硬退出条件（Exits）

- **同错两次退出（Same-Result-Twice）**：`scripts/log_trace.py` 会比对历史 `saw` 的指纹（先抹掉地址、目录前缀、数字等每次重跑都会变的噪声）；若同一错误连续或重复出现两次，脚本返回退出码 `2`，编排器必须停止当前思路并向用户升级求助。
- **预算/步数上限**：单节点默认 `max_attempts_per_node: 3`，超限即挂起人工介入。

## 4. Graph 拆分四刀法则（4 Cuts）

1. **Early-Start Test（早启动测试）**：对每条依赖边 A → B 问："如果 B 在 A 结束前启动会坏吗？" 不会坏就删掉边，并行执行。
2. **按独立失败原因拆节点**：会因不同原因挂掉的步骤拆开；总是同生共死的合并。
3. **每个 Worker 独立上下文**：并行审计/评审必须分派到独立子代理上下文，避免"第一个人的假设污染所有人"。
4. **冻结已通过节点（Freeze Passed Nodes）**：通过门控的节点输出设为 `[FROZEN]`；下游失败时只带着反馈重跑失败节点。
5. **确定性逻辑用代码**：汇总、去重、格式校验、状态流转用 Python 脚本，不用 LLM。

## 5. 回退代价门控（Undo-Price Gates）

| 级别 | 典型操作 | 放行条件 |
|---|---|---|
| `one-click` | 文档更新、单测补充、局部纯函数 | 确定性测试全绿自动通过 |
| `cleanup` | 跨文件重构、Auth/核心逻辑、Schema 调整 | 测试绿 + Trace 完整 + 独立上下文 Second Opinion |
| `no-undo` | 数据迁移、删库/删文件、对外发送/发布、资金操作 | **必须人类明确签字放行**（无任何置信度豁免） |
