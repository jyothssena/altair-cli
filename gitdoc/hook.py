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

if [ -n "$COMMIT_SOURCE" ]; then
    exit 0
fi

DIFF=$(git diff --cached)
if [ -z "$DIFF" ]; then
    exit 0
fi

echo "[GitDoc] Generating commit message..."
SCRIPT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
MSG=$(echo "$DIFF" | python3 "$SCRIPT_DIR/gemma_ollama.py" - --pass commit --no-color 2>/dev/null)

if [ -n "$MSG" ] && [ "$?" -eq 0 ]; then
    echo "$MSG" > "$COMMIT_MSG_FILE"
    echo "[GitDoc] Commit message generated. Edit if needed."
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
