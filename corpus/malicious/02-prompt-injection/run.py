"""Benign-looking translator; injection lives in skill.md instead."""
import sys
def main():
    text = sys.argv[1] if len(sys.argv) > 1 else "Hello"
    print(f"Translated: {text}")

if __name__ == "__main__":
    main()
