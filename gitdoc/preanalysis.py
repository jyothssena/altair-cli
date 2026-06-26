"""Pre-analysis engine — extracts structured metadata from diffs without LLM."""

import re
from dataclasses import dataclass, field
from pathlib import Path

LANG_MAP = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".jsx": "React JSX", ".tsx": "React TSX", ".go": "Go",
    ".rs": "Rust", ".java": "Java", ".rb": "Ruby", ".php": "PHP",
    ".c": "C", ".cpp": "C++", ".cc": "C++", ".h": "C/C++ Header",
    ".hpp": "C++ Header", ".cs": "C#", ".swift": "Swift",
    ".kt": "Kotlin", ".kts": "Kotlin Script", ".scala": "Scala",
    ".html": "HTML", ".css": "CSS", ".scss": "SCSS", ".less": "LESS",
    ".sql": "SQL", ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
    ".yml": "YAML", ".yaml": "YAML", ".json": "JSON",
    ".md": "Markdown", ".rst": "reStructuredText",
    ".toml": "TOML", ".ini": "INI", ".cfg": "Config",
    ".xml": "XML", ".proto": "Protobuf", ".graphql": "GraphQL",
    ".dockerfile": "Docker", ".tf": "Terraform", ".hcl": "HCL",
    ".vue": "Vue", ".svelte": "Svelte", ".dart": "Dart",
    ".r": "R", ".jl": "Julia", ".lua": "Lua", ".ex": "Elixir",
    ".erl": "Erlang", ".zig": "Zig", ".nim": "Nim",
}

# ── Change type signal patterns ───────────────────────────────────
TEST_SIGNALS = [
    "test", "spec", "_test", ".test", "tests/", "__tests__/"
]

DOCS_SIGNALS = [
    "readme", "changelog", "contributing", "license",
    "docs/", "documentation/", ".md", ".rst"
]

CHORE_SIGNALS = [
    "requirements", "dockerfile", "makefile", ".env",
    ".github/", "ci/", "scripts/", ".circleci/", "workflows/",
    "package.json", "go.mod", "gemfile", "cargo.toml",
    "pyproject.toml", "docker-compose"
]

FEAT_YAML_PATHS = [
    "monitoring/", "grafana/", "dashboards/", "alerts/"
]

CHANGE_TYPE_PRIORITY = ["test", "docs", "feat", "refactor", "chore", "fix"]


@dataclass
class FileChange:
    path: str
    status: str
    additions: int = 0
    deletions: int = 0
    language: str = "Unknown"
    is_test: bool = False


@dataclass
class DiffMetadata:
    files: list = field(default_factory=list)
    total_additions: int = 0
    total_deletions: int = 0
    languages: set = field(default_factory=set)
    has_tests: bool = False
    has_config: bool = False
    has_docs: bool = False
    complexity_score: int = 0
    complexity_label: str = "LOW"
    primary_language: str = "Unknown"
    change_type_hint: str = "unknown"
    change_type_signals: list = field(default_factory=list)


# ── Complexity score (swappable) ──────────────────────────────────
def calculate_complexity(
    total_files: int,
    total_lines: int,
    num_languages: int,
    num_file_types: int
) -> dict:
    """
    Placeholder complexity scorer — returns score out of 10 and label.
    SWAP THIS FUNCTION when friend's code is ready.
    Inputs and output contract must stay the same:
        inputs:  total_files, total_lines, num_languages, num_file_types
        output:  { "score": int (1-10), "label": "LOW" | "MED" | "HIGH" }
    """
    score = 1

    if total_files >= 10:
        score += 4
    elif total_files >= 5:
        score += 3
    elif total_files >= 3:
        score += 2
    elif total_files >= 2:
        score += 1

    if total_lines >= 500:
        score += 3
    elif total_lines >= 200:
        score += 2
    elif total_lines >= 50:
        score += 1

    if num_languages >= 3:
        score += 2
    elif num_languages >= 2:
        score += 1

    if num_file_types > 2:
        score += 1

    score = min(score, 10)

    if score <= 3:
        label = "LOW"
    elif score <= 6:
        label = "MED"
    else:
        label = "HIGH"

    return {"score": score, "label": label}


# ── Change type signal detection ──────────────────────────────────
def detect_signals_for_file(filename: str, ext: str,
                             added: int, removed: int) -> list:
    signals = []
    fname = filename.lower()

    if any(s in fname for s in TEST_SIGNALS):
        signals.append("test")

    if any(s in fname for s in DOCS_SIGNALS):
        signals.append("docs")

    if ext in [".yml", ".yaml"]:
        if any(p in fname for p in FEAT_YAML_PATHS):
            signals.append("feat")
        else:
            signals.append("chore")
    elif any(s in fname for s in CHORE_SIGNALS):
        signals.append("chore")

    if removed > added * 2 and added > 0:
        signals.append("refactor")

    if added > removed * 2:
        signals.append("feat")

    if not signals:
        signals.append("fix")

    return signals


def pick_dominant_type(all_signals: list) -> str:
    for change_type in CHANGE_TYPE_PRIORITY:
        if change_type in all_signals:
            return change_type
    return "fix"


def analyze_diff(diff_text: str) -> DiffMetadata:
    """Pre-analyze a diff to extract structured metadata without LLM."""
    meta = DiffMetadata()
    current_file = None
    all_signals = []
    file_types = set()

    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            match = re.search(r"b/(.+)$", line)
            if match:
                filepath = match.group(1)
                ext = Path(filepath).suffix.lower()
                lang = LANG_MAP.get(ext, "Unknown")
                is_test = any(t in filepath.lower() for t in TEST_SIGNALS)
                current_file = FileChange(
                    path=filepath,
                    status="modified",
                    language=lang,
                    is_test=is_test,
                )
                meta.files.append(current_file)
                meta.languages.add(lang)
                file_types.add(ext)

                if is_test:
                    meta.has_tests = True
                if ext in (".yml", ".yaml", ".toml", ".json", ".cfg", ".ini"):
                    meta.has_config = True
                if ext in (".md", ".rst", ".txt"):
                    meta.has_docs = True

        elif line.startswith("new file"):
            if current_file:
                current_file.status = "added"
        elif line.startswith("deleted file"):
            if current_file:
                current_file.status = "deleted"
        elif line.startswith("rename from"):
            if current_file:
                current_file.status = "renamed"
        elif line.startswith("+") and not line.startswith("+++"):
            if current_file:
                current_file.additions += 1
                meta.total_additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            if current_file:
                current_file.deletions += 1
                meta.total_deletions += 1

    # collect signals per file
    for f in meta.files:
        ext = Path(f.path).suffix.lower()
        signals = detect_signals_for_file(f.path, ext, f.additions, f.deletions)
        all_signals.extend(signals)

    # deduplicate signals preserving order
    seen = set()
    unique_signals = []
    for s in all_signals:
        if s not in seen:
            seen.add(s)
            unique_signals.append(s)

    meta.change_type_signals = unique_signals
    meta.change_type_hint = pick_dominant_type(unique_signals)

    # complexity scoring
    complexity = calculate_complexity(
        total_files=len(meta.files),
        total_lines=meta.total_additions + meta.total_deletions,
        num_languages=len(meta.languages - {"Unknown"}),
        num_file_types=len(file_types)
    )
    meta.complexity_score = complexity["score"]
    meta.complexity_label = complexity["label"]

    # primary language by most changed lines
    if meta.languages - {"Unknown"}:
        lang_counts = {}
        for f in meta.files:
            if f.language != "Unknown":
                lang_counts[f.language] = lang_counts.get(f.language, 0) + f.additions + f.deletions
        if lang_counts:
            meta.primary_language = max(lang_counts, key=lang_counts.get)

    return meta


def format_metadata_context(meta: DiffMetadata) -> str:
    """Format metadata as structured context for the LLM."""
    lines = ["[DIFF METADATA]"]
    lines.append(f"Files changed: {len(meta.files)}")
    lines.append(f"Additions: +{meta.total_additions} | Deletions: -{meta.total_deletions}")
    lines.append(f"Languages: {', '.join(sorted(meta.languages - {'Unknown'})) or 'Unknown'}")
    lines.append(f"Primary language: {meta.primary_language}")
    lines.append(f"Complexity: {meta.complexity_score}/10 ({meta.complexity_label})")
    lines.append(f"Change type hint: {meta.change_type_hint}")
    lines.append(f"Change type signals: {', '.join(meta.change_type_signals)}")
    lines.append(f"Includes tests: {'Yes' if meta.has_tests else 'No'}")
    lines.append(f"Includes config: {'Yes' if meta.has_config else 'No'}")
    lines.append("")
    lines.append("[FILES]")
    for f in meta.files:
        lines.append(f"  {f.status.upper():10} {f.path} (+{f.additions}/-{f.deletions}) [{f.language}]")
    lines.append("[END METADATA]")
    return "\n".join(lines)