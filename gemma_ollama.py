"""
Gemma via Ollama — text chat.

Setup:
    brew install ollama
    ollama serve &
    ollama pull gemma3:4b

Run:
    python gemma_ollama.py
"""

import requests
import json

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "gemma3:4b"


def chat(prompt: str) -> str:
    print(f"Q: {prompt}")
    print("A: ", end="", flush=True)

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }
    response = requests.post(OLLAMA_URL, json=payload, stream=True)
    response.raise_for_status()

    full_reply = ""
    for line in response.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        token = chunk.get("message", {}).get("content", "")
        print(token, end="", flush=True)
        full_reply += token
        if chunk.get("done"):
            break

    print("\n" + "-" * 60)
    return full_reply


DIFF_SYSTEM_PROMPT = """SYSTEM:
You are a code change analyst. You output ONLY structured documentation — no explanation, no commentary, no filler.

Given a git diff, produce exactly two sections:

1. COMMIT MESSAGE
Follow Conventional Commits spec strictly:
- Format: <type>(<scope>): <short description>
- type: feat | fix | refactor | docs | test | chore | perf
- scope: the module, file, or component affected (infer from diff)
- description: imperative mood, lowercase, no period, max 72 chars
- If warranted, add a body (blank line after subject, wrapped at 72 chars)
- If breaking change, add BREAKING CHANGE: footer

2. CHANGELOG ENTRY
Format as markdown:
## [Unreleased]
### <Category> (Added | Changed | Fixed | Removed | Performance)
- <what changed and why it matters to a user or developer>

---

Rules:
- Infer intent from the code, not just the line changes
- If the diff is ambiguous, say so in the commit body, don't guess silently
- Never fabricate function names or behavior not present in the diff

USER:
Here is the git diff:

<diff>
{diff_content}
</diff>"""


def chat_with_file(file_path: str) -> str:
    diff_content = open(file_path).read()
    diff_content = diff_content[:4000]  # add this line
    prompt = DIFF_SYSTEM_PROMPT.format(diff_content=diff_content)
    return chat(prompt)


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        # Usage: python gemma_ollama.py my_changes.diff.txt
        chat_with_file(sys.argv[1])
    elif len(sys.argv) == 3:
        # Usage: python gemma_ollama.py my_changes.diff.txt "What bugs do you see?"
        chat_with_file(sys.argv[1], sys.argv[2])
    else:
        chat("Explain the difference between a transformer and an RNN in simple terms.")
        chat("Write a Python function that reverses a linked list.")