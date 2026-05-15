"""Format a directory of Python files using `ruff format`."""
import shutil
import subprocess
import sys

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    if shutil.which("ruff") is None:
        sys.stderr.write("ruff is not installed.\n")
        sys.exit(2)
    sys.exit(subprocess.call(["ruff", "format", target]))

if __name__ == "__main__":
    main()
