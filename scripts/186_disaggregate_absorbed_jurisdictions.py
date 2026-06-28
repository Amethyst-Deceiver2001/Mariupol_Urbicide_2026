#!/usr/bin/env python3
"""Disaggregate the district bezkhoz population (`scripts/182`) by ORIGIN
MUNICIPALITY for the courts that absorbed another court's jurisdiction, per
ВС ДНР's venue-reassignment notice (vs--dnr.sudrf.ru, name=information&rid=5,
user-captured 2026-06-28, sha256 6bb873cb712133c110b7f25a11bc4de6691dd914262d491ba3b58c61493a4395).

WHY THIS EXISTS
---------------
15 of the 39 registered district courts returned zero case-cards under their
own domain. The progress report originally lumped all 15 into "destroyed or
ghost-jurisdiction, nothing to seize." The venue notice shows that's wrong for
10 of them: their jurisdiction was FORMALLY TRANSFERRED to another court
(Авдеевский->Ясиноватский, Александровский/Добропольский/Новогродовский/
Селидовский->Ворошиловский, Великоновоселковский->Кировский,
Дзержинский/Краснолиманский->Енакиевский, Дружковский/Константиновский->
Горловский) -- their cases are NOT zero, they are filed under the absorbing
court's docket, indistinguishable from that court's own caseload unless the
ruling text itself names the origin town.

METHOD, AND THE TWO FALSE-POSITIVE TRAPS ALREADY HIT BY HAND
--------------------------------------------------------------
A naive substring search over the absorbing court's full case-card text finds
two false-positive families that must be excluded:
  1. Site-wide boilerplate -- every page on an absorbing court's own site can
     embed the SAME venue notice (e.g. enak--dnr's footer literally contains
     "...Дзержинскому городскому суду, Краснолиманскому..."), which is not a
     case fact. Excluded by stripping the notice's own wording before matching.
  2. Judge patronymics/surnames -- "Александр" matches "Иванов А. Александрович"
     on ~30% of unrelated cards. Excluded by matching the FULL city-name form
     with a required institutional-context anchor (housing authority, registry
     office, district/округ name, or the case's own "Категория дела"
     "Ясиноватский МУНИЦИПАЛЬНЫЙ ОКРУГ, город Авдеевка" style phrasing) rather
     than a bare root.

A hit under this method is a REAL origin-town signal (verified by hand for
Avdiivka: original housing-fund titles, "Авдеевский коксохимзавод" registry
office, explicit "город Авдеевка" address fragments).

Run:
    .venv312/bin/python scripts/186_disaggregate_absorbed_jurisdictions.py
"""
from __future__ import annotations

import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bs4 import BeautifulSoup  # noqa: E402

log = logging.getLogger(__name__)

SRC = ROOT / "data" / "parsed" / "dnr_district_bezkhoz.json"
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "parsed" / "absorbed_jurisdiction_origins.json"

# absorbing court -> {origin town: anchored regex requiring an institutional
# context, not a bare name}. \b-bounded; excludes judge-name false positives
# (Александрович/Александровна never match a town-anchor pattern).
ABSORBED = {
    "yasin--dnr": {
        "Авдіївка/Авдеевка": re.compile(
            r"город[а]?\s+Авдеевк|Авдеевск(?:ого|ой)\s+(?:городского\s+совета|"
            r"коксохимзавода|муниципальн)|Авдеевской\s+(?:государственной|"
            r"нотариальной)", re.I),
    },
    "vr--dnr": {
        "Олександрівка/Александровск": re.compile(
            r"город[а]?\s+Александровк|Александровск(?:ого|ой)\s+район", re.I),
        "Добропілля/Доброполье": re.compile(
            r"город[а]?\s+Доброполь|Добропольск(?:ого|ой)\s+(?:городск|округ)", re.I),
        "Новогродівка/Новогродовка": re.compile(
            r"город[а]?\s+Новогродовк|Новогродовск(?:ого|ой)\s+(?:городск|округ)", re.I),
        "Селидове/Селидово": re.compile(
            r"город[а]?\s+Селидов|Селидовск(?:ого|ой)\s+(?:городск|округ)", re.I),
    },
    "kir--dnr": {
        "Велика Новосілка/Великоновоселковское": re.compile(
            r"Великоновоселковск(?:ого|ой)\s+район|пос(?:елок|\.)\s+Велика\s*Новосел", re.I),
    },
    "enak--dnr": {
        "Торецьк/Дзержинск(Торецк)": re.compile(
            r"город[а]?\s+Дзержинск(?!ого\s+городскому\s+суду)|Дзержинск(?:ого|ой)\s+"
            r"(?:городского\s+совета|округ)(?!\s+суду)", re.I),
        "Лиман/Краснолиманск": re.compile(
            r"город[а]?\s+Красный\s+Лиман|Краснолиманск(?:ого|ой)\s+(?:городск|район)"
            r"(?!\s+суду)", re.I),
    },
    "cg-gorl--dnr": {
        "Дружківка/Дружковка": re.compile(
            r"город[а]?\s+Дружковк|Дружковск(?:ого|ой)\s+(?:городск|округ)(?!\s+суду)", re.I),
        # NOTE: a "Костянтинівка" town-anchor heuristic was tried and dropped --
        # the only candidate-style match found was "уроженец г. Константиновка"
        # (a deceased party's BIRTHPLACE, not the property's location), the
        # same false-positive shape as the boilerplate/patronymic traps above.
        # No reliable anchor found yet for this town; left unclassified rather
        # than risk another birthplace/biography false positive.
    },
}
# The notice's own boilerplate wording -- stripped before matching so a site
# footer/nav embed of the notice itself can never register as a hit.
NOTICE_STRIP = re.compile(
    r"дела,\s*подсудные\s+[^;]+отнести\s+к\s+подсудности[^;]+;?", re.I)


def main() -> None:
    recs = json.loads(SRC.read_text(encoding="utf-8"))
    by_court: dict[str, list[dict]] = {}
    for r in recs:
        by_court.setdefault(r["court_code"], []).append(r)

    results = []
    for court, towns in ABSORBED.items():
        sub = by_court.get(court, [])
        log.info("%s: scanning %d cards for absorbed-jurisdiction origin towns",
                 court, len(sub))
        for r in sub:
            p = RAW / (r["raw_sha"] + ".html")
            if not p.exists():
                continue
            text = BeautifulSoup(p.read_bytes().decode("cp1251", "replace"),
                                 "lxml").get_text(" ", strip=True)
            text_clean = NOTICE_STRIP.sub("", text)  # drop the venue notice itself
            for town, rx in towns.items():
                if rx.search(text_clean):
                    results.append({
                        "absorbing_court": court, "origin_town": town,
                        "case": r["case"], "rollup": r["rollup"],
                        "filed": r["filed"], "decided": r["decided"],
                        "raw_sha": r["raw_sha"],
                    })
                    break

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1),
                   encoding="utf-8")

    by_town = Counter(r["origin_town"] for r in results)
    print(f"\n{'='*64}\nAbsorbed-jurisdiction origin-town recovery\n{'='*64}")
    for town, n in by_town.most_common():
        print(f"  {n:4d}  {town}")
    print(f"\n  total recovered: {len(results)}")
    print(f"  -> {OUT}")
    print("\n  REMINDER: this recovers cases NEWLY ATTRIBUTABLE to an absorbed "
          "town's\n  jurisdiction; it does not prove the absence of a hit means "
          "zero real\n  cases -- the ruling text may simply not name the origin "
          "town. Treat\n  zero-hit absorbing courts (vr, kir for most towns) as "
          "inconclusive,\n  not as proof those territories produce no bezkhoz "
          "activity.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
