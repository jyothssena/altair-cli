#!/bin/bash
# Altair — Quick Start Script
# Checks prerequisites, installs dependencies, and runs the pipeline.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${CYAN}${BOLD}  ✶ Altair — The Automagic Documenter${NC}"
echo -e "${CYAN}  ──────────────────────────────────────${NC}"
echo ""

# 1. Check Python
echo -e "${BOLD}[1/4]${NC} Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error:${NC} Python 3 not found. Install from https://python.org"
    exit 1
fi
PY_VERSION=$(python3 --version 2>&1)
echo -e "  ${GREEN}Found:${NC} $PY_VERSION"

# 2. Check/Install dependencies
echo -e "${BOLD}[2/4]${NC} Checking dependencies..."
if ! python3 -c "import requests" 2>/dev/null; then
    echo -e "  ${YELLOW}Installing requirements...${NC}"
    pip install -r requirements.txt --quiet
    echo -e "  ${GREEN}Done.${NC}"
else
    echo -e "  ${GREEN}All dependencies installed.${NC}"
fi

# 3. Check Ollama
echo -e "${BOLD}[3/4]${NC} Checking Ollama..."
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}Error:${NC} Ollama not found. Install from https://ollama.com"
    exit 1
fi

if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "  ${YELLOW}Starting Ollama server...${NC}"
    ollama serve &>/dev/null &
    sleep 3
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${RED}Error:${NC} Failed to start Ollama. Run 'ollama serve' manually."
        exit 1
    fi
fi
echo -e "  ${GREEN}Ollama is running.${NC}"

# 4. Check model
echo -e "${BOLD}[4/4]${NC} Checking Gemma 3 model..."
MODEL=${GITDOC_MODEL:-gemma3:4b}
if ! ollama list | grep -q "$MODEL"; then
    echo -e "  ${YELLOW}Pulling $MODEL (this may take a few minutes)...${NC}"
    ollama pull "$MODEL"
fi
echo -e "  ${GREEN}Model ready:${NC} $MODEL"

echo ""
echo -e "${GREEN}${BOLD}  Ready!${NC} All prerequisites satisfied."
echo ""
echo -e "${CYAN}  Usage:${NC}"
echo -e "    python3 gemma_ollama.py <file.diff>              Full pipeline"
echo -e "    python3 gemma_ollama.py <file.diff> --pass commit Single pass"
echo -e "    python3 gemma_ollama.py <file.diff> --json        JSON output"
echo -e "    python3 gemma_ollama.py --batch main..feature     Release notes"
echo -e "    python3 gemma_ollama.py --install-hook            Git hook"
echo -e "    git diff | python3 gemma_ollama.py -              From stdin"
echo ""

# If a diff file was passed as argument, run it
if [ -n "$1" ]; then
    echo -e "${CYAN}${BOLD}  Running pipeline on: $1${NC}"
    echo ""
    python3 gemma_ollama.py "$@"
else
    echo -e "${YELLOW}  Tip:${NC} Run with a diff file to see it in action:"
    echo -e "    ${BOLD}./start.sh samples/sample1_parser_fix.diff${NC}"
    echo ""
fi
