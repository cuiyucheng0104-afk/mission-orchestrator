#!/usr/bin/env python3
"""Self-verification test suite for mission-orchestrator scripts (Python 3.9+ stdlib only)."""

import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_ROOT / "scripts"


class TestMissionOrchestratorScripts(unittest.TestCase):
    def test_all_python_scripts_syntax_and_py39_compat(self):
        py_files = sorted(SCRIPTS_DIR.glob("*.py"))
        self.assertGreaterEqual(len(py_files), 5)
        for p in py_files:
            src = p.read_text(encoding="utf-8")
            ast.parse(src, filename=str(p))

    def test_init_kb_and_init_mission_idempotency_and_gitignore(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "demo-proj"
            proj.mkdir()

            p = subprocess.run(
                [sys.executable, "-B", str(SCRIPTS_DIR / "init_mission.py"), str(proj), "--goal", "test-mission", "--run-id", "run-1"],
                capture_output=True, text=True,
            )
            self.assertEqual(p.returncode, 0, p.stderr)

            kb = proj / ".kb"
            self.assertTrue((kb / ".gitignore").exists())
            self.assertIn(".obsidian-sync.json", (kb / ".gitignore").read_text(encoding="utf-8"))
            self.assertTrue((kb / "README.md").exists())
            self.assertTrue((kb / "changelog.md").exists())

            run_dir = kb / "runs/run-1"
            for fn in ("contract.yaml", "PROGRESS.md", "DEAD_ENDS.md", "trace.jsonl", "review_report.md", "evaluation_report.md"):
                self.assertTrue((run_dir / fn).exists(), f"missing {fn}")

            # Idempotency check: custom edits must NOT be overwritten
            custom_note = run_dir / "PROGRESS.md"
            custom_note.write_text("KEEP_CUSTOM_PROGRESS\n", encoding="utf-8")
            p2 = subprocess.run(
                [sys.executable, "-B", str(SCRIPTS_DIR / "init_mission.py"), str(proj), "--goal", "test-mission", "--run-id", "run-1"],
                capture_output=True, text=True,
            )
            self.assertEqual(p2.returncode, 0, p2.stderr)
            self.assertEqual(custom_note.read_text(encoding="utf-8"), "KEEP_CUSTOM_PROGRESS\n")

    def test_log_trace_same_result_twice_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "proj"
            proj.mkdir()
            subprocess.run(
                [sys.executable, "-B", str(SCRIPTS_DIR / "init_mission.py"), str(proj), "--goal", "g", "--run-id", "r1"],
                check=True, capture_output=True,
            )
            run_dir = proj / ".kb/runs/r1"

            p1 = subprocess.run(
                [sys.executable, "-B", str(SCRIPTS_DIR / "log_trace.py"), str(run_dir),
                 "--phase", "exec", "--node", "n1", "--action", "a1", "--expected", "ok", "--saw", "ERR_SAME", "--status", "fail"],
                capture_output=True, text=True,
            )
            self.assertEqual(p1.returncode, 0, p1.stderr)

            p2 = subprocess.run(
                [sys.executable, "-B", str(SCRIPTS_DIR / "log_trace.py"), str(run_dir),
                 "--phase", "exec", "--node", "n1", "--action", "a2", "--expected", "ok", "--saw", "ERR_SAME", "--status", "fail"],
                capture_output=True, text=True,
            )
            self.assertEqual(p2.returncode, 2, "Expected exit 2 on same-result-twice")

    def test_run_loop_feedback_recovery_and_escalation(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "proj"
            proj.mkdir()
            subprocess.run(
                [sys.executable, "-B", str(SCRIPTS_DIR / "init_mission.py"), str(proj), "--goal", "g", "--run-id", "r1"],
                check=True, capture_output=True,
            )
            run_dir = proj / ".kb/runs/r1"
            flag = proj / "flag.txt"

            ai_cmd = (
                f'{sys.executable} -c "import sys,pathlib; p=pathlib.Path({str(flag)!r}); '
                f'txt=sys.stdin.read(); p.write_text(\'ok\' if \'EXPECTED\' in txt else \'bad\')"'
            )
            gate_cmd = (
                f'{sys.executable} -c "import sys,pathlib; '
                f'v=pathlib.Path({str(flag)!r}).read_text(); sys.exit(0 if v==\'ok\' else 1)"'
            )
            p_ok = subprocess.run(
                [sys.executable, "-B", str(SCRIPTS_DIR / "run_loop.py"),
                 "--run-dir", str(run_dir), "--node", "n_fix", "--ai-cmd", ai_cmd, "--gate-cmd", gate_cmd, "--max-attempts", "3"],
                capture_output=True, text=True,
            )
            self.assertEqual(p_ok.returncode, 0, p_ok.stdout + p_ok.stderr)
            self.assertIn("PASSED on attempt 2", p_ok.stdout)

            # Test same-result-twice escalation (exit 2)
            ai_stub = f'{sys.executable} -c "import sys; sys.stdin.read()"'
            gate_always_fail = f'{sys.executable} -c "import sys; print(\'SAME_ERR\', file=sys.stderr); sys.exit(1)"'
            p_esc = subprocess.run(
                [sys.executable, "-B", str(SCRIPTS_DIR / "run_loop.py"),
                 "--run-dir", str(run_dir), "--node", "n_stuck", "--ai-cmd", ai_stub, "--gate-cmd", gate_always_fail, "--max-attempts", "5"],
                capture_output=True, text=True,
            )
            self.assertEqual(p_esc.returncode, 2, p_esc.stdout + p_esc.stderr)

    def test_init_mission_runs_in_isolated_mode(self):
        # python3 -I (3.11+ 隐含 -P) 不把脚本目录放进 sys.path
        with tempfile.TemporaryDirectory() as tmp:
            p = subprocess.run(
                [sys.executable, "-I", "-B", str(SCRIPTS_DIR / "init_mission.py"), tmp, "--goal", "g", "--run-id", "r"],
                capture_output=True, text=True,
            )
            self.assertEqual(p.returncode, 0, p.stderr)

    def test_contract_yaml_escapes_goal(self):
        goal = '修 "登录" 的 bug: 超时 \\ # 注释'
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(
                [sys.executable, "-B", str(SCRIPTS_DIR / "init_mission.py"), tmp, "--goal", goal, "--run-id", "r"],
                check=True, capture_output=True,
            )
            lines = (Path(tmp) / ".kb/runs/r/contract.yaml").read_text(encoding="utf-8").splitlines()
            raw = next(l for l in lines if l.startswith("goal: "))[len("goal: "):]
            # JSON 字符串是合法的 YAML 双引号标量
            self.assertEqual(json.loads(raw), goal)
            for bad in ("../x", "/tmp/abs-out", ".."):
                p = subprocess.run(
                    [sys.executable, "-B", str(SCRIPTS_DIR / "init_mission.py"), tmp, "--goal", "g", "--run-id", bad],
                    capture_output=True, text=True,
                )
                self.assertNotEqual(p.returncode, 0, f"run-id {bad!r} 应被拒绝")
            self.assertFalse((Path(tmp) / ".kb/x").exists())

    def _log(self, run_dir, node, saw):
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPTS_DIR / "log_trace.py"), str(run_dir),
             "--phase", "exec", "--node", node, "--action", "a", "--saw", saw, "--status", "fail"],
            capture_output=True, text=True,
        ).returncode

    def test_log_trace_fuse_ignores_volatile_noise(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(
                [sys.executable, "-B", str(SCRIPTS_DIR / "init_mission.py"), tmp, "--goal", "g", "--run-id", "r"],
                check=True, capture_output=True,
            )
            run_dir = Path(tmp) / ".kb/runs/r"
            a = 'File "/tmp/tmpab12cd/t.py", line 12: AssertionError at 12:00:01 pid=411 obj 0x7f3a10'
            b = 'File "/var/folders/zz/tmpXY99/t.py", line 15: AssertionError at 12:00:09 pid=977 obj 0x7f9bc4'
            self.assertEqual(self._log(run_dir, "n", a), 0)
            self.assertEqual(self._log(run_dir, "n", b), 2, "同一错误只差时间戳/pid/临时目录/行号，应熔断")
            self.assertEqual(self._log(run_dir, "w", r"C:\Users\a\proj\t.py: req 3f2a9c1e-11aa-4bbb-8ccc-0123456789ab at commit 1a2b3c4d5e"), 0)
            self.assertEqual(self._log(run_dir, "w", r"C:\Users\b\tmp\t.py: req 7a1b2c3d-22bb-4ccc-9ddd-ba9876543210 at commit 9f8e7d6c5b"), 2)
            # 真正不同的错误不应误熔断
            self.assertEqual(self._log(run_dir, "m", "AssertionError: x"), 0)
            self.assertEqual(self._log(run_dir, "m", "KeyError: y"), 0)

    def _git(self, repo, *args):
        subprocess.run(
            ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t", "-C", str(repo), *args],
            check=True, capture_output=True,
        )

    def _fence(self, repo, run_dir, base="base"):
        return subprocess.run(
            [sys.executable, "-I", "-B", str(SCRIPTS_DIR / "check_fence.py"), str(run_dir), "--base", base, "--repo", str(repo)],
            capture_output=True, text=True,
        )

    def test_check_fence_blocks_out_of_fence_and_forbidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / "src").mkdir(parents=True)
            (repo / "migrations").mkdir()
            (repo / "src/a.py").write_text("1\n", encoding="utf-8")
            (repo / "migrations/001.sql").write_text("1\n", encoding="utf-8")
            (repo / "文档.md").write_text("1\n", encoding="utf-8")
            self._git(repo, "init", "-q")
            self._git(repo, "add", "-A")
            self._git(repo, "commit", "-q", "-m", "base")
            self._git(repo, "tag", "base")
            subprocess.run(
                [sys.executable, "-B", str(SCRIPTS_DIR / "init_mission.py"), str(repo), "--goal", "g", "--run-id", "r"],
                check=True, capture_output=True,
            )
            run_dir = repo / ".kb/runs/r"
            contract = run_dir / "contract.yaml"

            # 契约没填完（fence 还是占位符）→ 不放行；此刻只有 .kb/ 的改动，只有占位符检查能拦
            p = self._fence(repo, run_dir)
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertIn("⏳", p.stderr)
            (repo / "src/a.py").write_text("2\n", encoding="utf-8")

            # forbidden 用行内写法 → 拒绝（否则会被当成空列表而整个失效）
            contract.write_text('constraints:\n  fence:\n    - "src/"\n    - ".kb/"\n  forbidden: ["src/"]\n', encoding="utf-8")
            p = self._fence(repo, run_dir)
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertIn("行内", p.stderr)

            contract.write_text(
                'constraints:\n  fence:\n    - ".kb/"\n    - "src/"\n    - "*.md"\n'
                '  forbidden:\n    - "migrations/"\n    - "src/*/"\ndone_when:\n  - "x"\n', encoding="utf-8")

            # 已提交 + 未提交 + 中文路径，全在围栏内 → 放行
            self._git(repo, "commit", "-q", "-am", "in fence")
            (repo / "文档.md").write_text("2\n", encoding="utf-8")
            p = self._fence(repo, run_dir)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

            # `src/*/` 只禁子目录之下，不误伤同级文件 src/a.py（上面已放行）；子目录里的要拦
            (repo / "src/vendor").mkdir()
            (repo / "src/vendor/v.py").write_text("x\n", encoding="utf-8")
            p = self._fence(repo, run_dir)
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertIn("src/vendor/v.py", p.stdout + p.stderr)
            (repo / "src/vendor/v.py").unlink()

            # 未跟踪的围栏外文件 → 拦
            (repo / "other.txt").write_text("x\n", encoding="utf-8")
            p = self._fence(repo, run_dir)
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertIn("other.txt", p.stdout + p.stderr)
            # --repo 指到子目录也要看见仓库根的未跟踪文件
            p = self._fence(repo / "src", run_dir)
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertIn("other.txt", p.stdout + p.stderr)
            (repo / "other.txt").unlink()

            # 碰 forbidden → 拦，即使 fence 的通配也匹配它
            (repo / "migrations/说明.md").write_text("x\n", encoding="utf-8")
            p = self._fence(repo, run_dir)
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertIn("migrations/说明.md", p.stdout + p.stderr)
            (repo / "migrations/说明.md").unlink()

            # 把文件移出 forbidden 目录也算碰了它
            self._git(repo, "mv", "migrations/001.sql", "src/001.sql")
            p = self._fence(repo, run_dir)
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertIn("migrations/001.sql", p.stdout + p.stderr)
            self._git(repo, "mv", "src/001.sql", "migrations/001.sql")

            # 全部提交后拿 HEAD 当 base → 零改动，不能当作通过
            self._git(repo, "add", "-A")
            self._git(repo, "commit", "-q", "-m", "all")
            p = self._fence(repo, run_dir, base="HEAD")
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)

    def test_sync_obsidian_syncs_docs_and_runs_with_no_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "my-app"
            proj.mkdir()
            vault = Path(tmp) / "vault"
            (vault / ".obsidian").mkdir(parents=True)

            subprocess.run(
                [sys.executable, "-B", str(SCRIPTS_DIR / "init_mission.py"), str(proj), "--goal", "sync-test", "--run-id", "run-abc"],
                check=True, capture_output=True,
            )
            p = subprocess.run(
                [sys.executable, "-B", str(SCRIPTS_DIR / "sync_obsidian.py"), str(proj), str(vault), "--no-record"],
                capture_output=True, text=True,
            )
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertFalse((proj / ".kb/.obsidian-sync.json").exists())
            out_dir = vault / "项目知识库/my-app"
            self.assertTrue((out_dir / "my-app.md").exists())
            self.assertTrue((out_dir / "runs/run-abc/review_report.md").exists())


if __name__ == "__main__":
    unittest.main()
