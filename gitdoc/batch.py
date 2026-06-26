"""Batch mode — generate release notes from a branch."""

import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from .colors import C
from .chunking import truncate_diff
from .ollama import call_ollama
from .pipeline import print_header
from .preanalysis import analyze_diff, format_metadata_context
from .prompts import PROMPT_CHANGELOG


def run_batch(range_spec: str, model: str, output_file: Optional[str]):
    """Process all commits in a branch range and generate release notes."""
    print_header()
    print(f"{C.BOLD}Batch Mode:{C.RESET} Generating release notes for {C.CYAN}{range_spec}{C.RESET}\n")

    try:
        result = subprocess.run(
            ["git", "log", "--oneline", range_spec],
            capture_output=True, text=True, check=True,
        )
        commits = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
    except subprocess.CalledProcessError as e:
        sys.exit(f"{C.RED}Error:{C.RESET} git log failed: {e.stderr}")

    if not commits:
        sys.exit(f"{C.RED}Error:{C.RESET} No commits found in range {range_spec}")

    print(f"  Found {C.BOLD}{len(commits)}{C.RESET} commits\n")

    all_entries = []
    start_time = time.time()
    for i, commit_line in enumerate(commits, 1):
        sha = commit_line.split()[0]
        msg_preview = " ".join(commit_line.split()[1:])[:40]
        print(f"  [{i}/{len(commits)}] {C.DIM}{sha}{C.RESET} {msg_preview}... ", end="", flush=True)

        try:
            diff_result = subprocess.run(
                ["git", "diff", f"{sha}~1..{sha}"],
                capture_output=True, text=True, check=True,
            )
            diff_text = diff_result.stdout
        except subprocess.CalledProcessError:
            # First commit or orphan — try git show
            try:
                diff_result = subprocess.run(
                    ["git", "show", sha, "--format=", "--patch"],
                    capture_output=True, text=True, check=True,
                )
                diff_text = diff_result.stdout
            except subprocess.CalledProcessError:
                diff_text = ""

        if not diff_text.strip():
            print(f"{C.DIM}(empty diff, skipped){C.RESET}")
            continue

        diff_text = truncate_diff(diff_text)
        meta = analyze_diff(diff_text)
        metadata_ctx = format_metadata_context(meta)

        entry_start = time.time()
        output = call_ollama(model, PROMPT_CHANGELOG, f"{metadata_ctx}\n\n[DIFF]\n{diff_text}\n[END DIFF]")
        elapsed = time.time() - entry_start
        all_entries.append(output.strip())
        print(f"{C.GREEN}done{C.RESET} {C.DIM}({elapsed:.1f}s){C.RESET}")

    total_time = time.time() - start_time
    print(f"\n  Processed {len(all_entries)} commits in {total_time:.1f}s")

    release_notes = f"# Release Notes\n\nGenerated from: `{range_spec}`\n\n"
    release_notes += "## [Unreleased]\n\n"

    categories = {"Added": [], "Changed": [], "Fixed": [], "Removed": [], "Performance": []}
    for entry in all_entries:
        for cat in categories:
            if f"### {cat}" in entry:
                lines = entry.split("\n")
                capture = False
                for line in lines:
                    if f"### {cat}" in line:
                        capture = True
                        continue
                    if line.startswith("### "):
                        capture = False
                    if capture and line.startswith("- "):
                        categories[cat].append(line)

    for cat, entries in categories.items():
        if entries:
            release_notes += f"### {cat}\n"
            for e in entries:
                release_notes += f"{e}\n"
            release_notes += "\n"

    if output_file:
        Path(output_file).write_text(release_notes, encoding="utf-8")
        print(f"\n{C.GREEN}Release notes written to:{C.RESET} {output_file}")
    else:
        print(f"\n{C.MAGENTA}{'─' * 64}{C.RESET}")
        print(release_notes)
