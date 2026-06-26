"""
chunker_smart.py — Split a git diff into per-file chunks
and extract only meaningful changed lines per file type.

Usage:
    python chunker_smart.py <diff_file>
"""

import sys


def split_diff_by_file(diff_text: str) -> list:
    chunks = []
    current = []
    for line in diff_text.splitlines():
        if line.startswith("diff --git") and current:
            chunks.append("\n".join(current))
            current = []
        current.append(line)
    if current:
        chunks.append("\n".join(current))
    return chunks


def extract_meaningful_changes(chunk: str, filename: str) -> list:
    ext = filename.split(".")[-1] if "." in filename else ""
    lines = chunk.splitlines()
    meaningful = []

    CODE_PATTERNS = [
        "def ", "class ", "import ", "from ", "return ",
        "raise ", "async ", "await ", "= ", "if ", "elif ",
        "for ", "while ", "except ", "BREAKING",
    ]

    CONFIG_PATTERNS = [
        '"model"', '"url"', '"host"', '"port"', '"password"',
        '"datasource"', '"target"', '"expr"', '"title"', '"type"',
        "image:", "port:", "environment:", "depends_on:",
        "version:", "service:", "volumes:",
    ]

    for line in lines:
        if not (line.startswith("+") or line.startswith("-")):
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue

        stripped = line[1:].strip()

        if not stripped:
            continue
        if stripped.startswith("#") or stripped.startswith("//"):
            continue

        if ext in ["json", "yml", "yaml"]:
            if any(p in line for p in CONFIG_PATTERNS):
                meaningful.append(line)
            continue

        if any(p in stripped for p in CODE_PATTERNS):
            meaningful.append(line)
            continue

        if len(stripped) > 10 and not stripped.startswith(("}", "{", "]", "[", ")", "(")):
            meaningful.append(line)

    return meaningful


def build_smart_chunks(file_path: str) -> list:
    diff_text = open(file_path).read()
    raw_chunks = split_diff_by_file(diff_text)

    result = []
    for chunk in raw_chunks:
        first_line = chunk.splitlines()[0] if chunk else ""
        filename = first_line.split(" b/")[-1] if " b/" in first_line else "unknown"
        ext = filename.split(".")[-1] if "." in filename else "unknown"

        meaningful_lines = extract_meaningful_changes(chunk, filename)

        result.append({
            "filename": filename,
            "ext": ext,
            "raw_size": len(chunk),
            "meaningful_lines": meaningful_lines,
            "meaningful_size": len("\n".join(meaningful_lines)),
            "context": f"File: {filename}\n" + "\n".join(meaningful_lines)
        })

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python chunker_smart.py <diff_file>")
        sys.exit(1)

    chunks = build_smart_chunks(sys.argv[1])

    for i, c in enumerate(chunks):
        has_changes = len(c['meaningful_lines']) > 0
        status = f"{len(c['meaningful_lines'])} meaningful lines" if has_changes else "no meaningful changes"

        print(f"\n{'='*60}")
        print(f"[{i+1}/{len(chunks)}] {c['filename']}  ({c['ext']})")
        print(f"  raw: {c['raw_size']} chars  →  {status}")
        print(f"{'='*60}")

        if has_changes:
            print(c['context'])
        else:
            print("  [SKIPPED]")