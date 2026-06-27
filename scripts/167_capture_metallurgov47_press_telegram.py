#!/usr/bin/env python3
"""Capture press + Telegram primary sources confirming pr. Metallurgov, 47
as the Troianda-M demolition address (closes the open address gap flagged
in `docs/case_studies/troianda_m_demolition_challenge.md`, 2026-06-26).

Quick text/HTML fetches only (no video) -- run directly, not handed off,
per CLAUDE.md capture-before-parse discipline. Idempotent: re-running just
re-confirms existing hashes (forensics.capture_source dedupes by sha256).

Usage:
    .venv312/bin/python scripts/167_capture_metallurgov47_press_telegram.py
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402
from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

TARGETS = [
    {
        "url": "https://www.agents.media/neskolko-desyatkov-zhitelej-mariupolya-podali-kollektivnuyu-zhalobu-v-verhovnyj-sud-s-trebovaniem-kompensirovat-poteryannoe-zhile/",
        "source_type": "press_article",
        "title": "Agents.Media: residents file Supreme Court complaint over lost housing",
        "description": "Names address pr. Metallurgov 47; 60 residents filed, 22 with "
                        "compensation approval; cassation filed 27.02.2026; replacement "
                        "project 'Novoe vremya 2'; developer named 'RKS-NR', Ildar Sharipov, "
                        "linked to Deputy PM Marat Khusnutdinov; compensation rate 45,000 "
                        "RUB/sqm vs market 53,000 RUB/sqm.",
    },
    {
        "url": "https://www.donetsk.kp.ru/daily/27638/4989073/",
        "source_type": "press_article",
        "title": "KP Donetsk: Metallurgov 47 reconstruction",
        "description": "Confirms address pr. Metallurgov 47; 9-storey, 2-entrance "
                        "replacement building, works started 18.09.2024, target "
                        "completion autumn 2025; resident witness Maxim Zhitnikov "
                        "account of March 2022 damage (occupation framing -- "
                        "'liberation', Ukrainian tank narrative -- mark as occupier "
                        "framing if quoted in case study, not adopted voice).",
    },
    {
        "url": "https://t.me/metallgov/397?embed=1",
        "source_type": "telegram_post",
        "title": "@metallgov/397 -- captions the fire photo as pr. Metallurgov 47",
        "description": "Single line: 'пр. Металлургов 47' crediting @mariupol_our -- "
                        "this is the same fire/combat-damage photo handed to Claude "
                        "by the user 2026-06-26.",
    },
    {
        "url": "https://t.me/mariupollnew/22920?embed=1",
        "source_type": "telegram_post",
        "title": "@mariupollnew/22920 -- foundation pit excavation at Metallurgov 47",
        "description": "'Разрабатывают котлован на месте дома №47 по пр. Металлургов, "
                        "возле центрального рынка' -- confirms demolition-to-construction "
                        "sequence and near-central-market location detail.",
    },
    {
        "url": "https://t.me/novosti_mariupol1/32537?embed=1",
        "source_type": "telegram_post",
        "title": "@novosti_mariupol1/32537 -- Metallurgov 47 2022/2025 before-after video",
        "description": "References a before/after video from channel MRPLRU -- not yet "
                        "independently captured; follow-up lead.",
    },
    {
        "url": "https://t.me/allmarinews/21995?embed=1",
        "source_type": "telegram_post",
        "title": "@allmarinews/21995 -- residents appeal to Russian Community + Investigative Committee",
        "description": "'Жители проспекта Металлургов, 47, обратились в Русскую общину "
                        "Мариуполя и в Следственный комитет РФ' -- corroborates ongoing "
                        "resident advocacy outside the court track.",
    },
]


def capture_one(t: dict, con) -> None:
    headers = {"User-Agent": config.USER_AGENT} if hasattr(config, "USER_AGENT") else {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        r = requests.get(t["url"], headers=headers, timeout=20)
    except requests.RequestException as e:
        log.error("fetch failed for %s: %s", t["url"], e)
        return
    if r.status_code != 200:
        log.warning("HTTP %s for %s", r.status_code, t["url"])
        return
    sha = forensics.capture_source(
        r.content,
        url=t["url"],
        source_type=t["source_type"],
        title=t["title"],
        description=t["description"],
        content_type=r.headers.get("Content-Type", "text/html"),
        http_status=r.status_code,
        con=con,
    )
    log.info("captured %s -> sha=%s", t["url"], sha[:12])


def main() -> None:
    con = forensics.open_state()
    for t in TARGETS:
        capture_one(t, con)
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
