#!/usr/bin/env python3
"""Re-embed the stakeholder network data into `stakeholder-network.jsx`'s
single-line `const NETWORK = {...}` literal, from the freshly regenerated
`data/parsed/stakeholder_{nodes,edges}.jsonl` (run scripts/40 first).

This is the formalized version of the one-off rewrite done in the
2026-06-20 session (see memory: stakeholder_network_rebuild_style_audit).
Does NOT touch the compiled .html bundle -- that needs a separate esbuild
pass (see scripts/190 or the README it prints).

Run:
    .venv312/bin/python scripts/189_rebuild_stakeholder_jsx.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

NODES = config.PROJECT_ROOT / "data" / "parsed" / "stakeholder_nodes.jsonl"
EDGES = config.PROJECT_ROOT / "data" / "parsed" / "stakeholder_edges.jsonl"
JSX = config.PROJECT_ROOT / "docs" / "exhibits" / "stakeholder-network.jsx"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    nodes = load_jsonl(NODES)
    edges = load_jsonl(EDGES)
    network = {"nodes": nodes, "edges": edges}
    network_json = json.dumps(network, ensure_ascii=False, separators=(",", ":"))

    src = JSX.read_text(encoding="utf-8")
    new_line = f"const NETWORK = {network_json};"
    new_src, n = re.subn(r"^const NETWORK = \{.*\};$", new_line, src,
                          count=1, flags=re.MULTILINE)
    if n != 1:
        print("ERROR: did not find exactly one 'const NETWORK = {...};' line "
              f"to replace (found {n}) -- aborting without writing.",
              file=sys.stderr)
        sys.exit(1)

    JSX.write_text(new_src, encoding="utf-8")
    print(f"Rewrote NETWORK literal: {len(nodes)} nodes, {len(edges)} edges "
          f"({len(network_json):,} bytes)")
    print(f"-> {JSX}")
    print("\nNext: rebuild the bundle (see scripts/190_rebuild_stakeholder_bundle.sh)")


if __name__ == "__main__":
    main()
