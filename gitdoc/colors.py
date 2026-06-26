"""ANSI color codes for rich terminal output."""

import os
import sys


class C:
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    RESET = "\033[0m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_RED = "\033[41m"

    @staticmethod
    def disable():
        for attr in dir(C):
            if attr.isupper() and not attr.startswith("_"):
                setattr(C, attr, "")

    @staticmethod
    def should_use_color():
        if os.environ.get("NO_COLOR"):
            return False
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


if not C.should_use_color():
    C.disable()
