#!/usr/bin/env python3
"""
GitDoc — The Complete Code Intelligence Pipeline

Usage:
    python gemma_ollama.py input.diff                    # Full pipeline
    python gemma_ollama.py input.diff --pass commit      # Single pass
    python gemma_ollama.py input.diff -o output.md       # Write to file
    python gemma_ollama.py --batch main..feature-branch  # Release notes
    python gemma_ollama.py --install-hook                # Git hook setup
    git diff HEAD~1 | python gemma_ollama.py -           # Stdin
"""

from gitdoc.cli import main

if __name__ == "__main__":
    main()
