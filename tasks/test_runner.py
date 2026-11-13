import subprocess
import sys
from pathlib import Path


def test_each_task_has_passing_fixed_solution():
    root = Path(__file__).parent
    for task_dir in sorted(root.glob("task-*")):
        solution = task_dir / "solution.py"
        tests = list(task_dir.glob("test_*.py"))
        assert tests, f"missing tests in {task_dir.name}"
        # Verify golden fix: run stub with rule hint
        env = {**dict(__import__("os").environ), "PLAYBOOK_RULE": "Run tests after every code change"}
        proc = subprocess.run(
            [sys.executable, str(task_dir / "run_agent_stub.py")],
            cwd=task_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"{task_dir.name} stub failed: {proc.stderr}"
