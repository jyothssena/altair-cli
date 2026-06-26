"""
chunker_raw.py — Split a git diff into per-file chunks.
No filtering. Raw diff lines only.

Usage:
    python chunker_raw.py <diff_file>
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


def build_raw_chunks(file_path: str) -> list:
    diff_text = open(file_path).read()
    raw_chunks = split_diff_by_file(diff_text)

    result = []
    for chunk in raw_chunks:
        first_line = chunk.splitlines()[0] if chunk else ""
        filename = first_line.split(" b/")[-1] if " b/" in first_line else "unknown"
        ext = filename.split(".")[-1] if "." in filename else "unknown"

        result.append({
            "filename": filename,
            "ext": ext,
            "raw_size": len(chunk),
            "context": chunk
        })

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python chunker_raw.py <diff_file>")
        sys.exit(1)

    chunks = build_raw_chunks(sys.argv[1])

    for i, c in enumerate(chunks):
        print(f"\n{'='*60}")
        print(f"[{i+1}/{len(chunks)}] {c['filename']}  ({c['ext']})")
        print(f"  raw size: {c['raw_size']} chars")
        print(f"{'='*60}")
        print(c['context'])