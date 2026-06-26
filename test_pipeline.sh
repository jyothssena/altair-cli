#!/bin/bash
# test_pipeline.sh — Automated test suite for Altair
# Tests all input modes, edge cases, and output formats.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

PASS=0
FAIL=0
SKIP=0

pass() { echo -e "  ${GREEN}PASS${NC} $1"; PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}FAIL${NC} $1 — $2"; FAIL=$((FAIL + 1)); }
skip() { echo -e "  ${YELLOW}SKIP${NC} $1 — $2"; SKIP=$((SKIP + 1)); }

echo ""
echo -e "${BOLD}Altair — Test Suite${NC}"
echo -e "${DIM}────────────────────────────────────────${NC}"
echo ""

# ── Prerequisite check ────────────────────────────────────────────────────────

echo -e "${BOLD}[Prerequisites]${NC}"

if ! command -v python3 &> /dev/null; then
    fail "Python3" "not installed"
    exit 1
fi
pass "Python3 found"

if ! python3 -c "import requests" 2>/dev/null; then
    fail "requests module" "not installed (run: pip install -r requirements.txt)"
    exit 1
fi
pass "requests module"

if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    skip "Ollama" "not running — LLM tests will be skipped"
    OLLAMA=0
else
    pass "Ollama running"
    OLLAMA=1
fi

echo ""

# ── 1. CLI Help & Args ───────────────────────────────────────────────────────

echo -e "${BOLD}[1] CLI Arguments${NC}"

python3 gemma_ollama.py --help > /dev/null 2>&1 && pass "--help" || fail "--help" "non-zero exit"

OUT=$(python3 gemma_ollama.py 2>&1 || true)
echo "$OUT" | grep -q "No input specified" && pass "no input → error" || fail "no input" "expected error message"

OUT=$(python3 gemma_ollama.py nonexistent.diff 2>&1 || true)
echo "$OUT" | grep -q "File not found" && pass "missing file → error" || fail "missing file" "expected 'File not found'"

touch /tmp/altair_empty.diff
OUT=$(python3 gemma_ollama.py /tmp/altair_empty.diff 2>&1 || true)
echo "$OUT" | grep -q "File is empty" && pass "empty file → error" || fail "empty file" "expected 'File is empty'"
rm -f /tmp/altair_empty.diff

printf '\x00\x01\x02\x03' > /tmp/altair_binary.diff
OUT=$(python3 gemma_ollama.py /tmp/altair_binary.diff 2>&1 || true)
echo "$OUT" | grep -q "binary" && pass "binary file → error" || fail "binary file" "expected binary error"
rm -f /tmp/altair_binary.diff

echo ""

# ── 2. Pre-Analysis (no LLM needed) ─────────────────────────────────────────

echo -e "${BOLD}[2] Pre-Analysis Engine${NC}"

OUT=$(python3 -c "
from gitdoc.preanalysis import analyze_diff, format_metadata_context
diff = open('samples/sample1_parser_fix.diff').read()
meta = analyze_diff(diff)
print(f'files={len(meta.files)}')
print(f'lang={meta.primary_language}')
print(f'adds={meta.total_additions}')
print(f'dels={meta.total_deletions}')
print(f'complexity={meta.complexity_score}')
print(f'type={meta.change_type_hint}')
")

echo "$OUT" | grep -q "files=1" && pass "file count = 1" || fail "file count" "expected 1"
echo "$OUT" | grep -q "lang=Python" && pass "language = Python" || fail "language" "expected Python"
echo "$OUT" | grep -q "adds=14" && pass "additions = 14" || fail "additions" "expected 14"
echo "$OUT" | grep -q "dels=2" && pass "deletions = 2" || fail "deletions" "expected 2"
echo "$OUT" | grep -q "type=feat" && pass "change type = feat" || fail "change type" "expected feat"

# Multi-file test
OUT=$(python3 -c "
from gitdoc.preanalysis import analyze_diff
diff = open('samples/sample4_multi_file_feature.diff').read()
meta = analyze_diff(diff)
print(f'files={len(meta.files)}')
print(f'has_tests={meta.has_tests}')
")
echo "$OUT" | grep -q "files=3" && pass "multi-file: 3 files" || fail "multi-file" "expected 3 files"
echo "$OUT" | grep -q "has_tests=True" && pass "multi-file: tests detected" || fail "multi-file" "expected has_tests=True"

echo ""

# ── 3. Smart Chunking ────────────────────────────────────────────────────────

echo -e "${BOLD}[3] Smart Chunking${NC}"

OUT=$(python3 -c "
from gitdoc.chunking import truncate_diff, chunk_diff
from gitdoc.config import MAX_DIFF_CHARS

# Small diff — should pass through unchanged
small = open('samples/sample1_parser_fix.diff').read()
result = truncate_diff(small)
print(f'small_unchanged={result == small}')
print(f'small_under_budget={len(result) <= MAX_DIFF_CHARS}')

# Chunk mode
chunks = chunk_diff(small)
print(f'small_chunks={len(chunks)}')
")

echo "$OUT" | grep -q "small_unchanged=True" && pass "small diff passes through" || fail "small diff" "expected unchanged"
echo "$OUT" | grep -q "small_under_budget=True" && pass "small diff under budget" || fail "small diff budget" "over MAX_DIFF_CHARS"
echo "$OUT" | grep -q "small_chunks=1" && pass "small diff = 1 chunk" || fail "small chunks" "expected 1"

# Large diff chunking
if [ -f edge_cases/02_giant.diff ]; then
    OUT=$(python3 -c "
from gitdoc.chunking import chunk_diff
from gitdoc.config import MAX_DIFF_CHARS
big = open('edge_cases/02_giant.diff').read()
chunks = chunk_diff(big)
print(f'big_chunks={len(chunks)}')
print(f'all_under_budget={all(len(c) <= MAX_DIFF_CHARS for c in chunks)}')
")
    echo "$OUT" | grep -q "big_chunks=" && pass "giant diff chunked into multiple" || fail "giant chunking" "no output"
    echo "$OUT" | grep -q "all_under_budget=True" && pass "all chunks under budget" || fail "chunk budget" "some chunks over limit"
fi

echo ""

# ── 4. Scoring Validation ────────────────────────────────────────────────────

echo -e "${BOLD}[4] Scoring Functions${NC}"

OUT=$(python3 -c "
from gitdoc.scoring import score_commit, score_changelog, score_review, score_pr

# Commit scoring
s1 = score_commit('feat(parser): add new method')[0]
s2 = score_commit('fix stuff')[0]
s3 = score_commit('')[0]
print(f'commit_good={s1}')
print(f'commit_bad={s2}')
print(f'commit_empty={s3}')

# Changelog scoring
good_cl = '## [Unreleased]\n### Added\n- New feature for parsing'
s4 = score_changelog(good_cl)[0]
print(f'changelog_good={s4}')

# Review scoring
good_rv = '### Code Review\n**Risk Level:** HIGH\n**Issues Found:**\n- bug\n**Security:**\n- none\n**Suggestions:**\n- fix it'
s5 = score_review(good_rv)[0]
print(f'review_good={s5}')

# PR scoring
good_pr = '**Title:** Fix auth\n**Summary:** Fixes auth bug\n**Changes:**\n- fix\n**Risk Assessment:** LOW\n**Testing Suggestions:**\n- test it'
s6 = score_pr(good_pr)[0]
print(f'pr_good={s6}')
")

echo "$OUT" | grep -q "commit_good=10" && pass "commit: valid format → 10" || fail "commit scoring" "expected 10"
echo "$OUT" | grep -q "commit_bad=" && pass "commit: no scope → lower score" || fail "commit bad" "no output"
echo "$OUT" | grep -q "commit_empty=0" && pass "commit: empty → 0" || fail "commit empty" "expected 0"
echo "$OUT" | grep -q "changelog_good=10" && pass "changelog: valid → 10" || fail "changelog scoring" "expected 10"
echo "$OUT" | grep -q "review_good=10" && pass "review: valid → 10" || fail "review scoring" "expected 10"
echo "$OUT" | grep -q "pr_good=10" && pass "PR: valid → 10" || fail "PR scoring" "expected 10"

echo ""

# ── 5. LLM Pipeline (requires Ollama) ────────────────────────────────────────

echo -e "${BOLD}[5] LLM Pipeline (live)${NC}"

if [ $OLLAMA -eq 0 ]; then
    skip "All LLM tests" "Ollama not running"
    echo ""
else
    # Single pass
    OUT=$(python3 gemma_ollama.py samples/sample1_parser_fix.diff --pass commit --no-color 2>&1)
    echo "$OUT" | grep -q "Commit Message" && pass "single pass: commit" || fail "single pass" "no output"

    # JSON output
    OUT=$(python3 gemma_ollama.py samples/sample1_parser_fix.diff --json --pass commit 2>&1)
    echo "$OUT" | python3 -m json.tool > /dev/null 2>&1 && pass "JSON output: valid" || fail "JSON output" "invalid JSON"

    # File output
    python3 gemma_ollama.py samples/sample1_parser_fix.diff --pass commit -o /tmp/altair_out.md --no-color 2>&1 > /dev/null
    [ -f /tmp/altair_out.md ] && [ -s /tmp/altair_out.md ] && pass "file output: written" || fail "file output" "file not created"
    rm -f /tmp/altair_out.md

    # Stdin pipe
    OUT=$(cat samples/sample2_auth_middleware.diff | python3 gemma_ollama.py - --pass commit --no-color 2>&1)
    echo "$OUT" | grep -q "Commit Message" && pass "stdin pipe: works" || fail "stdin pipe" "no output"

    # Verbose mode
    OUT=$(python3 gemma_ollama.py samples/sample1_parser_fix.diff --pass commit --no-color -v 2>&1)
    echo "$OUT" | grep -q "DEBUG" && pass "verbose mode: shows debug" || fail "verbose" "no DEBUG output"

    echo ""
fi

# ── 6. Hook Install ──────────────────────────────────────────────────────────

echo -e "${BOLD}[6] Git Hook${NC}"

OUT=$(python3 gemma_ollama.py --install-hook 2>&1)
echo "$OUT" | grep -q "installed" && pass "hook install message" || fail "hook install" "no success message"
[ -f .git/hooks/prepare-commit-msg ] && pass "hook file exists" || fail "hook file" "not created"
[ -x .git/hooks/prepare-commit-msg ] && pass "hook is executable" || fail "hook perms" "not executable"

echo ""

# ── 7. Edge Cases (no LLM — just no crash) ───────────────────────────────────

echo -e "${BOLD}[7] Edge Cases (no crash)${NC}"

if [ -d edge_cases ] && [ $OLLAMA -eq 1 ]; then
    for f in edge_cases/05_new_file.diff edge_cases/06_deleted_file.diff edge_cases/07_rename.diff edge_cases/09_whitespace_only.diff edge_cases/14_unicode.diff edge_cases/19_crlf.diff; do
        if [ -f "$f" ]; then
            python3 gemma_ollama.py "$f" --pass commit --no-color > /dev/null 2>&1 && pass "$(basename $f)" || fail "$(basename $f)" "crashed"
        fi
    done
else
    skip "Edge cases" "edge_cases/ dir missing or Ollama not running"
fi

echo ""

# ── Summary ──────────────────────────────────────────────────────────────────

echo -e "${DIM}────────────────────────────────────────${NC}"
TOTAL=$((PASS + FAIL + SKIP))
echo -e "${BOLD}Results:${NC} ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}, ${YELLOW}${SKIP} skipped${NC} (${TOTAL} total)"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}${BOLD}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}${BOLD}${FAIL} test(s) failed.${NC}"
    exit 1
fi
