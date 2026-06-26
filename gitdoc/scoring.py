"""Confidence scoring — validates LLM output structure."""

import re
from .colors import C


def score_commit(text: str) -> tuple:
    """Validate and score commit message output."""
    if not text or not text.strip():
        return 0, "FAILED", C.RED

    # Strip any markdown fences the model might add
    clean = text.strip()
    if clean.startswith(" ⁠"):
        lines = clean.split("\n")
        clean = "\n".join(l for l in lines if not l.startswith("⁠ "))
    
    first_line = clean.strip().split("\n")[0].strip()
    
    # Strict match: type(scope): description
    strict = r"^(feat|fix|refactor|docs|test|chore|perf)\([a-zA-Z0-9_\-./]+\): .{1,72}$"
    if re.match(strict, first_line):
        return 10, "HIGH", C.GREEN

    # Loose match: type(scope): description (over 72 chars)
    loose = r"^(feat|fix|refactor|docs|test|chore|perf)\([a-zA-Z0-9_\-./]+\): .+"
    if re.match(loose, first_line):
        return 7, "MEDIUM", C.YELLOW

    # Has type but missing scope or colon
    if re.match(r"^(feat|fix|refactor|docs|test|chore|perf)", first_line):
        return 5, "MEDIUM", C.YELLOW

    return 2, "LOW", C.RED



def score_changelog(text: str) -> tuple:
    if not text or not text.strip():
        return 0, "FAILED", C.RED
    has_header = "## [Unreleased]" in text
    has_category = any(f"### {c}" in text for c in ("Added", "Changed", "Fixed", "Removed", "Performance"))
    has_entry = "- " in text
    if has_header and has_category and has_entry:
        return 10, "HIGH", C.GREEN
    if has_category and has_entry:
        return 7, "MEDIUM", C.YELLOW
    if has_entry:
        return 4, "LOW", C.RED
    return 1, "FAILED", C.RED


def score_review(text: str) -> tuple:
    if not text or not text.strip():
        return 0, "FAILED", C.RED
    has_risk = "Risk Level:" in text or "**Risk Level:**" in text
    has_structure = "Issues" in text or "Suggestions" in text or "Security" in text
    if has_risk and has_structure:
        return 10, "HIGH", C.GREEN
    if has_structure:
        return 6, "MEDIUM", C.YELLOW
    return 3, "LOW", C.RED


def score_pr(text: str) -> tuple:
    if not text or not text.strip():
        return 0, "FAILED", C.RED
    has_title = "Title:" in text or "**Title:**" in text
    has_summary = "Summary:" in text or "**Summary:**" in text
    has_risk = "Risk Assessment:" in text or "**Risk Assessment:**" in text
    if has_title and has_summary and has_risk:
        return 10, "HIGH", C.GREEN
    if has_title and has_summary:
        return 7, "MEDIUM", C.YELLOW
    return 3, "LOW", C.RED


SCORERS = {
    "commit": score_commit,
    "changelog": score_changelog,
    "review": score_review,
    "pr": score_pr,
}
