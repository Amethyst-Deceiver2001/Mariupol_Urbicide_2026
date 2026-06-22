#!/usr/bin/env python3
"""Stage 1f: capture ГКО ДНР framework decrees from нпа.днронлайн.рф.

Captures the legal chain-of-authority documents that authorised the
demolition of all war-damaged buildings in Mariupol:

  Постановление ГКО ДНР №162 (23.07.2022) — demolition procedure framework
  Постановление ГКО ДНР №205 (27.08.2022) — amendment adding HQ review step
  Постановление ГКО ДНР №245 (19.09.2022) — further amendment (to locate)

Also searches for ГКО Распоряжения listing specific buildings — particularly
Распоряжение №56 (29.09.2022), the Mariupol demolition list cited in
case 33-2575/2025 as the authority for demolishing ТСЖ «Троянда-М» et al.

Note: Распоряжение №56 is an operational order and may not be on the
normative-acts portal. A separate manual search of the mariupol.gosuslugi.ru
archive (pre-integration Oct 2022 documents) may be needed.

See src/mariupol_seizures/crawl/gko_decrees.py for full design notes.
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures.crawl import gko_decrees  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    gko_decrees.run()
