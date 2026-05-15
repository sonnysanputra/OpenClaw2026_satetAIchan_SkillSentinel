"""Convert currencies via exchangerate.host (no API key required)."""
import json
import sys
import urllib.request

def convert(amount: float, src: str, dst: str) -> float:
    url = f"https://api.exchangerate.host/convert?from={src}&to={dst}&amount={amount}"
    with urllib.request.urlopen(url, timeout=5) as resp:
        data = json.load(resp)
    return float(data["result"])

def main():
    amount = float(sys.argv[1]) if len(sys.argv) > 1 else 100.0
    src = sys.argv[2] if len(sys.argv) > 2 else "USD"
    dst = sys.argv[3] if len(sys.argv) > 3 else "EUR"
    print(f"{amount} {src} = {convert(amount, src, dst):.2f} {dst}")

if __name__ == "__main__":
    main()
