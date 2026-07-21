#!/usr/bin/env python3
"""Parse resident posts that report a SPECIFIC apartment handed out as
"compensation housing" (компенсационное жильё) -- the reallocation endpoint of
the ownerless-seizure pipeline (dispossessed owner A's flat -> new occupant B).
Surfaced by the 2026-07-21 monitored-channel scan (scripts/385/390); see
memory/monitored_scan_findings_2026-07-21.md.

Each hit is a new occupant (or their agent) publicly asking who used to live
in the apartment they were just assigned ("Ищу собственника … распределена
как компенсационное жильё"). Read-only over the already-captured
telegram_building_chat_msg corpus; writes data/parsed/
compensation_reallocation.jsonl. No network, no DB writes.

PRIVACY (CLAUDE.md hard rule): BOTH the dispossessed owner and the posting
new occupant are living private individuals. This parser stores ONLY the
structured address (building_id/street/house/apt), the post date, and
provenance (channel, message URL, source sha256). It deliberately does NOT
store the free-text body, personal names, or phone numbers. The message URL
lets an authorized reviewer open the raw post from the evidence store if the
personal detail is ever needed under proper handling; it is never surfaced in
shared output.

    PYTHONPATH=src .venv312/bin/python scripts/391_parse_compensation_reallocation_posts.py
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.normalize.address import address_to_building_key  # noqa: E402

log = logging.getLogger(__name__)

# A post qualifies only if it BOTH reports a compensation reallocation AND
# carries a specific street+house+apartment. The two-signal gate keeps generic
# "what is compensation housing?" chatter out.
REALLOC_RE = re.compile(
    r"распределен\w*\s+(?:как\s+)?компенсац|"
    r"выдан\w*\s+(?:как\s+)?компенсац|"
    r"компенсац\w+\s+жиль[её]\b|"
    r"выдали\s+как\s+компенсац", re.I)
SEARCH_RE = re.compile(r"ищу\s+собственник|ищем\s+собственник|отзовит|кто\s+знает\s+хозя", re.I)

# street + house + apartment. Case-INSENSITIVE (re.I): resident chat posts are
# frequently all-lowercase ("ищу собственника по адресу ленина 106"), so an
# uppercase-first requirement drops nearly everything. The defect the original
# had was a street token that allowed internal SPACES, letting it bleed backward
# over preceding sentence words ("...собственника жилья зелинского"). The fix is
# to RIGHT-ANCHOR: the street is the single hyphenated word immediately before
# the house number (no internal spaces), optionally followed by a trailing type
# word (Комсомольский БУЛЬВАР 68). Because the street can't span spaces, it can
# only ever be the street name, never a run of words.
# The address normalizer (normalize/toponym.py:_classify) needs a street-TYPE
# word -- leading ("ул. Куприна") or trailing ("Комсомольский бульвар") -- to
# classify STREET/AVENUE/BOULEVARD; a bare name resolves to UNKNOWN by design
# ("rather miss than collide"). So we capture BOTH markers and hand the
# normalizer a string that carries whichever is present. A post with no type
# word at all can't be spine-joined and is dropped downstream.
ADDR_RE = re.compile(
    r"((?:ул(?:иц\w*)?|просп(?:ект)?|пр-?кт|пр|б-?р|бул(?:ьвар)?|"
    r"пер(?:еул\w*)?|шоссе)\.?\s*)?"                              # 1: optional LEADING type
    r"([А-Яа-яёЁ][А-Яа-яёЁ\-]{2,})"                              # 2: street name (one word)
    r"((?:[\s,]+(?:бульвар|б-?р|проспект|просп|пр-?кт|улиц\w*|"
    r"переул\w*|пер|шоссе)\.?))?"                                # 3: optional TRAILING type
    r"[,\s]+(?:д(?:ом)?\.?\s*)?(\d+\s*[А-Яа-я]?)"                # 4: house
    r"[,\s]+кв\.?\s*(\d+)", re.I)                                # 5: apt

# tokens that are really quarter/microdistrict/non-street tags -- drop them
# (see memory/near_miss_review_findings).
STREET_STOPLIST = re.compile(r"^(?:лет|ссср|квартал|микрорайон|мкр|дом|"
                             r"адрес\w*|собственник\w*|соглас\w*)$", re.I)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    con = sqlite3.connect(config.STATE_DB)
    rows = con.execute(
        "SELECT sha256, url, raw_path FROM source_document "
        "WHERE source_type='telegram_building_chat_msg'",
    ).fetchall()
    log.info("scanning %d messages for compensation-reallocation reports", len(rows))

    # dedup by (building_id, apt); keep the earliest dated post as canonical,
    # count how many independent posts named the same unit.
    ledger: dict[tuple, dict] = {}
    scanned = 0
    for sha, url, path in rows:
        scanned += 1
        if scanned % 100000 == 0:
            log.info("  ... %d/%d", scanned, len(rows))
        try:
            d = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            continue
        text = d.get("message") or ""
        if not (REALLOC_RE.search(text) and (SEARCH_RE.search(text) or "компенсац" in text.lower())):
            continue
        m = ADDR_RE.search(text)
        if not m:
            continue
        lead, name, trail = m.group(1) or "", m.group(2).strip(), m.group(3) or ""
        house_raw, apt = m.group(4).strip(), m.group(5)
        if STREET_STOPLIST.search(name):
            continue
        # hand the normalizer the name WITH its type marker so it can classify;
        # keep a clean display form for the record
        street_for_norm = (lead + name + trail).strip()
        street_raw = re.sub(r"\s+", " ", street_for_norm).strip(" .,")
        building_id = address_to_building_key(street_for_norm, house_raw)
        if building_id is None or building_id.startswith("UNKNOWN:"):
            continue
        date = (d.get("date") or "")[:10]
        ch = (re.search(r"t\.me/([^/]+)/", url) or [None, "?"])[1]
        key = (building_id, apt)
        rec = ledger.get(key)
        if rec is None:
            ledger[key] = {
                "building_id": building_id,
                "street_raw": street_raw,
                "house_raw": house_raw,
                "apt_raw": apt,
                "first_report_date": date,
                "n_posts": 1,
                # provenance ONLY -- no body text, no names/phones (privacy rule)
                "source_channel": ch,
                "source_url": url,
                "source_sha256": sha,
            }
        else:
            rec["n_posts"] += 1
            if date and (not rec["first_report_date"] or date < rec["first_report_date"]):
                rec["first_report_date"] = date
                rec["source_channel"] = ch
                rec["source_url"] = url
                rec["source_sha256"] = sha

    out = ROOT / "data" / "parsed" / "compensation_reallocation.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for rec in sorted(ledger.values(), key=lambda r: (r["building_id"], int(r["apt_raw"]))):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    log.info("wrote %d distinct (building, apt) reallocation records -> %s", len(ledger), out)
    # quick building-level summary for review
    from collections import Counter
    by_bldg = Counter(r["building_id"] for r in ledger.values())
    print(f"{len(ledger)} distinct reallocated apartments across {len(by_bldg)} buildings")
    for bid, n in by_bldg.most_common(30):
        print(f"  {n:2}  {bid}")


if __name__ == "__main__":
    main()
