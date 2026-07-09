#!/usr/bin/env python3
"""Capture the primary text of Закон ДНР №272-РЗ (17.04.2026) -- "О признаках
бесхозяйного имущества в отношении жилых помещений..." -- which repeals and
replaces Закон ДНР №66-РЗ (21.03.2024) as the DNR-wide statutory basis for
the housing-specific bezkhoz procedure, plus №66-РЗ itself (for the
side-by-side comparison) and two sibling instruments already referenced
elsewhere in this project's research (№269-РЗ, №137-РЗ) whose primary text
had never actually been captured despite being cited.

Found via glavadnr.ru/doc/zakony/<N>rz.pdf, the same URL pattern already
confirmed working for №52-РЗ. All four are text-native PDFs (pdftotext
-layout works directly, no OCR needed).

MAJOR FINDING (read in full 2026-07-08, verifying a user-supplied Telegram
post from @mrpl_besxozxata/7910/94267): №272-РЗ eliminates the court-
petition requirement entirely for housing bezkhoz designation. №66-РЗ ст.
required "уполномоченный орган обращается в суд с заявлением о признании
права муниципальной собственности" (the authorized body petitions a court).
№272-РЗ ст.7 ч.2 instead vests title "в силу закона со дня включения такого
жилого помещения в реестр муниципального имущества" (automatically, by
operation of law, the day the unit enters the municipal property registry)
-- a purely administrative/extrajudicial procedure (ст.8 ч.1 explicitly
uses the phrase "во внесудебном порядке"). This appears to be the specific,
dated implementing statute for the court-abolition shift the project has
tracked only as an inferred data signature (the Mariupol court conveyor
shutting down, attributed to ФКЗ-4) -- see docs/legal_mechanisms_review.md
and CLAUDE.md's "Current state" section.

Every other claim in the user-supplied Telegram summary
(t.me/mrpl_besxozxata/7910/94267) was verified word-for-word against this
primary text: the two mandatory + one optional признака (ст.2), the 10-day/
30-day notice timeline including the door-posted notice (ст.5 ч.1 п.3), the
forced-entry-with-police clause (ст.5 ч.3), the furniture/valuables
inventory (ст.5 ч.2/ч.4), the exact Статья 8 ч.1 quote on pre-registry
reversal, the Статья 8 ч.3 repair-cost reimbursement clause, the 2030
sunset (ст.11), the ЕГРН-registered-title carve-out (ст.1 ч.3), the
outbuildings-follow-the-house list (ст.1 ч.4), and the №52-РЗ movable-
property cross-reference (ст.1 ч.5). The message's claimed publication date
(24.04.2026) is plausible but not independently confirmed by this PDF alone
(only the 17.04.2026 signature/adoption date is on the document itself).
"""
import logging
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

TARGETS = [
    (
        "https://glavadnr.ru/doc/zakony/272rz.pdf",
        "Закон ДНР №272-РЗ (17.04.2026) «О признаках бесхозяйного "
        "имущества в отношении жилых помещений, об особенностях порядка "
        "выявления, учета и возникновения права муниципальной "
        "собственности на такие жилые помещения»",
        "Repeals and replaces №66-РЗ. Eliminates the court-petition "
        "requirement -- title now vests automatically (\"в силу закона\") "
        "upon municipal-registry entry, no court step. Valid until "
        "01.01.2030. Text-native PDF.",
    ),
    (
        "https://glavadnr.ru/doc/zakony/66rz.pdf",
        "Закон ДНР №66-РЗ (21.03.2024) «Об особенностях выявления, "
        "использования и признания права муниципальной собственности... "
        "на жилые помещения, имеющие признаки бесхозяйного имущества...» "
        "-- REPEALED by №272-РЗ",
        "Predecessor statute, repealed by №272-РЗ ст.12 effective "
        "24.04.2026 (per user-supplied claim, publication date not "
        "independently confirmed). Required a court petition to "
        "recognize municipal ownership -- the key procedural difference "
        "from its replacement. Already cited extensively (ст.5(3)(а) "
        "personal-appearance clause) in docs/legal_mechanisms_review.md "
        "but primary text had never been captured. Text-native PDF.",
    ),
    (
        "https://glavadnr.ru/doc/zakony/269rz.pdf",
        "Закон ДНР №269-РЗ (03.04.2026) -- disposal/compensation "
        "provisions, sibling instrument to №272-РЗ",
        "Already referenced in docs/legal_mechanisms_review.md as part "
        "of the DNR-wide ownerless-procedure instrument chain but primary "
        "text had never been captured. Text-native PDF.",
    ),
    (
        "https://glavadnr.ru/doc/zakony/137rz.pdf",
        "Закон ДНР №137-РЗ (13.12.2024) -- amendment to №66-РЗ",
        "Already referenced in docs/legal_mechanisms_review.md but "
        "primary text had never been captured. Text-native PDF.",
    ),
    (
        "https://glavadnr.ru/doc/zakony/141rz.pdf",
        "Закон ДНР №141-РЗ (18.12.2024) «О поддержке граждан, жилые "
        "помещения которых утрачены в результате боевых действий на "
        "территории Донецкой Народной Республики»",
        "The compensation-housing law for war-damaged (not "
        "bezkhoz-stripped) housing loss, amended by №269-РЗ ст.10 "
        "(already captured above). Previously only [CITED] via Telegram "
        "(@morgun_ov) references; primary text never independently "
        "captured. Same glavadnr.ru/doc/zakony/<N>rz.pdf pattern, "
        "confirmed resolving (200, text-native).",
    ),
]


def fetch(url: str) -> tuple[bytes, str, int]:
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(
                url, headers={"User-Agent": config.USER_AGENT},
                timeout=config.TIMEOUT, allow_redirects=True,
            )
            resp.raise_for_status()
            return resp.content, resp.headers.get("Content-Type", "application/pdf"), resp.status_code
        except requests.exceptions.RequestException as exc:
            if attempt == config.MAX_RETRIES - 1:
                raise
            log.warning("transient error fetching %s (attempt %d/%d): %s -- retrying",
                        url, attempt + 1, config.MAX_RETRIES, exc)
            time.sleep(2.0 * (attempt + 1))


def main() -> None:
    con = forensics.open_state()

    for url, title, description in TARGETS:
        content, ctype, status = fetch(url)
        sha = forensics.capture_source(
            content, url=url, source_type="dnr_zakon_pdf",
            title=title, description=description,
            content_type=ctype, http_status=status, con=con,
        )
        log.info("captured %s -> sha=%s status=%s (%d bytes)", title, sha[:12], status, len(content))
        time.sleep(1.0)

    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
