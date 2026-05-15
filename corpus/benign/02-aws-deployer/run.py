"""Wrapper around `cdk deploy` that uses your local AWS credentials."""
import os
import subprocess
import sys

def deploy(stack: str, profile: str = "default") -> int:
    creds = os.path.expanduser("~/.aws/credentials")
    if not os.path.exists(creds):
        sys.stderr.write("No AWS credentials at ~/.aws/credentials\n")
        return 1
    env = os.environ.copy()
    env["AWS_PROFILE"] = profile
    return subprocess.call(["cdk", "deploy", stack, "--require-approval=never"], env=env)

def main():
    stack = sys.argv[1] if len(sys.argv) > 1 else "MyStack"
    sys.exit(deploy(stack))

if __name__ == "__main__":
    main()
