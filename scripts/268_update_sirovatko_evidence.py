#!/usr/bin/env python3
"""One-off, idempotent update to person:сироватко-ю's evidence in the
stakeholder graph: the document-content survey (2026-07-06, scripts/264/265)
found the primary source proving he SIGNED the 17.10.2023 Rosreestr
registration-freeze letter to МФЦ ДНР, not merely received a resident
complaint about it (his evidence array previously only listed the latter).

Local, offline, no network.

Run:
    .venv312/bin/python3 scripts/268_update_sirovatko_evidence.py
    .venv312/bin/python3 scripts/189_rebuild_stakeholder_jsx.py
    (then the esbuild pass scripts/189 prints instructions for)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NODES_PATH = ROOT / "data" / "parsed" / "stakeholder_nodes.jsonl"

NEW_EVIDENCE_ITEM = (
    "telegram:mrpl_besxozxata/44397 (SIGNED the 17.10.2023 internal letter "
    "to МФЦ ДНР ordering staff to stop accepting registration applications "
    "from Ukrainian-passport/foreign/stateless owners — confirmed author, "
    "not just addressee, of the Rosreestr registration freeze)"
)


def main() -> None:
    rows = [json.loads(l) for l in NODES_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    updated = False
    for r in rows:
        if r.get("node_id") == "person:сироватко-ю":
            if NEW_EVIDENCE_ITEM not in r.get("evidence", []):
                r.setdefault("evidence", []).append(NEW_EVIDENCE_ITEM)
                updated = True
            break
    else:
        print("person:сироватко-ю not found in stakeholder_nodes.jsonl", file=sys.stderr)
        return

    if not updated:
        print("Evidence already present — nothing to do.", file=sys.stderr)
        return

    with open(NODES_PATH, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("Updated person:сироватко-ю's evidence.", file=sys.stderr)


if __name__ == "__main__":
    main()
