"""Extract text from a PDF using pypdf."""
import sys
from pypdf import PdfReader

def extract(path: str) -> str:
    reader = PdfReader(path)
    return "\n".join((p.extract_text() or "") for p in reader.pages)

def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: run.py <file.pdf>\n")
        sys.exit(1)
    print(extract(sys.argv[1]))

if __name__ == "__main__":
    main()
