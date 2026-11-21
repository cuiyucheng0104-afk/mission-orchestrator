# 04 · 历史演进复盘、根因固化与 KB/Obsidian 同步

## 1. Phase 5 三项工程复盘（每次长任务/PR 周期收尾必做）

### A. Git 历史包袱与架构减法审计
深入查看关键历史提交与长期分支演进，把存量代码与规则分为三类：
1. **有意为之的底座**：继续加固并写进自动化测试；
2. **历史遗留妥协**：明确标记技术债与清理窗口；
3. **为已不存在的问题引入的包袱**（例如旧模型时代的冗余脚手架、已迁走目录的旧指引）：**安全移除（减法艺术）**。

### B. 慢节点与卡顿热点复盘
复盘近期 PR 与本次运行的 `trace.jsonl`：
- 哪一环最慢、最容易卡顿或最耗 Token（如轮询等待、重复全盘扫描、串行阻塞本可并行的节点）？
- 能否通过 **Early-Start 并行化**、**增量/只查变更路径**、**反应式唤醒**消除？

### C. Bug / 返工 / 回滚共性根因 → 固化成系统基础设施
不要只记流水账。问一句：**为什么这类错会一再发生？**
- 能写成 **单元测试 / 负向变异测试** 的，不留在口头注意里；
- 能放进 **`.githooks/pre-commit` / `.github/workflows/ci.yml`** 的，不靠人肉提醒；
- 属于跨项目工作流教训的，升级写回 `mission-orchestrator` 的铁律与检查脚本。

---

## 2. 项目知识库（`.kb/`）目录与写作铁律

```text
<项目根目录>/.kb/
├── .gitignore           # 自动忽略 .obsidian-sync.json（防本机路径泄密）
├── README.md            # 导航入口（✅ / 🚧 / ⏳）
├── tech-stack.md / api.md / database.md / deployment.md / dev-standards.md
├── business-logic.md / testing.md / project-config.md / faq.md / changelog.md
├── runs/<run-id>/       # 本次任务的 contract / PROGRESS / DEAD_ENDS / trace / review
└── assets/              # diagrams / screenshots / icons
```

- **事实优先**：版本号、命令、路径必须来自代码实扫，禁止编造。
- **诚实标注欠账**：扫不到的理由与背景标 `> ⏳ 待补充：<需要谁提供>`。
- **变更必留痕**：收尾必在 `.kb/changelog.md` `[未发布]` 追加记录。

## 3. 同步到 Obsidian

```bash
# 同步 .kb/ 主题文档 + runs/<run-id>/ 审计档案到 Obsidian
python3 <skill_dir>/scripts/sync_obsidian.py <project_root> <vault_path>
# 若在只读/干净提交前的临时目录运行，加 --no-record 避免写入 .obsidian-sync.json
```
