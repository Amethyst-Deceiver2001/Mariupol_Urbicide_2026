#!/usr/bin/env python3
"""Read-only triage of the messages captured by scripts/385's monitored-channel
text scan -- surface mission-relevant updates and new leads across the ~592K
messages the 2026-07-20/21 run pulled (most channels' full history, first-time
text mine for the official/admin/legal ones).

NOT a capture script and NOT a loader: opens the already-captured raw JSON
message files, applies keyword theme rules, and writes a human-readable digest
to data/reports/. No network, no DB writes, no raw-store writes. Safe to run
repeatedly.

    PYTHONPATH=src .venv312/bin/python scripts/390_triage_monitored_channel_scan.py
    PYTHONPATH=src .venv312/bin/python scripts/390_triage_monitored_channel_scan.py --since 2026-07-20
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger(__name__)

# Channel priority tiers (from scripts/385 CHANNELS) -- drives report ordering.
TIER_OFFICIAL = {
    "mizodnr", "rosreestr80", "minstroydnr", "AG_DPR", "prav_dnr",
    "KoltsovAnton", "PushilinDenis", "mkhusnullin", "ordjonikidzadmin",
    "ilichevskiy", "mariupol_primorskiy", "zhovtnevyy", "news_oktyabrskiy",
    "mtspdnr", "mzdnr_official", "minobrnauki_dnr", "merdnr", "rks_nr",
    "ivashchenko_kv", "morgun_ov",
}
TIER_LEGAL_BEZKHOZ = {
    "advocate_Basivskiy", "yuridicheskiyeuslugiMariupolDon", "donurcenter",
    "mrpl_besxozxata",
}
TIER_NEWS = {
    "mariupol_nash", "ssaniaworld", "nmrpl", "mariupolRIP",
    "kadryVoynyMariypol2022", "mrplSprotyv", "novosti_mariupol1",
    "mariupol24tv", "mrpl_ctzn", "NickolayOsychenko",
    "mariupol_po_faktu", "solntsev_official", "Nash_Mariupol",
    "CHYORNYY_SPISOK", "infrMariupol", "Mangush_Podslushano",
}

def tier(ch: str) -> int:
    if ch in TIER_OFFICIAL: return 0
    if ch in TIER_LEGAL_BEZKHOZ: return 1
    if ch in TIER_NEWS: return 2
    return 3

# Theme rules -- (bucket, compiled regex). Order matters only for display.
THEMES = {
    "federal_military_transfer": re.compile(
        r"войсков\w+\s+част|в/ч\s*\d|Росимущест|федеральн\w+\s+собственност|"
        r"Минобороны|Министерств\w+\s+обороны|Росгвард|\bФСБ\b(?!У)|в\s+федеральную", re.I),
    "bezkhoz_registry_frontline": re.compile(
        r"бесхозяйн|призна\w+\s+бесхоз|реестр\w*\s+муниципальн|переучет|"
        r"перерегистрац|до\s*1\s*июл|1\s*июля\s*2026|снят\w+\s+с\s+учет", re.I),
    "compensation_housing": re.compile(
        r"компенсацион\w+\s+жил|компенсац\w+\s+за\s+жил|141-?РЗ|269-?РЗ|"
        r"жилищн\w+\s+сертификат|специализированн\w+\s+фонд|маневренн\w+\s+фонд", re.I),
    "demolition_construction": re.compile(
        r"\bснос\b|подлеж\w+\s+сносу|демонтаж|аварийн\w+\s+жил|КРТ\b|"
        r"комплексн\w+\s+развити|реновац|изъяти\w+\s+(?:имуществ|для)", re.I),
    "victim_burial": re.compile(
        r"захорон|во\s+дворе\s+похорон|братск\w+\s+могил|перезахорон|"
        r"эксгумац|стихийн\w+\s+захорон", re.I),
    "resale": re.compile(
        r"куплю-продаж|продаж\w+\s+квартир|переуступк|риелтор|вторичк", re.I),
}

# Numbered legal instruments -- capture the (type, number) for a frequency table,
# to spot instruments not yet in our docs.
INSTRUMENT_RE = re.compile(
    r"(Указ|Постановлени\w*|Распоряжени\w*|Закон\w*|ФКЗ|ФЗ|Решени\w*|Приказ\w*)"
    r"[^.\n]{0,40}?№\s*([\dI/\-А-Яа-я]{1,20})", re.I)

MAX_PER_BUCKET = 120   # cap hits shown per (tier, theme)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-07-20",
                    help="captured_at date floor (this scanning session)")
    ap.add_argument("--year", default="2026",
                    help="only surface messages whose MESSAGE date starts with this (recency)")
    args = ap.parse_args()

    con = sqlite3.connect(config.STATE_DB)
    rows = con.execute(
        "SELECT url, raw_path FROM source_document "
        "WHERE source_type='telegram_building_chat_msg' AND captured_at >= ?",
        (args.since,),
    ).fetchall()
    log.info("%d messages captured since %s to triage", len(rows), args.since)

    # hits[(tier, bucket)] -> list of (channel, date, url, snippet)
    hits: dict[tuple, list] = defaultdict(list)
    instrument_counts: Counter = Counter()
    instrument_examples: dict = {}
    scanned = 0
    recent = 0

    for url, path in rows:
        scanned += 1
        if scanned % 50000 == 0:
            log.info("  ... %d/%d scanned", scanned, len(rows))
        m = re.match(r"https://t\.me/([^/]+)/(\d+)", url)
        if not m:
            continue
        channel = m.group(1)
        try:
            d = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            continue
        text = (d.get("message") or "").strip()
        if not text:
            continue
        date = (d.get("date") or "")[:10]
        if args.year and not date.startswith(args.year):
            continue
        recent += 1
        t = tier(channel)

        for bucket, rx in THEMES.items():
            mm = rx.search(text)
            if mm:
                key = (t, bucket)
                if len(hits[key]) < MAX_PER_BUCKET:
                    s, e = max(0, mm.start() - 70), mm.end() + 90
                    snip = re.sub(r"\s+", " ", text[s:e]).strip()
                    hits[key].append((channel, date, url, snip))

        # instrument numbers (only on official/legal tiers -- news paraphrases are noisy)
        if t <= 1:
            for typ, num in INSTRUMENT_RE.findall(text):
                keyi = f"{typ.split()[0][:12]} №{num}"
                instrument_counts[keyi] += 1
                if keyi not in instrument_examples:
                    instrument_examples[keyi] = (channel, date, url)

    # write report
    out = ROOT / "data" / "reports" / "monitored_scan_triage_2026-07-21.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    tier_name = {0: "OFFICIAL/ADMIN", 1: "LEGAL/BEZKHOZ", 2: "NEWS/INTEL", 3: "OTHER"}
    with out.open("w", encoding="utf-8") as f:
        f.write(f"Monitored-channel scan triage — captured since {args.since}, "
                f"message-date year {args.year}\n")
        f.write(f"{len(rows)} messages scanned, {recent} in {args.year}\n\n")
        for t in (0, 1, 2, 3):
            for bucket in THEMES:
                key = (t, bucket)
                if key not in hits:
                    continue
                f.write(f"\n{'='*78}\n[{tier_name[t]}] {bucket}  ({len(hits[key])} hits"
                        f"{'+ (capped)' if len(hits[key])==MAX_PER_BUCKET else ''})\n{'='*78}\n")
                for ch, date, url, snip in sorted(hits[key], key=lambda x: -_datekey(x[1])):
                    f.write(f"  {date} @{ch} {url}\n    …{snip}…\n")
        f.write(f"\n\n{'#'*78}\nNUMBERED LEGAL INSTRUMENTS mentioned (official/legal tiers), "
                f"by frequency\n{'#'*78}\n")
        for inst, n in instrument_counts.most_common(150):
            ch, date, url = instrument_examples[inst]
            f.write(f"  {n:4}x  {inst:28}  e.g. {date} @{ch} {url}\n")
    log.info("wrote %s", out)
    print(f"triage written -> {out}  ({recent} {args.year} messages bucketed)")


def _datekey(d: str) -> int:
    return int(d.replace("-", "")) if d and d.replace("-", "").isdigit() else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
