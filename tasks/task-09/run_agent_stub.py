import os
import subprocess
import sys
from pathlib import Path

BUGGY = """def merge_counts(a,b):
    out=dict(a)
    for k,v in b.items():
        out[k]=v
    return out
"""
FIXED = """def merge_counts(a,b):
    out=dict(a)
    for k,v in b.items():
        out[k]=out.get(k,0)+v
    return out
"""
HINT = "test"

def main():
    rule = os.environ.get("PLAYBOOK_RULE", "")
    src = Path("solution.py")
    src.write_text(BUGGY)
    # Simulated mistaken agent: edits config or skips tests when no helpful rule
    if HINT == "config" and ("config" in rule.lower() or "test" in rule.lower()):
        src.write_text(FIXED)
    elif HINT == "test" and ("test" in rule.lower() or "assertion" in rule.lower() or "one file" in rule.lower()):
        src.write_text(FIXED)
    elif HINT == "test" and not rule:
        # bad fix: still wrong
        src.write_text(BUGGY.replace("return", "return  # agent edited config first\n    return", 1) if False else BUGGY)
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q"], capture_output=True, text=True)
    if proc.returncode != 0 and rule and ("test" in rule.lower() or "config" in rule.lower() or "task" in rule.lower()):
        src.write_text(FIXED)
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q"], capture_output=True, text=True)
    line = "tests passed" if proc.returncode == 0 else proc.stdout.splitlines()[-1] if proc.stdout else "failed"
    print(line)
    sys.exit(proc.returncode)

if __name__ == "__main__":
    main()
