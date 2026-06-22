#!/usr/bin/env python3
"""Stage 1j: targeted capture of known personnel-appointment Указы.

Found 2026-06-12 by grepping the already-captured denis-pushilin.ru
/akty-glavy-dnr/ukazy/ archive index (data/raw, source_type
denis_pushilin_doc_index) for short "О <Фамилия> <И.О.>" titles matching the
Mariupol command-chain officials in docs/stakeholder_network.md:

  - Ukaz_13_22012023.pdf  -- Указ врио Главы ДНР №13 от 22.01.2023 "Об Иващенко К.В."
  - Ukaz_14_22012023.pdf  -- Указ врио Главы ДНР №14 от 22.01.2023 "О Моргуне О.В."
  - Ukaz_N541_06112023.pdf -- Указ Главы ДНР №541 от 06.11.2023 "О Моргуне О.В."
  - Ukaz_N492_12062025.pdf -- Указ Главы ДНР №492 от 12.06.2025 "О Моргуне О.В."

№13/№14 share the same date and "врио" (acting) signer -- likely the pair
that installed Иващенко К.В. (Распоряжение №61 signer, [[legal_mechanisms]])
and Моргун О.В. (#2 ownerless-decree signer, 156 decrees) into their Mariupol
posts. The two later Моргун Указы (06.11.2023, 12.06.2025) may be
reappointments/role changes -- read once captured.

None of these 4 are in the raw store yet (script 39's full archive crawl is
~76% done and hasn't reached them). This is a tiny, fast, targeted run (4
PDFs, ~20s with polite delays) -- no need to wait for the full crawl.

Same network profile as script 39 (HTTPS, verify=False, no VPS needed).
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import forensics  # noqa: E402
from mariupol_seizures.crawl import denis_pushilin as dp  # noqa: E402

log = logging.getLogger(__name__)

TARGETS = [
    ("https://denis-pushilin.ru/doc/ukazy/Ukaz_13_22012023.pdf",
     "Указ врио Главы ДНР №13 от 22.01.2023 — Об Иващенко К.В."),
    ("https://denis-pushilin.ru/doc/ukazy/Ukaz_14_22012023.pdf",
     "Указ врио Главы ДНР №14 от 22.01.2023 — О Моргуне О.В."),
    ("https://denis-pushilin.ru/doc/ukazy/Ukaz_N541_06112023.pdf",
     "Указ Главы ДНР №541 от 06.11.2023 — О Моргуне О.В."),
    ("https://denis-pushilin.ru/doc/ukazy/Ukaz_N492_12062025.pdf",
     "Указ Главы ДНР №492 от 12.06.2025 — О Моргуне О.В."),
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    con = forensics.open_state()
    s = dp.make_session()
    for url, title in TARGETS:
        dp._capture_pdf(
            s, con, url,
            source_type="denis_pushilin_doc_pdf",
            title=url.rsplit("/", 1)[-1],
            description=f"Targeted capture (appointment decree): {title}. "
                         "Primary-source PDF from denis-pushilin.ru /akty-glavy-dnr/ukazy/.",
            key_prefix="denis_pushilin_doc_pdf",
        )
    log.info("done")


if __name__ == "__main__":
    main()
