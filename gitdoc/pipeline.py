"""Pipeline execution — runs passes and formats output."""

import time

from .colors import C
from .config import MAX_RETRIES
from .ollama import call_ollama
from .prompts import PASS_CONFIG
from .scoring import SCORERS
from .preanalysis import DiffMetadata


def run_pass(pass_name: str, model: str, diff_text: str, metadata_ctx: str) -> dict:
    """Execute a single analysis pass."""
    config = PASS_CONFIG[pass_name]
    user_content = f"{metadata_ctx}\n\n[DIFF]\n{diff_text}\n[END DIFF]"

    result = {"name": pass_name, "label": config["label"], "output": None, "confidence": None}

    for attempt in range(1, MAX_RETRIES + 1):
        output = call_ollama(model, config["prompt"], user_content)
        score, label, color = SCORERS[pass_name](output)

        if score >= 5 or attempt == MAX_RETRIES:
            result["output"] = output.strip()
            result["confidence"] = (score, label, color)
            break
        time.sleep(0.5)

    return result


def print_header():
    print(f"""
{C.BOLD}{C.CYAN}\u2554{'═' * 62}\u2557
║                                                              ║
║   {C.WHITE}GitDoc{C.CYAN} — Code Intelligence Pipeline                       ║
║   {C.DIM}Powered by Gemma 3 via Ollama{C.RESET}{C.BOLD}{C.CYAN}                             ║
║                                                              ║
\u255a{'═' * 62}\u255d{C.RESET}
""")


def print_metadata(meta: DiffMetadata):
    print(f"{C.BOLD}{C.WHITE}┌─ Pre-Analysis ────────────────────────────────────────────────{C.RESET}")
    print(f"{C.DIM}│{C.RESET} Files: {C.BOLD}{len(meta.files)}{C.RESET} | "
          f"+{C.GREEN}{meta.total_additions}{C.RESET} / "
          f"-{C.RED}{meta.total_deletions}{C.RESET} | "
          f"Complexity: {complexity_bar(meta.complexity_score)}")
    print(f"{C.DIM}│{C.RESET} Language: {C.CYAN}{meta.primary_language}{C.RESET} | "
          f"Type: {C.YELLOW}{meta.change_type_hint}{C.RESET}")
    for f in meta.files[:8]:
        status_color = {
            "added": C.GREEN, "deleted": C.RED,
            "modified": C.YELLOW, "renamed": C.BLUE,
        }.get(f.status, C.WHITE)
        print(f"{C.DIM}│{C.RESET}   {status_color}{f.status:>8}{C.RESET}  {f.path}")
    if len(meta.files) > 8:
        print(f"{C.DIM}│{C.RESET}   ... and {len(meta.files) - 8} more files")
    print(f"{C.BOLD}{C.WHITE}└───────────────────────────────────────────────────────────────{C.RESET}\n")


def complexity_bar(score: int) -> str:
    filled = score
    empty = 10 - score
    if score <= 3:
        color = C.GREEN
    elif score <= 6:
        color = C.YELLOW
    else:
        color = C.RED
    return f"{color}{'█' * filled}{'░' * empty}{C.RESET} {score}/10"


def print_pass_result(result: dict, index: int):
    config = PASS_CONFIG[result["name"]]
    score, label, color = result["confidence"]
    badge = f"{color}{C.BOLD}[{label}]{C.RESET}"

    print(f"{C.BOLD}{C.MAGENTA}{'─' * 64}{C.RESET}")
    print(f"{C.BOLD}{C.WHITE} Pass {index}: {config['label']}{C.RESET}  Confidence: {badge}")
    print(f"{C.MAGENTA}{'─' * 64}{C.RESET}")
    print()
    print(result["output"])
    print()


def print_summary(results: list):
    print(f"\n{C.BOLD}{C.CYAN}{'═' * 64}")
    print(f" PIPELINE SUMMARY")
    print(f"{'═' * 64}{C.RESET}\n")

    for r in results:
        score, label, color = r["confidence"]
        status = f"{color}● {label}{C.RESET}"
        print(f"  {status:>30}  {r['label']}")

    overall_scores = [r["confidence"][0] for r in results]
    avg = sum(overall_scores) / len(overall_scores) if overall_scores else 0
    if avg >= 8:
        overall = f"{C.GREEN}{C.BOLD}EXCELLENT{C.RESET}"
    elif avg >= 5:
        overall = f"{C.YELLOW}{C.BOLD}GOOD{C.RESET}"
    else:
        overall = f"{C.RED}{C.BOLD}NEEDS REVIEW{C.RESET}"

    print(f"\n  Overall Quality: {overall} ({avg:.1f}/10)")
    print()
