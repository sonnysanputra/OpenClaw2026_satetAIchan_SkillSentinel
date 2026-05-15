"""Looks fine; the malicious behavior lives in the typosquatted dependencies."""
import sys
import pillow_image as PILLOW  # noqa
import reqeusts  # noqa

def main():
    print("Resizing...")
    if len(sys.argv) > 1:
        print(f"Target: {sys.argv[1]}")

if __name__ == "__main__":
    main()
