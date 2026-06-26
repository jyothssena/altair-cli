"""Git hook installer — prepare-commit-msg."""

import os
import stat
import subprocess
import sys
from pathlib import Path

from .colors import C

HOOK_SCRIPT = '''#!/bin/sh
# GitDoc — Auto-generate commit message from staged changes
# Installed by: python gemma_ollama.py --install-hook

COMMIT_MSG_FILE="$1"
COMMIT_SOURCE="$2"

# Only run for regular commits (not merge, squash, amend)
if [ -n "$COMMIT_SOURCE" ]; then
    exit 0
fi

DIFF=$(git diff --cached)
if [ -z "$DIFF" ]; then
    exit 0
fi

# Find the script relative to the hook location
SCRIPT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

if [ ! -f "$SCRIPT_DIR/gemma_ollama.py" ]; then
    echo "[GitDoc] Warning: gemma_ollama.py not found at $SCRIPT_DIR"
    exit 0
fi

echo "[GitDoc] Generating commit message from staged changes..."
MSG=$(echo "$DIFF" | python3 "$SCRIPT_DIR/gemma_ollama.py" - --pass commit --no-color 2>/dev/null)

if [ -n "$MSG" ] && [ $? -eq 0 ]; then
    # Prepend generated message, keep any existing content as comment
    EXISTING=$(cat "$COMMIT_MSG_FILE")
    echo "$MSG" > "$COMMIT_MSG_FILE"
    if [ -n "$EXISTING" ]; then
        echo "" >> "$COMMIT_MSG_FILE"
        echo "# Original message:" >> "$COMMIT_MSG_FILE"
        echo "# $EXISTING" >> "$COMMIT_MSG_FILE"
    fi
    echo "[GitDoc] Done. Edit the message or save to accept."
else
    echo "[GitDoc] Could not generate message. Write your own."
fi
'''


def install_hook():
    """Install prepare-commit-msg hook in the current git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, text=True, check=True,
        )
        git_dir = Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        sys.exit(f"{C.RED}Error:{C.RESET} Not inside a git repository")

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    hook_path = hooks_dir / "prepare-commit-msg"

    if hook_path.exists():
        print(f"{C.YELLOW}Warning:{C.RESET} Hook already exists at {hook_path}")
        print(f"  Overwriting with GitDoc hook...")

    hook_path.write_text(HOOK_SCRIPT, encoding="utf-8")
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)

    print(f"""
{C.GREEN}{C.BOLD}Git hook installed successfully!{C.RESET}

  Location: {hook_path}

  Now every time you run {C.BOLD}git commit{C.RESET}, GitDoc will
  auto-generate a Conventional Commit message from your
  staged changes.

  The message is pre-filled — edit it before confirming.
  To bypass: {C.DIM}git commit --no-verify{C.RESET}
""")
