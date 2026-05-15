"""Fetch a news article and summarize it via the Anthropic API."""
import os
import sys
import urllib.request

def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.read().decode("utf-8", errors="replace")

def summarize(text: str) -> str:
    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=200,
        messages=[{"role": "user", "content": f"Summarize:\n\n{text[:8000]}"}],
    )
    return msg.content[0].text

def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://news.example-news.org/article/1"
    print(summarize(fetch(url)))

if __name__ == "__main__":
    main()
