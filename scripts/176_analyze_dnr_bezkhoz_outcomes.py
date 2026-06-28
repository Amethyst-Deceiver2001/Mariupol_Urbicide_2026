#!/usr/bin/env python3
"""Outcome analysis over the captured DNR Supreme Court bezkhoz appeal
population (scripts/175). Pure local analysis over the forensic store — no
network. Safe for Claude or the user to run.

WHAT THIS ANSWERS
-----------------
For the complete set of ВС ДНР appellate rulings of the type "признание права
муниципальной собственности на бесхозяйную недвижимую вещь" that the user
exhaustively pulled from the portal (2026-06-26, treated as the full
published population of this case type/court), classify the OWNER-SIDE
outcome of each appeal and tabulate the distribution, plus petitioner type,
object type, municipality, and the "outside RF territory" marker.

METHOD (two reconciled signals, never one regex over prose)
-----------------------------------------------------------
1. STRUCTURED metadata field "Результат рассмотрения" — a standardized GAS
   Правосудие result code present on every docket card, even the few whose
   full ruling text is NOT published.
2. PROSE disposition (after ОПРЕДЕЛИЛА:/РЕШИЛА:) — needed to disambiguate the
   two structured codes that are owner-direction-ambiguous on their own:
     - "оставлено без рассмотрения": petition-bounced (WIN, the admin must
       refile as an ordinary suit) vs appeal-dismissed (LOSE, a non-party's
       жалоба tossed so the lower grant stands). Disambiguated by whether the
       phrase attaches to заявление or жалоба, and by the presence of the
       "в порядке искового производства" advisory (unique to petition-bounce).
     - "...отменено ... с разрешением вопроса по существу": appellate court
       resolved it itself; check prose for "Признать право" (grant=LOSE) vs
       bounce vs remand.
   For the AFFIRM code ("оставлено БЕЗ ИЗМЕНЕНИЯ") the owner direction depends
   on what the first instance did (granted->LOSE, refused->WIN), read from the
   facts recital.

IMPORTANT INTERPRETIVE CAVEAT (do not strip when quoting these numbers)
-----------------------------------------------------------------------
A "WIN" here is almost always PROCEDURAL and TEMPORARY: the appellate court
reverses a first-instance grant because there is a "спор о праве" (a real
owner exists / wasn't joined as a party), which the simplified особое
производство track can't handle -- so the petition is bounced to ordinary
litigation, which the administration can and does refile. It is NOT a ruling
that seizing a displaced person's home is unlawful. And this population is
SELF-SELECTED: it is the set of cases where SOMEONE APPEARED to appeal. The
truly absent/abandoned owners' first-instance grants mostly are never
appealed and never enter this dataset at all -- so this is not the base rate
of seizure, it is the contest rate among those who managed to contest.

Run:
    .venv312/bin/python scripts/176_analyze_dnr_bezkhoz_outcomes.py
"""
from __future__ import annotations

import csv
import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bs4 import BeautifulSoup  # noqa: E402

from mariupol_seizures import forensics  # noqa: E402

log = logging.getLogger(__name__)

OUT_JSON = ROOT / "data" / "parsed" / "dnr_bezkhoz_outcomes.json"
OUT_CSV = ROOT / "data" / "parsed" / "dnr_bezkhoz_outcomes.csv"

CASE_NO_RX = re.compile(r"№\s*(33-\d+/\d{4})")
RESULT_RX = re.compile(r"Результат рассмотрения\n(.+?)\n(?:Основани|Номер здани|Судья)", re.S)
ZAYAV_RX = re.compile(r"ЗАЯВИТЕЛЬ\n(.+?)\n", re.S)
LOWER_COURT_RX = re.compile(r"Суд \(судебный участок\) первой инстанции\n(.+?)\n", re.S)
FACTS_ANCHOR_RX = re.compile(r"установил[аa]?\s*:", re.I)
DISP_ANCHOR_RX = re.compile(r"(?:ОПРЕДЕЛИЛ[аAА]?|РЕШИЛ[аAА]?)\s*:", re.I)

# first-instance disposition, from the facts recital
LOWER_GRANTED_RX = re.compile(
    r"(?:заявлени\w+ (?:Администрации|администрации)?[\s\S]{0,40}?удовлетвор"
    r"|признан\w+ право муниципальн\w+ собственности"
    r"|признано право муниципальной)", re.I)
LOWER_REFUSED_RX = re.compile(
    r"(?:в удовлетворении[\s\S]{0,40}?отказа|заявлени\w+[\s\S]{0,40}?оставлен\w+ без рассмотрения"
    r"|[Фф]онду[\s\S]{0,30}?отказан)", re.I)


def owner_outcome(result_code: str, disp: str, facts: str, text_published: bool) -> str:
    rc = result_code.lower()

    if "удовлетворен" in rc and "отказано" not in rc:
        return "LOSE_seizure_granted_on_appeal"
    if rc.strip() in ("отказано",) or "отказано в удовлетворении" in rc:
        return "WIN_petition_refused_on_merits"
    if "прекращено" in rc:
        return "WITHDRAWN_appeal_lower_stands"

    if "оставлено без рассмотрения" in rc or "оставлением заявление без рассмотрения" in rc:
        # The metadata result CODE is present even when the full ruling TEXT
        # (and so `disp`) is not published -- and this code is owner-direction-
        # ambiguous on its own (see module docstring). Guessing WIN by default
        # when there's no text to disambiguate from silently fabricates a
        # direction; admit unknown instead.
        if not text_published:
            return "UNKNOWN_full_text_not_published"
        # disambiguate petition-bounce (win) vs appeal-dismissed (lose)
        appeal_dismissed = re.search(
            r"жалоб\w+[\s\S]{0,160}?оставить без рассмотрения", disp)
        bounce_advisory = re.search(r"в порядке искового производства", disp)
        if appeal_dismissed and not bounce_advisory:
            return "LOSE_appeal_dismissed_grant_stands"
        return "WIN_petition_bounced_to_ordinary_suit"

    if "по существу" in rc:  # "...отменено ... с разрешением вопроса по существу"
        if not text_published:
            return "UNKNOWN_full_text_not_published"
        if re.search(r"[Пп]ризнать право (?:государственн\w+|муниципальн\w+)", disp):
            return "LOSE_seizure_granted_on_appeal"
        if re.search(r"в порядке искового производства", disp):
            return "WIN_petition_bounced_to_ordinary_suit"
        if re.search(r"(?:направить|возвратить)[\s\S]{0,250}?(?:по существу|на новое)", disp):
            return "NEUTRAL_remanded_for_merits"
        if not disp.strip():
            return "UNKNOWN_full_text_not_published"
        return "NEUTRAL_resolved_on_merits_direction_unclear"

    if "без изменения" in rc:
        # Same trap: "AFFIRM" needs the FACTS recital (which court's ruling
        # affirmed what) to know which side won. No facts recital means no
        # published text -- AFFIRM_lower_direction_unclear was silently
        # absorbing these instead of admitting the text isn't there.
        if not text_published:
            return "UNKNOWN_full_text_not_published"
        if LOWER_GRANTED_RX.search(facts):
            return "LOSE_lower_grant_affirmed"
        if LOWER_REFUSED_RX.search(facts):
            return "WIN_lower_refusal_affirmed"
        return "AFFIRM_lower_direction_unclear"

    return "UNCLASSIFIED:" + result_code[:50]


ROLLUP = {
    "WIN_petition_bounced_to_ordinary_suit": "WIN (procedural/temporary)",
    "WIN_petition_refused_on_merits": "WIN (procedural/temporary)",
    "WIN_lower_refusal_affirmed": "WIN (procedural/temporary)",
    "LOSE_seizure_granted_on_appeal": "LOSE (seizure granted/upheld)",
    "LOSE_appeal_dismissed_grant_stands": "LOSE (seizure granted/upheld)",
    "LOSE_lower_grant_affirmed": "LOSE (seizure granted/upheld)",
    "NEUTRAL_remanded_for_merits": "NEUTRAL (claim revived/remanded)",
    "NEUTRAL_resolved_on_merits_direction_unclear": "NEUTRAL (claim revived/remanded)",
    "UNKNOWN_full_text_not_published": "UNKNOWN (text unpublished)",
    "WITHDRAWN_appeal_lower_stands": "WITHDRAWN",
    "AFFIRM_lower_direction_unclear": "UNKNOWN (affirm, lower unclear)",
}


def petitioner_type(z: str) -> str:
    if "Фонд" in z:
        return "FGI_state_property_fund"
    if "дминистрац" in z:
        return "municipal_administration"
    if "инистерств" in z:
        return "ministry"
    if "ФГУП" in z or "унитарн" in z:
        return "state_unitary_enterprise"
    return "other"


def object_type(text: str) -> str:
    has_res = re.search(r"квартир|жил\w+ дом|жило\w+ помещение", text)
    has_non = re.search(r"нежило\w+|встроенн\w+ помещени|нежилое здание", text)
    if has_res and not has_non:
        return "residential"
    if has_non and not has_res:
        return "nonresidential"
    return "unclear"


def main() -> None:
    con = forensics.open_state()
    rows = con.execute(
        "SELECT sha256, url, raw_path FROM source_document "
        "WHERE source_type='dnr_supreme_court_docket_case'"
    ).fetchall()

    records = []
    for sha, url, rp in rows:
        p = Path(rp)
        if not p.exists():
            continue
        text = BeautifulSoup(p.read_text(encoding="cp1251", errors="replace"),
                             "lxml").get_text("\n", strip=True)
        if "бесхоз" not in text.lower():
            continue  # filters Troianda-M-type and other non-bezkhoz drift
        cm = CASE_NO_RX.search(text)
        rm = RESULT_RX.search(text)
        zm = ZAYAV_RX.search(text)
        lcm = LOWER_COURT_RX.search(text)
        result_code = rm.group(1).strip() if rm else "<none>"
        # "Судебный акт" heading only appears when a ruling document is embedded
        # in the card -- absent on metadata-only (text-not-published) cards,
        # where the facts/disp anchors below also won't be found. Without this
        # flag the classifier branches were silently guessing a direction from
        # an empty match instead of admitting the text isn't there.
        text_published = "Судебный акт" in text
        facts_m = FACTS_ANCHOR_RX.search(text)
        # affirm-branch needs the lower-court disposition, which can sit beyond a
        # fixed window in long rulings -> give that branch the full post-facts text.
        facts = text[facts_m.end():] if facts_m else text
        disp_m = DISP_ANCHOR_RX.search(text, facts_m.end() if facts_m else 0)
        disp = text[disp_m.end():disp_m.end() + 1600] if disp_m else ""
        # collapse newlines/runs to single spaces -- the GAS text is newline-joined,
        # but the clause regexes use literal spaces (a phrase split across lines
        # would otherwise silently fail to match).
        facts = re.sub(r"\s+", " ", facts)
        disp = re.sub(r"\s+", " ", disp)
        outcome = owner_outcome(result_code, disp, facts, text_published)
        records.append({
            "case": cm.group(1) if cm else "?",
            "result_code": result_code,
            "outcome": outcome,
            "rollup": ROLLUP.get(outcome, "UNKNOWN/UNCLASSIFIED"),
            "text_published": text_published,  # persisted so the Mariupol-vs-
            # rest text-unpublished gap is reproducible from this artifact alone
            "petitioner": petitioner_type(zm.group(1).strip() if zm else ""),
            "object": object_type(text),
            "lower_court": lcm.group(1).strip() if lcm else None,
            "mariupol": "Мариупол" in text,
            "outside_rf": "за пределами Российской Федерации" in text,
            "url": url, "sha": sha[:16],
        })

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(records[0].keys()))
        w.writeheader()
        w.writerows(records)

    n = len(records)
    print(f"\n{'='*72}\nDNR Supreme Court bezkhoz appeal population — {n} cases\n{'='*72}")
    print("\nOWNER-SIDE OUTCOME (rolled up):")
    for k, v in Counter(r["rollup"] for r in records).most_common():
        print(f"  {v:3d}  ({100*v/n:4.1f}%)  {k}")
    print("\n  detail:")
    for k, v in Counter(r["outcome"] for r in records).most_common():
        print(f"     {v:3d}  {k}")
    print("\nPETITIONER:")
    for k, v in Counter(r["petitioner"] for r in records).most_common():
        print(f"  {v:3d}  {k}")
    print("\nOBJECT TYPE:", dict(Counter(r["object"] for r in records)))
    print("MARIUPOL:", sum(1 for r in records if r["mariupol"]),
          "| rest of DNR:", sum(1 for r in records if not r["mariupol"]))
    print("Owner explicitly 'outside RF territory':",
          sum(1 for r in records if r["outside_rf"]))
    print(f"\n  → {OUT_JSON}\n  → {OUT_CSV}")
    print("\n  REMINDER: a 'WIN' is procedural+temporary (petition bounced to "
          "ordinary\n  suit, refileable); this population is self-selected to "
          "cases someone\n  appealed. See the module docstring before quoting "
          "any number.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
