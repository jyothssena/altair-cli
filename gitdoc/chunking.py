"""Smart chunking — split and prioritize large diffs to fit model context."""

import re
from .config import MAX_DIFF_CHARS


def split_diff_by_file(diff: str) -> list:
    """Split a unified diff into per-file chunks."""
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


def truncate_file_chunk(chunk_content: str, max_chars: int) -> str:
    """Truncate a single file's diff at line boundaries."""
    if len(chunk_content) <= max_chars:
        return chunk_content

    lines = chunk_content.split("\n")
    result = []
    char_count = 0

    for line in lines:
        if char_count + len(line) + 1 > max_chars:
            result.append("    [... remaining lines in this file truncated ...]")
            break
        result.append(line)
        char_count += len(line) + 1

    return "\n".join(result)


def truncate_diff(diff: str) -> str:
    """Intelligently chunk large diffs by file priority.

    Strategy:
    1. Split diff into per-file chunks
    2. Sort by change size (most changes first = most important)
    3. Include files until budget is exhausted
    4. Always include all file headers so the model sees full scope
    """
    if len(diff) <= MAX_DIFF_CHARS:
        return diff

    chunks = split_diff_by_file(diff)
    if not chunks:
        return diff[:MAX_DIFF_CHARS]

    for chunk in chunks:
        change_lines = sum(
            1 for line in chunk["content"].split("\n")
            if (line.startswith("+") and not line.startswith("+++")) or
               (line.startswith("-") and not line.startswith("---"))
        )
        chunk["score"] = change_lines
        chunk["size"] = len(chunk["content"])

    chunks.sort(key=lambda c: c["score"], reverse=True)

    hard_limit = MAX_DIFF_CHARS - 500
    result_parts = []
    chars_used = 0
    files_included = 0
    files_truncated = 0

    for chunk in chunks:
        if chars_used >= hard_limit:
            break

        space_left = hard_limit - chars_used

        if space_left < 200:
            break

        if chunk["size"] <= space_left:
            result_parts.append(chunk["content"])
            chars_used += chunk["size"]
        else:
            result_parts.append(truncate_file_chunk(chunk["content"], space_left))
            chars_used += space_left
            files_truncated += 1

        files_included += 1

    files_skipped = len(chunks) - files_included

    output = "\n".join(result_parts)

    footer_parts = []
    if files_truncated > 0:
        footer_parts.append(f"{files_truncated} file(s) partially shown")
    if files_skipped > 0:
        skipped_names = [c["file"] for c in chunks[files_included:files_included + 5] if c["file"]]
        unique_skipped = list(dict.fromkeys(skipped_names))[:5]
        extra = f" +{files_skipped - len(unique_skipped)} more" if files_skipped > len(unique_skipped) else ""
        footer_parts.append(f"{files_skipped} file(s) omitted: {', '.join(unique_skipped)}{extra}")

    if footer_parts:
        output += f"\n\n[CHUNKING: {'; '.join(footer_parts)}. Total: {len(chunks)} files]"

    return output[:MAX_DIFF_CHARS]
