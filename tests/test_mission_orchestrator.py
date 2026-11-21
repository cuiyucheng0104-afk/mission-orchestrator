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
