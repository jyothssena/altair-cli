"""CLI entry point and main execution logic."""

import argparse
import json
import sys
from pathlib import Path

from .colors import C
from .config import MODEL
from .preanalysis import analyze_diff, format_metadata_context
from .chunking import truncate_diff
from .prompts import PASS_CONFIG
from .pipeline import run_pass, print_header, print_metadata, print_pass_result, print_summary
from .batch import run_batch
from .hook import install_hook


def read_diff(input_path: str) -> str:
    if input_path == "-":
        content = sys.stdin.read()
    else:
        path = Path(input_path)
        if not path.exists():
            sys.exit(f"{C.RED}Error:{C.RESET} File not found: {input_path}")
        if path.stat().st_size == 0:
            sys.exit(f"{C.RED}Error:{C.RESET} File is empty: {input_path}")
        content = path.read_text(encoding="utf-8", errors="replace")

    if not content.strip():
        sys.exit(f"{C.RED}Error:{C.RESET} Input contains no content")
    return content


def parse_args():
    parser = argparse.ArgumentParser(
        prog="gitdoc",
        description="GitDoc — Multi-pass code intelligence pipeline powered by Gemma 3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.diff                     Full pipeline (all 4 passes)
  %(prog)s input.diff --pass commit       Single pass only
  %(prog)s input.diff --pass review       Just code review
  %(prog)s input.diff -o docs.md          Output to file
  %(prog)s --batch main..feature          Release notes for branch
  %(prog)s --install-hook                 Install git hook
  git diff | %(prog)s -                   Read from stdin
        """,
    )
    parser.add_argument("input", nargs="?", help="Path to .diff/.txt file, or '-' for stdin")
    parser.add_argument("-o", "--output", help="Write output to file")
    parser.add_argument("--pass", dest="pass_name", choices=["commit", "changelog", "review", "pr", "all"],
                        default="all", help="Which analysis pass to run (default: all)")
    parser.add_argument("--model", default=MODEL, help=f"Ollama model (default: {MODEL})")
    parser.add_argument("--batch", metavar="RANGE", help="Batch mode: git range like main..feature")
    parser.add_argument("--install-hook", action="store_true", help="Install prepare-commit-msg git hook")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument("--json", action="store_true", help="Output as JSON (for scripting)")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.no_color:
        C.disable()

    if args.install_hook:
        install_hook()
        return

    if args.batch:
        run_batch(args.batch, args.model, args.output)
        return

    if not args.input:
        sys.exit(f"{C.RED}Error:{C.RESET} No input specified. Use --help for usage.")

    diff_text = read_diff(args.input)
    diff_text = truncate_diff(diff_text)
    meta = analyze_diff(diff_text)
    metadata_ctx = format_metadata_context(meta)

    if args.pass_name == "all":
        passes = ["commit", "changelog", "review", "pr"]
    else:
        passes = [args.pass_name]

    if not args.json:
        print_header()
        print_metadata(meta)
        print(f"{C.BOLD}{C.WHITE}Running {len(passes)} analysis pass{'es' if len(passes) > 1 else ''}...{C.RESET}\n")

    results = []
    for i, pass_name in enumerate(passes, 1):
        if not args.json:
            config = PASS_CONFIG[pass_name]
            print(f"  {C.DIM}[{i}/{len(passes)}]{C.RESET} {config['label']}...", end="", flush=True)

        result = run_pass(pass_name, args.model, diff_text, metadata_ctx)
        results.append(result)

        if not args.json:
            _, label, color = result["confidence"]
            print(f" {color}{label}{C.RESET}")

    if args.json:
        json_output = {
            "metadata": {
                "files_changed": len(meta.files),
                "additions": meta.total_additions,
                "deletions": meta.total_deletions,
                "primary_language": meta.primary_language,
                "complexity": meta.complexity_score,
                "change_type": meta.change_type_hint,
            },
            "passes": {
                r["name"]: {
                    "output": r["output"],
                    "confidence": r["confidence"][1],
                }
                for r in results
            },
        }
        output_str = json.dumps(json_output, indent=2)
        if args.output:
            Path(args.output).write_text(output_str, encoding="utf-8")
        else:
            print(output_str)
        return

    print()
    for i, result in enumerate(results, 1):
        print_pass_result(result, i)

    if len(results) > 1:
        print_summary(results)

    if args.output:
        file_content = f"# GitDoc Analysis\n\n"
        file_content += f"**Input:** `{args.input}`\n"
        file_content += f"**Model:** `{args.model}`\n"
        file_content += f"**Files:** {len(meta.files)} | "
        file_content += f"**Complexity:** {meta.complexity_score}/10\n\n"
        for r in results:
            file_content += f"---\n\n## {r['label']}\n\n{r['output']}\n\n"
        Path(args.output).write_text(file_content, encoding="utf-8")
        print(f"{C.GREEN}Full output written to:{C.RESET} {args.output}")
