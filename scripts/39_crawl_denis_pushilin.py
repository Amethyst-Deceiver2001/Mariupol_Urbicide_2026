#!/usr/bin/env python3
"""Stage 1i: capture denis-pushilin.ru — the official site of Denis Pushilin
(Head of the DNR occupation administration), 2022 onward.

Reachable over HTTPS with a self-signed ddos-guard cert (verify=False, same
pattern as other crawl stages) — no VPS needed, confirmed 2026-06-12.

Recommended first run (everything from 2022-01-01, ~4,900 items, ~8-9 hours,
fully resumable — safe to Ctrl-C and rerun):

    PYTHONPATH=src python scripts/39_crawl_denis_pushilin.py

Highest-signal subset only — the ~2,890 primary-source legal PDFs (Указы и
Распоряжения Главы ДНР incl. №301, DNR laws, ГКО Постановления/Распоряжения
incl. the №162/205/245 demolition framework and the №56 absence-corroboration
set), skipping the ~2,006 general news/press sitemap pages (~5-6 hours):

    PYTHONPATH=src python scripts/39_crawl_denis_pushilin.py --archives-only

Other useful flags:

    --date-from 2023-01-01   # narrower window
    --skip-dated-archives    # skip ukazy/rasporyazheniya PDF archives
    --skip-undated-archives  # skip zakony/GKO/EES bounded archives

See src/mariupol_seizures/crawl/denis_pushilin.py for full design notes.
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures.crawl import denis_pushilin  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    denis_pushilin.main()
