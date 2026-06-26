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

    # Strip markdown fences
    clean = text.strip()
    if clean.startswith(" ⁠"):
        lines = clean.split("\n")
        clean = "\n".join(l for l in lines if not l.startswith("⁠ "))

    has_header = "## [Unreleased]" in clean
    has_category = any(f"### {c}" in clean for c in ("Added", "Changed", "Fixed", "Removed", "Performance"))
    has_entry = bool(re.search(r"^- .+", clean, re.MULTILINE))

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

    clean = text.strip()
    has_risk = bool(re.search(r"\*{0,2}Risk Level:?\*{0,2}\s*(HIGH|MEDIUM|LOW)", clean))
    has_issues = "Issues" in clean or "issues" in clean
    has_security = "Security" in clean or "security" in clean
    has_suggestions = "Suggestion" in clean or "suggestion" in clean

    structure_count = sum([has_issues, has_security, has_suggestions])

    if has_risk and structure_count >= 2:
        return 10, "HIGH", C.GREEN
    if has_risk or structure_count >= 2:
        return 6, "MEDIUM", C.YELLOW
    if structure_count >= 1:
        return 4, "LOW", C.RED
    return 2, "LOW", C.RED



def score_pr(text: str) -> tuple:
    if not text or not text.strip():
        return 0, "FAILED", C.RED

    clean = text.strip()
    has_title = bool(re.search(r"\*{0,2}Title:?\*{0,2}", clean))
    has_summary = bool(re.search(r"\*{0,2}Summary:?\*{0,2}", clean))
    has_risk = bool(re.search(r"\*{0,2}Risk Assessment:?\*{0,2}\s*(HIGH|MEDIUM|LOW)", clean))
    has_changes = "Changes:" in clean or "**Changes:**" in clean
    has_testing = "Testing" in clean or "testing" in clean

    score_count = sum([has_title, has_summary, has_risk, has_changes, has_testing])

    if score_count >= 4:
        return 10, "HIGH", C.GREEN
    if score_count >= 3:
        return 7, "MEDIUM", C.YELLOW
    if score_count >= 1:
        return 4, "LOW", C.RED
    return 1, "FAILED", C.RED

def explain_score(pass_name: str, text: str) -> str:
    """Return human-readable explanation of why a score was given."""
    if pass_name == "commit":
        first_line = (text or "").strip().split("\n")[0] if text else ""
        if not first_line:
            return "Empty output"
        if re.match(r"^(feat|fix|refactor|docs|test|chore|perf)\(.+\): .+", first_line):
            return f"Valid format: {first_line[:60]}"
        return f"Missing type(scope): format. Got: {first_line[:60]}"

    if pass_name == "changelog":
        issues = []
        if "## [Unreleased]" not in (text or ""):
            issues.append("missing '## [Unreleased]' header")
        if not any(f"### {c}" in (text or "") for c in ("Added", "Changed", "Fixed", "Removed", "Performance")):
            issues.append("missing ### Category")
        if "- " not in (text or ""):
            issues.append("missing bullet entries")
        return "; ".join(issues) if issues else "Valid structure"

    return "Scored by section detection"


SCORERS = {
    "commit": score_commit,
    "changelog": score_changelog,
    "review": score_review,
    "pr": score_pr,
}

