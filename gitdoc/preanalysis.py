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
    primary_language: str = "Unknown"
    change_type_hint: str = "unknown"


def analyze_diff(diff_text: str) -> DiffMetadata:
    """Pre-analyze a diff to extract structured metadata without LLM."""
    meta = DiffMetadata()
    current_file = None

    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            match = re.search(r"b/(.+)$", line)
            if match:
                filepath = match.group(1)
                ext = Path(filepath).suffix.lower()
                lang = LANG_MAP.get(ext, "Unknown")
                is_test = any(t in filepath.lower() for t in ["test", "spec", "_test", "test_"])
                current_file = FileChange(
                    path=filepath,
                    status="modified",
                    language=lang,
                    is_test=is_test,
                )
                meta.files.append(current_file)
                meta.languages.add(lang)
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

    num_files = len(meta.files)
    total_changes = meta.total_additions + meta.total_deletions
    if num_files <= 1 and total_changes < 20:
        meta.complexity_score = 2
    elif num_files <= 3 and total_changes < 100:
        meta.complexity_score = 4
    elif num_files <= 5 and total_changes < 300:
        meta.complexity_score = 6
    elif num_files <= 10:
        meta.complexity_score = 8
    else:
        meta.complexity_score = 10

    if meta.languages - {"Unknown"}:
        lang_counts = {}
        for f in meta.files:
            if f.language != "Unknown":
                lang_counts[f.language] = lang_counts.get(f.language, 0) + f.additions + f.deletions
        if lang_counts:
            meta.primary_language = max(lang_counts, key=lang_counts.get)

    if all(f.status == "added" for f in meta.files):
        meta.change_type_hint = "new feature"
    elif meta.has_tests and not any(not f.is_test for f in meta.files):
        meta.change_type_hint = "test addition"
    elif meta.has_docs and len(meta.files) == 1:
        meta.change_type_hint = "documentation"
    elif meta.total_deletions > meta.total_additions * 2:
        meta.change_type_hint = "refactor/removal"
    elif any("fix" in f.path.lower() or "bug" in f.path.lower() for f in meta.files):
        meta.change_type_hint = "bug fix"
    else:
        meta.change_type_hint = "enhancement"

    return meta


def format_metadata_context(meta: DiffMetadata) -> str:
    """Format metadata as structured context for the LLM."""
    lines = ["[DIFF METADATA]"]
    lines.append(f"Files changed: {len(meta.files)}")
    lines.append(f"Additions: +{meta.total_additions} | Deletions: -{meta.total_deletions}")
    lines.append(f"Languages: {', '.join(sorted(meta.languages - {'Unknown'})) or 'Unknown'}")
    lines.append(f"Primary language: {meta.primary_language}")
    lines.append(f"Complexity: {meta.complexity_score}/10")
    lines.append(f"Change type hint: {meta.change_type_hint}")
    lines.append(f"Includes tests: {'Yes' if meta.has_tests else 'No'}")
    lines.append(f"Includes config: {'Yes' if meta.has_config else 'No'}")
    lines.append("")
    lines.append("[FILES]")
    for f in meta.files:
        lines.append(f"  {f.status.upper():10} {f.path} (+{f.additions}/-{f.deletions}) [{f.language}]")
    lines.append("[END METADATA]")
    return "\n".join(lines)
