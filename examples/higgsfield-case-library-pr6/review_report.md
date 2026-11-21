# 审核与交付就绪报告 — 2026-11-22-repo-audit-and-upgrade

## 一、Round 1 → Round 2 独立对抗评审闭环记录

| 编号 | 级别 | 独立评审发现的问题 | E2 闭环整改措施 | 终审状态 (`G_REV-R2`) |
|---|---|---|---|---|
| `P0-1` | **阻断** | 原共享工作分支 `feat/repo-audit-and-harness-upgrade` 被另一窗口推入 `70d628e`（含 `tools/编排器/` 等 20 个 `forbidden` 文件） | 从干净基线 `clean-history-2026-11` (`9b7e5b6`) 开设隔离 worktree 与全新分支 `feat/repo-harness-ci-2026-11`，彻底剥离他人改动 | **已关闭（`git merge-base` = `9b7e5b6`）** |
| `P0-2` | **阻断** | 初版 `contract.yaml` `fence` 遗漏 `.githooks/`、`README.md`、`实验室/*` 与 `技能包台账.tsv` | 已修订 `contract.yaml` `fence` 并精确锁定 `forbidden` 为 `调研资料/技能包解包/*/` | **已关闭（35/35 改动在 `fence` 内）** |
| `P1-1` | **重要** | `tools/仓库自检.py` 缺 `源码索引/` 与磁盘计数一致性、计数仅查 `233` 字面量、链接扫描缺 `01 总目录` 与 `指引/00`、Python 3.9 f-string 检查过窄 | 已补全 AST 反斜杠检查（3.12+ 走 `get_source_segment`，<3.12 由 `ast.parse` 原生拦截）、磁盘 vs `包索引.tsv`/`文件索引.tsv` 全量核对、正则核对 `\d+ 个单文件`、纳入 `01 总目录` 与 `指引/00` | **已关闭（实测 exit 0）** |
| `P1-2` | **重要** | `tests/test_repo_harness.py` 缺 `体检.py` 负向泄露阻断测试、`出库.专项台账()` 动态测试、`LC_ALL=C` 测试，且 `evaluation_report.md:63` 对 `取回大文件.py` 描述超前 | 已全部补齐真实负向/动态夹具测试，补全 `取回大文件.py` symlink 越界校验，修正 `evaluation_report.md` 描述 | **已关闭（10/10 OK）** |
| `NTH` | 优化 | `分级.py` `"外10"` 前缀误命中 `S-X1`、`比.sh` 硬编码 `/usr/bin/python3`、`lib.sh` 空输出返回 0、`pre-commit` 重复跑体检 | 已全部修复并经回归测试通过 | **已关闭** |

---

## 二、门 1 / 门 2 / 门 3 终审交付就绪判定（`G_REV-R2` 实测确认）

| 维度 / 能力 | 终审判定 | 实测能用的 | 交付前/后续备注 | 实测证据 |
|---|---|---|---|---|
| **门 1：契约与围栏（`feat/repo-harness-ci-2026-11`）** | **`ready`** | 分支干净切自 `9b7e5b6`，35 个改动文件 100% 在新版 `fence` 内，零混入 `70d628e` 或任何 `forbidden` 目录 | 可直接推送并向 `clean-history-2026-11` 提 PR | `git merge-base` = `9b7e5b6`；`git diff --name-status 9b7e5b6..HEAD` |
| **门 2：工具门禁、脱敏与单测** | **`ready`** | Python 3.9 AST/反斜杠、Shell `dash` 语法、`体检.py --全部`（含真实负向 exit 1 夹具）、`出库.专项台账()` 动态防覆盖、`源码索引/` 磁盘同步、计数与核心链接全通过 | 无阻断项 | `python3.9 -I -B -m unittest discover -s tests -v` (10 OK)；`仓库自检.py` (exit 0)；`sh .githooks/pre-commit` (exit 0)；`LC_ALL=C` 复跑 (exit 0) |
| **门 3a：GitHub Actions 无 `ffmpeg` CI** | **`ready`** | `.github/workflows/ci.yml` 在 `ubuntu-latest`（Python 3.11、无 `ffmpeg`、无 Release 大媒体）下可 100% 绿灯通过 | 无需改动即可放行 PR CI | 本机默认 `PATH` 无 `ffmpeg` 条件下实测全绿 |
| **门 3b：音视频实片量测与对拍** | **`needs-config`** | POSIX `/bin/sh` 语法、`set -eu`、`LC_ALL=C`、`size` JSON 构造、空输出非 0、超容差 `exit 1` 与缺参 `exit 2` 经 mock 夹具实测通过 | 真实运行 `--自检` 或实片量测/对拍需在运行环境配置 `ffmpeg`/`ffprobe` 到 `PATH` 并按需取回 `SAMPLE_LIB` 媒体 | `TestMeasureAndCompareScripts` (2/2 OK)；默认 `PATH` 无 `ffmpeg` |
