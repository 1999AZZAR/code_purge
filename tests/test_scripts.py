import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "scripts" / "backup.sh"
RUN_TESTS = ROOT / "scripts" / "run_tests.sh"

spec = importlib.util.spec_from_file_location("analyze", ROOT / "scripts" / "analyze.py")
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load scripts/analyze.py")
analyze = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = analyze
spec.loader.exec_module(analyze)


class ScriptTests(unittest.TestCase):
    def test_backup_preserves_worktree_and_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            project.mkdir()
            subprocess.run(["git", "init", "-q", str(project)], check=True)
            subprocess.run(["git", "-C", str(project), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(project), "config", "user.name", "Test"], check=True)
            tracked = project / "tracked.txt"
            tracked.write_text("initial\n")
            subprocess.run(["git", "-C", str(project), "add", "tracked.txt"], check=True)
            subprocess.run(["git", "-C", str(project), "commit", "-qm", "initial"], check=True)
            tracked.write_text("staged\n")
            subprocess.run(["git", "-C", str(project), "add", "tracked.txt"], check=True)
            tracked.write_text("unstaged\n")
            (project / "untracked.txt").write_text("untracked\n")
            before = subprocess.run(
                ["git", "-C", str(project), "status", "--porcelain=v1"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout

            backup_root = Path(temp_dir) / "backups"
            env = os.environ | {"CODE_PURGE_BACKUP_ROOT": str(backup_root)}
            result = subprocess.run(
                ["bash", str(BACKUP), str(project)], capture_output=True, text=True, env=env
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            after = subprocess.run(
                ["git", "-C", str(project), "status", "--porcelain=v1"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertEqual(before, after)
            backup_dirs = list(backup_root.iterdir())
            self.assertEqual(len(backup_dirs), 1)
            self.assertTrue((backup_dirs[0] / "project.tar.gz").is_file())
            self.assertTrue((backup_dirs[0] / "staged.patch").is_file())
            self.assertTrue((backup_dirs[0] / "working.patch").is_file())

    def test_test_runner_reports_no_suite_as_unverified(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(["bash", str(RUN_TESTS), temp_dir], capture_output=True, text=True)

        self.assertEqual(result.returncode, 2)
        self.assertIn("No test suite detected", result.stdout)

    def test_test_runner_executes_python_suite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir, "test_example.py").write_text("def test_ok():\n    assert True\n")
            result = subprocess.run(["bash", str(RUN_TESTS), temp_dir], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("pytest passed", result.stdout)

    def test_knip_invalid_json_is_reported(self):
        report = analyze.Report(project_root=".", languages=["typescript"])
        with patch.object(analyze, "_project_node_tool", return_value="/project/knip"), patch.object(
            analyze, "_run", return_value=(1, "not json", "")
        ):
            analyze.run_knip(".", report)

        self.assertTrue(any("invalid JSON" in error for error in report.tool_errors))

    def test_jscpd_does_not_read_stale_global_report(self):
        stale = Path("/tmp/jscpd-report/jscpd-report.json")
        stale.parent.mkdir(exist_ok=True)
        stale.write_text(json.dumps({"duplicates": [{"lines": 99}]}))
        report = analyze.Report(project_root=".", languages=["python"])
        with patch.object(analyze, "_project_node_tool", return_value="/project/jscpd"), patch.object(
            analyze, "_run", return_value=(0, "", "")
        ):
            analyze.run_jscpd(".", report)

        self.assertEqual(report.findings, [])
        self.assertIn("did not produce", report.tool_errors[0])


if __name__ == "__main__":
    unittest.main()
