# Altair — The Automagic Documenter

> A multi-pass code intelligence pipeline that transforms raw git diffs into structured documentation using Google Gemma 3 (4B) via Ollama.
>
> *Named after Altair — the brightest star in the Aquila constellation — guiding developers through the darkness of undocumented code.*

**GDG Hackathon 2026 — Track 1: Git-to-Doc**

---

## The Problem

Developers write terrible commit messages, skip changelogs, and rarely document their code changes properly. Manual documentation is friction that slows teams down.

## The Solution

Altair takes a raw `.diff` file and runs it through a **5-stage intelligent pipeline**:

```
                    ┌─────────────────┐
   .diff input ──> │  Pre-Analysis   │ ── metadata extraction (pure Python)
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Smart Chunker  │ ── function-boundary splitting
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼──┐  ┌───────▼───┐   ┌──────▼──────┐
     │  Pass 1   │  │  Pass 2   │   │  Pass 3/4   │
     │  Commit   │  │ Changelog │   │ Review / PR │
     └────────┬──┘  └───────┬───┘   └──────┬──────┘
              │              │             │
              └──────────────┼─────────────┘
                             │
                    ┌────────▼────────┐
                    │   Validation    │ ── confidence scoring + retry
                    └────────┬────────┘
                             │
                        Structured Output
```

---

## Features

| Feature | Description |
|---------|-------------|
| **Multi-pass Pipeline** | 4 specialized passes: commit message, changelog, code review, PR description |
| **Pre-analysis Engine** | Pure Python metadata extraction — languages, complexity, change types — before LLM call |
| **Smart Chunking** | Function-boundary splitting for large diffs, hunk-aware truncation within context limits |
| **Confidence Scoring** | Validates LLM output structure, assigns HIGH/MEDIUM/LOW confidence, auto-retries on LOW |
| **Batch Mode** | Process entire branch range into consolidated release notes |
| **Git Hook** | `prepare-commit-msg` hook auto-generates commit messages on every `git commit` |
| **JSON Output** | Machine-readable output for CI/CD integration |
| **Edge Case Hardening** | Handles empty files, binary content, oversized diffs, Ollama failures gracefully |
| **Rich Terminal UI** | Colored output with progress indicators, complexity bars, pipeline summary |

---

## Quick Start

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/) installed and running
- Gemma 3 model pulled: `ollama pull gemma3:4b`

### Setup

```bash
git clone https://github.com/jyothssena/GDG_Hackathon_track1.git
cd GDG_Hackathon_track1
pip install -r requirements.txt
ollama serve  # in another terminal
```

### Usage

```bash
# Full pipeline (all 4 passes)
python gemma_ollama.py samples/sample1_parser_fix.diff

# Single pass
python gemma_ollama.py input.diff --pass commit
python gemma_ollama.py input.diff --pass changelog
python gemma_ollama.py input.diff --pass review
python gemma_ollama.py input.diff --pass pr

# From stdin (pipe git diff directly)
git diff | python gemma_ollama.py -

# JSON output for scripting
python gemma_ollama.py input.diff --json

# Batch mode — release notes from branch
python gemma_ollama.py --batch main..feature-branch

# Install git hook
python gemma_ollama.py --install-hook

# Write output to file
python gemma_ollama.py input.diff -o output.md

# Verbose mode (debug metadata)
python gemma_ollama.py input.diff -v
```

---

## Architecture

```
GDG_Hackathon_track1/
├── gemma_ollama.py          # Entry point
├── gitdoc/                  # Core package
│   ├── __init__.py
│   ├── config.py            # Environment-configurable settings
│   ├── colors.py            # ANSI terminal colors
│   ├── preanalysis.py       # Diff metadata extraction (45+ languages)
│   ├── chunking.py          # Function-boundary splitter + truncation
│   ├── prompts.py           # Specialized system prompts per pass
│   ├── ollama.py            # Ollama API with retry logic
│   ├── scoring.py           # Output validation + confidence scoring
│   ├── pipeline.py          # Pass orchestration + terminal UI
│   ├── batch.py             # Batch mode (branch → release notes)
│   ├── hook.py              # Git hook installer
│   └── cli.py               # Argument parsing + main logic
├── samples/                 # Test diff files
│   ├── sample1_parser_fix.diff
│   ├── sample2_auth_middleware.diff
│   ├── sample3_new_cache.diff
│   ├── sample4_multi_file_feature.diff
│   └── sample5_refactor_deletion.diff
├── edge_cases/              # 24 edge-case test diffs
├── run_edges.sh             # Edge case test runner
└── requirements.txt         # Dependencies (requests>=2.28.0)
```

---

## How It Works

### 1. Pre-Analysis (No LLM)

Before calling the model, Altair extracts structured metadata using pure Python:
- Files changed, additions/deletions per file
- Language detection (45+ file extensions)
- Complexity scoring (1-10 scale based on files, lines, languages)
- Change type inference (feat/fix/refactor/docs/test/chore)

This metadata is prepended to the LLM prompt as context.

### 2. Smart Chunking

Large diffs are intelligently split to stay within model context:
- Split by file boundaries
- For large code files: split by function/class boundaries (`def`, `class`, `async def`)
- Preserve diff headers during truncation
- Hard cut at line boundaries as last resort

### 3. Multi-Pass LLM Pipeline

Each pass uses a specialized system prompt optimized for its output format:

| Pass | Output | Validation |
|------|--------|------------|
| `commit` | Conventional Commit message | Regex: `type(scope): description` |
| `changelog` | Keep a Changelog entry | Checks: header, category, bullets |
| `review` | Code review with risk level | Checks: risk level, issues, suggestions |
| `pr` | PR description | Checks: title, summary, risk, changes |

### 4. Confidence Scoring & Retry

Each output is validated against structural rules:
- **HIGH** (8-10): Perfect format, all required sections present
- **MEDIUM** (5-7): Mostly correct, minor format issues
- **LOW** (1-4): Auto-retry up to 3 times

### 5. Batch Mode

Process an entire branch into consolidated release notes:
```bash
python gemma_ollama.py --batch main..feature-branch -o RELEASE_NOTES.md
```
- Iterates all commits in range
- Handles first-commit (no parent) gracefully
- Shows per-commit timing and progress
- Categorizes entries (Added/Changed/Fixed/Removed/Performance)

---

## Configuration

Environment variables for customization:

| Variable | Default | Description |
|----------|---------|-------------|
| `GITDOC_OLLAMA_URL` | `http://localhost:11434/api/chat` | Ollama API endpoint |
| `GITDOC_MODEL` | `gemma3:4b` | Model to use |
| `GITDOC_MAX_CHARS` | `12000` | Max diff chars per chunk |

Environment variable prefix `GITDOC_` kept for backward compatibility (rename to `ALTAIR_` planned).

---

## Sample Output

```
╔══════════════════════════════════════════════════════════════╗
║   Altair — Code Intelligence Pipeline                       ║
║   Powered by Gemma 3 via Ollama                             ║
╚══════════════════════════════════════════════════════════════╝

┌─ Pre-Analysis ────────────────────────────────────────────────
│ Files: 1 | +14 / -3 | Complexity: █░░░░░░░░░ 1/10
│ Language: Python | Type: feat
│   modified  app/auth/middleware.py
└───────────────────────────────────────────────────────────────

Running 4 analysis passes...

  [1/4] Commit Message... HIGH
  [2/4] Changelog... HIGH
  [3/4] Code Review... HIGH
  [4/4] PR Description... HIGH

════════════════════════════════════════════════════════════════
 PIPELINE SUMMARY
════════════════════════════════════════════════════════════════

  ● HIGH  Commit Message
  ● HIGH  Changelog
  ● HIGH  Code Review
  ● HIGH  PR Description

  Overall Quality: EXCELLENT (10.0/10)
```

---

## Design Decisions

1. **Local-first**: Everything runs on-device via Ollama. No cloud APIs, no data leaves the machine.
2. **Model-agnostic**: Works with any Ollama model (`--model` flag). Defaults to Gemma 3 4B.
3. **Pre-analysis before LLM**: Structured metadata reduces hallucination and improves output quality.
4. **Retry with validation**: Don't trust LLM output blindly — validate structure and retry on failure.
5. **Modular architecture**: Each component is independently testable and swappable.

---

## Team

| Member | Focus Area |
|--------|-----------|
| Stephy | Prompt engineering & tuning |
| Kunal | Edge case hardening & error handling |
| Kshitij | Git hook, batch mode, JSON validation |
| Jyothssena | Validation scoring & explain_score |
| Tanmayi | Pre-analysis engine & smart chunking |

---

## License

Built for GDG Hackathon 2026. MIT License.

---

> *"Altair" — Arabic for "the flying one." Like the star, this tool soars above messy diffs to illuminate what truly changed.*
