#!/usr/bin/env python3
"""Stage 2: parse the raw store into lifecycle rows (re-runnable, offline)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mariupol_seizures.parse import case_parser

if __name__ == "__main__":
    case_parser.run()
