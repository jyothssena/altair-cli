"""Ollama API interface."""

import json
import sys
import time

import requests

from .colors import C
from .config import OLLAMA_URL, REQUEST_TIMEOUT


def call_ollama(model: str, system_prompt: str, user_content: str, stream: bool = False) -> str:
    """Send a request to Ollama and return the response text."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "stream": stream,
        "options": {
            "temperature": 0.2,
            "num_predict": 1024,
        },
    }

    last_error = None
    for attempt in range(1, 4):
        try:
            resp = requests.post(OLLAMA_URL, json=payload, stream=stream, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            break
        except requests.ConnectionError:
            last_error = f"Cannot connect to Ollama at {OLLAMA_URL}. Run: ollama serve"
            if attempt < 3:
                time.sleep(2)
                continue
            sys.exit(f"{C.RED}Error:{C.RESET} {last_error}")
        except requests.Timeout:
            last_error = f"Request timed out ({REQUEST_TIMEOUT}s). Diff may be too large."
            if attempt < 3:
                time.sleep(1)
                continue
            sys.exit(f"{C.RED}Error:{C.RESET} {last_error}")
        except requests.HTTPError as e:
            sys.exit(f"{C.RED}Error:{C.RESET} Ollama HTTP {e.response.status_code}: {e.response.text}")

    if not stream:
        return resp.json().get("message", {}).get("content", "")

    full = ""
    for line in resp.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        token = chunk.get("message", {}).get("content", "")
        full += token
        if chunk.get("done"):
            break
    return full
