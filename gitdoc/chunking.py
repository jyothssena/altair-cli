"""Smart chunking — split and prioritize large diffs to fit model context."""

import re
from .config import MAX_DIFF_CHARS


def split_diff_by_file(diff: str) -> list:
    """Split a unified diff into per-file chunks.
    Returns list of dicts: {file, content}
    """
    chunks = []
    current_chunk = []
    current_file = None

    for line in diff.split("\n"):
        if line.startswith("diff --git"):
            if current_chunk:
                chunks.append({"file": current_file, "content": "\n".join(current_chunk)})
            current_chunk = [line]
            match = re.search(r"b/(.+)$", line)
            current_file = match.group(1) if match else "unknown"
        else:
            current_chunk.append(line)

    if current_chunk:
        chunks.append({"file": current_file, "content": "\n".join(current_chunk)})

    return chunks


def split_by_function_boundary(file_chunk: dict) -> list:
    """Split a single large file chunk by function/class boundaries.
    
    Scans for 'def ' and 'class ' lines in added/removed lines.
    Each function/class block becomes its own chunk.
    If a single block is still > MAX_DIFF_CHARS, hard cut at line boundary.
    """
    content = file_chunk["content"]
    filename = file_chunk["file"]
    lines = content.split("\n")

    blocks = []
    current_block = []
    current_label = f"{filename} — header"

    for line in lines:
        stripped = line[1:].strip() if line.startswith(("+", "-")) else line.strip()

        # new function or class boundary
        if stripped.startswith("def ") or stripped.startswith("class ") or stripped.startswith("async def "):
            if current_block:
                blocks.append({
                    "file": filename,
                    "label": current_label,
                    "content": "\n".join(current_block)
                })
            current_label = f"{filename} — {stripped.split('(')[0].strip()}"
            current_block = [line]
        else:
            current_block.append(line)

    if current_block:
        blocks.append({
            "file": filename,
            "label": current_label,
            "content": "\n".join(current_block)
        })

    # hard cut any block still over MAX_DIFF_CHARS
    result = []
    for block in blocks:
        if len(block["content"]) <= MAX_DIFF_CHARS:
            result.append(block)
        else:
            lines = block["content"].split("\n")
            part = []
            char_count = 0
            part_num = 1
            for line in lines:
                if char_count + len(line) + 1 > MAX_DIFF_CHARS:
                    result.append({
                        "file": filename,
                        "label": f"{block['label']} (part {part_num})",
                        "content": "\n".join(part)
                    })
                    part = [line]
                    char_count = len(line)
                    part_num += 1
                else:
                    part.append(line)
                    char_count += len(line) + 1
            if part:
                result.append({
                    "file": filename,
                    "label": f"{block['label']} (part {part_num})",
                    "content": "\n".join(part)
                })

    return result


def truncate_file_chunk(chunk_content: str, max_chars: int) -> str:
    """Truncate a single file's diff, preserving diff headers."""
    if len(chunk_content) <= max_chars:
        return chunk_content

    lines = chunk_content.split("\n")

    # preserve diff header lines before first @@
    header_lines = []
    content_lines = []
    past_header = False

    for line in lines:
        if not past_header and (line.startswith("diff ") or line.startswith("index ") or
                                line.startswith("--- ") or line.startswith("+++ ") or
                                line.startswith("new file") or line.startswith("deleted file")):
            header_lines.append(line)
        else:
            past_header = True
            content_lines.append(line)

    result = header_lines[:]
    char_count = sum(len(l) + 1 for l in result)

    for line in content_lines:
        if char_count + len(line) + 1 > max_chars:
            result.append("    [... truncated ...]")
            break
        result.append(line)
        char_count += len(line) + 1

    return "\n".join(result)


def chunk_diff(diff: str) -> list:
    """
    MAIN FUNCTION — call this from outside.
    
    Takes raw diff text, returns list of strings ready for Gemma.
    
    Steps:
      1. If diff <= 12K → return as single item list
      2. Split by file
      3. If file <= 12K → keep as is
      4. If file > 12K → split by function/class boundary
         If single function > 12K → hard cut at line boundary
    
    Returns:
        list of strings — each string is one chunk ready to pass to Gemma
    """

    # STEP 1 — size check
    if len(diff) <= MAX_DIFF_CHARS:
        return [diff]

    # STEP 2 — split by file
    file_chunks = split_diff_by_file(diff)
    result = []

    for file_chunk in file_chunks:
        content = file_chunk["content"]
        filename = file_chunk["file"]

        # STEP 3 — file fits within limit
        if len(content) <= MAX_DIFF_CHARS:
            result.append(content)

        # STEP 4 — file too large, split by function boundary
        else:
            ext = filename.split(".")[-1].lower() if "." in filename else ""

            # function boundary splitting for code files
            if ext in ["py", "js", "ts", "jsx", "tsx", "go", "rs", "java", "rb", "php"]:
                sub_chunks = split_by_function_boundary(file_chunk)
                for sub in sub_chunks:
                    result.append(sub["content"])
            else:
                # for non-code files (json, yml etc) — hard cut preserving headers
                result.append(truncate_file_chunk(content, MAX_DIFF_CHARS))

    return result


def truncate_diff(diff: str) -> str:
    """Legacy single-string output for backwards compatibility.
    Prefer chunk_diff() for new code.
    """
    chunks = chunk_diff(diff)
    return "\n".join(chunks)[:MAX_DIFF_CHARS]