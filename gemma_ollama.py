#!/usr/bin/env python3
"""
Automagic Documenter — Git Diff to Conventional Commit + Changelog
Uses Gemma3:4b via Ollama

Setup:
    brew install ollama
    ollama serve &
    ollama pull gemma3:4b

Run:
    python gemma_ollama.py <diff_file>
"""

import sys
import re
import json
import requests

# ── Config ────────────────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "gemma3:4b"
MAX_DIFF_CHARS = 6000  # gemma3:4b context is limited, truncate hard

# ── Prompts ───────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a code change analyst. Output ONLY a valid JSON object.
No explanation. No commentary. No markdown fences. No emoji. No preamble.

Produce exactly this structure:
{
  "COMMIT_MESSAGE": "<type>(<scope>): <description>",
  "CHANGELOG_ENTRY": "## [Unreleased]\\n### <Category>\\n- <what changed and why>"
}

Rules:
- type must be one of: feat | fix | refactor | docs | test | chore | perf
- scope: infer from production files only, ignore test files
- description: imperative mood, lowercase, no period, max 72 chars
- Do not copy text verbatim from History.md or CHANGELOG.md
- Do not use emoji anywhere
- Never fabricate function names or behavior not present in the diff
- For a dependency upgrade with behavior changes use: fix or feat
- Output raw JSON only"""

USER_PROMPT_TEMPLATE = """Here is the git diff:

<diff>
{diff_content}
</diff>

Output only the JSON object."""

# ── Post-processing ───────────────────────────────────────────────────────────

VALID_TYPES = {"feat", "fix", "refactor", "docs", "test", "chore", "perf"}

EMOJI_PATTERN = re.compile(
    r'[\U00010000-\U0010ffff]|'
    r'[\u2600-\u26FF]|'
    r'[\u2700-\u27BF]|'
    r'[\u23E9-\u23F3]|'
    r'[\u25AA-\u25FE]|'
    r'[\u2b50\u2b55\u231a\u231b\u23f0\u23f3]'
)

TYPE_ALIASES = {
    "performance": "perf",
    "feature": "feat",
    "bugfix": "fix",
    "bug": "fix",
    "breaking": "fix",
    "update": "chore",
}

def strip_emoji(text: str) -> str:
    return EMOJI_PATTERN.sub('', text).strip()

def normalize_commit(msg: str) -> str:
    msg = strip_emoji(msg)

    # Normalize word-only types like "Performance: ..." -> "perf: ..."
    for alias, canonical in TYPE_ALIASES.items():
        msg = re.sub(
            rf'^{alias}[\s:]+',
            f'{canonical}: ',
            msg,
            flags=re.IGNORECASE
        )

    # Parse and enforce structure
    match = re.match(r'^(\w+)(\([^)]+\))?:\s*(.*)', msg, re.DOTALL)
    if match:
        type_, scope, desc = match.groups()
        type_ = type_.lower()
        if type_ not in VALID_TYPES:
            # Don't silently discard — flag it
            type_ = f"chore /* REVIEW: '{type_}' not a valid type */"
        scope = scope or ""
        first_line = desc.split('\n')[0].rstrip('.')
        msg = f"{type_}{scope}: {first_line}"

    return msg

def parse_model_output(raw: str) -> dict:
    # Strip markdown fences if model ignored instructions
    cleaned = re.sub(r'```json|```', '', raw).strip()

    # Strip timing noise (llama.cpp leak)
    cleaned = re.sub(r'slot print_timing:.*?t/s', '', cleaned, flags=re.MULTILINE).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Attempt to salvage by finding the first { ... } block
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                return {"error": "Failed to parse model output", "raw": raw}
        else:
            return {"error": "No JSON found in output", "raw": raw}

    if "COMMIT_MESSAGE" in data:
        data["COMMIT_MESSAGE"] = normalize_commit(data["COMMIT_MESSAGE"])

    if "CHANGELOG_ENTRY" in data:
        data["CHANGELOG_ENTRY"] = strip_emoji(data["CHANGELOG_ENTRY"])

    return data

# ── Ollama call ───────────────────────────────────────────────────────────────

def call_ollama(diff_content: str) -> str:
    if len(diff_content) > MAX_DIFF_CHARS:
        diff_content = diff_content[:MAX_DIFF_CHARS] + "\n\n[diff truncated]"
        print(f"[warn] diff truncated to {MAX_DIFF_CHARS} chars", file=sys.stderr)

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": USER_PROMPT_TEMPLATE.format(diff_content=diff_content)},
        ],
        "stream": True,
    }

    response = requests.post(OLLAMA_URL, json=payload, stream=True)
    response.raise_for_status()

    full_reply = ""
    for line in response.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        full_reply += chunk.get("message", {}).get("content", "")
        if chunk.get("done"):
            break

    return full_reply

# ── Entry point ───────────────────────────────────────────────────────────────

def process_diff_file(path: str) -> None:
    try:
        diff_content = open(path).read()
    except FileNotFoundError:
        print(f"[error] file not found: {path}", file=sys.stderr)
        sys.exit(1)

    print(f"[info] sending diff to {MODEL}...", file=sys.stderr)
    raw = call_ollama(diff_content)

    result = parse_model_output(raw)

    if "error" in result:
        print(f"[error] {result['error']}", file=sys.stderr)
        print(result.get("raw", ""), file=sys.stderr)
        sys.exit(1)

    # Clean final output
    print("\n## COMMIT MESSAGE\n")
    print(result["COMMIT_MESSAGE"])
    print("\n## CHANGELOG ENTRY\n")
    print(result["CHANGELOG_ENTRY"])

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python gemma_ollama.py <diff_file>", file=sys.stderr)
        sys.exit(1)

    process_diff_file(sys.argv[1])