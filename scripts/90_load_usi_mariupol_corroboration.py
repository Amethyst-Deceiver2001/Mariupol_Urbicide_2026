#!/usr/bin/env python3
"""Load corroboration rows for the usi-mariupol.ru (ЮгСтройИнвест) site crawl.

Three demolish->rebuild findings from the same-domain crawl (script 86) of the
developer's own marketing site:

  1. ул. Зелинского, 23 (pid=4844) — EXACT address match. Demolition order
     №144, 12.12.2022. New-build landing page "Резиденция Концепт" literally
     calls the new building "дом Зелинского, 23" — same address reused on the
     cleared footprint, no renumbering. Highest-confidence pair found to date.

  2. бул. Богдана Хмельницкого, 20 (pid=4326, corpse-note property, Group 4,
     100% destroyed) — SAME-BLOCK match. The АУРА project's DDU template is
     for "бул. Богдана Хмельницкого, 16а" on a new land cadastral
     (93:37:0010103:3861), immediately adjacent on the same boulevard.
     Address-laundering candidate, not an exact address reuse — confidence
     accordingly lower than case 1.

  3. "Приморье" megaproject (13 buildings, 30.77 ha) — PERIMETER match only.
     The marketing page's own bounding-street description (пр. Ленина / ул.
     Краснофлотская / ул. Просторная / Западная / ул. Новороссийская / просп.
     Нахимова / ул. Гагарина / ул. Восстания / ул. Латышева) contains 23
     spine properties with an already-loaded demolition event. This is a
     street-perimeter match, NOT a parcel-level GIS overlay (no cadastral was
     published for Приморье) — loaded at low confidence with that caveat
     recorded in `detail`.

Run:
    python scripts/90_load_usi_mariupol_corroboration.py [--dry-run]
"""
import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger(__name__)

KIND_SAME_ADDRESS = "developer_new_build_same_address"
KIND_SAME_BLOCK    = "developer_new_build_same_block"
KIND_PERIMETER     = "developer_new_build_perimeter_candidate"

PRIMORYE_PIDS = [
    5993, 5994, 5995, 5996, 5997, 5998, 5999, 6000, 6001, 6002, 6003, 6004,
    6016, 6017, 6018, 6019, 6021, 6022, 6023, 6241, 6246, 13986, 13993,
]


def main(dry_run: bool = False) -> None:
    import psycopg2
    from mariupol_seizures.db.load import _upsert_source_doc_by_sha  # noqa: E402

    conn = psycopg2.connect(config.DATABASE_URL)
    cur  = conn.cursor()

    sha_koncept_l = "7d837bc8d6cf9edcbeca0df172ebe339b0c08af77e9334f7e4816634ac2d015d"
    sha_aura_pdf  = "aec4c92f17cb3d7bf0ca8aa855ef4079fd7673436dff2d4280d3e1820d78ca1f"
    sha_primorye  = "c9cd215de5ba5999b7b6915a91833bbd48415e88154db3f2813074736324f199"

    if dry_run:
        log.info("dry-run: would load 1 + 1 + %d = %d corroboration rows",
                  len(PRIMORYE_PIDS), 2 + len(PRIMORYE_PIDS))
        return

    src_koncept_l = _upsert_source_doc_by_sha(cur, sha_koncept_l)
    src_aura      = _upsert_source_doc_by_sha(cur, sha_aura_pdf)
    src_primorye  = _upsert_source_doc_by_sha(cur, sha_primorye)

    loaded = 0

    # ── Case 1: Зелинского, 23 — exact address reuse ──────────────────────────
    detail = json.dumps({
        "developer": "OOO SZ-1 Porfir / GK YugStroyInvest",
        "project_name": "Резиденция Концепт (Новый квартал у моря)",
        "source_url": "https://usi-mariupol.ru/landing/rezidenciya-koncept-l/",
        "match_type": "exact_address_reuse",
        "demolition_order": "Распоряжение администрации г.Мариуполя от 12.12.2022 № 144",
        "site_area_ga": 4.3864,
        "construction_type": "Монолит-Каркас",
        "keys_delivery": "4 квартал 2026",
        "evidentiary_note": (
            "Developer's own marketing copy refers to the new building's ground-floor "
            "commercial space as located 'в доме Зелинского, 23' — the same street "
            "address as the demolished MKD (order №144, 12.12.2022), with no "
            "renumbering. Direct evidence of address continuity across demolish-rebuild."
        ),
    }, ensure_ascii=False)
    cur.execute("""
        INSERT INTO corroboration
          (property_id, kind, reference, source_doc_id, confidence,
           detail, dedup_key, captured_at, verdict)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), 'confirms')
        ON CONFLICT (dedup_key) DO UPDATE
            SET detail = EXCLUDED.detail, captured_at = NOW()
    """, (
        4844, KIND_SAME_ADDRESS,
        "https://usi-mariupol.ru/landing/rezidenciya-koncept-l/",
        src_koncept_l, 0.9, detail,
        "usi_mariupol_zelinskogo23_koncept_l",
    ))
    loaded += 1
    log.info("loaded pid=4844 (Зелинского, 23) — Резиденция Концепт")

    # ── Case 2: Хмельницкого, 20 — same-block АУРА new-build ──────────────────
    detail = json.dumps({
        "developer": "OOO SZ-1 Porfir (INN 9310009271, OGRN 1239300008870), GK YugStroyInvest",
        "project_name": "АУРА",
        "source_url": "https://usi-mariupol.ru/assets/files/aura-2-2.pdf",
        "match_type": "same_block_adjacent",
        "new_build_address": "бул. Богдана Хмельницкого, 16а",
        "new_land_cadastral": "93:37:0010103:3861",
        "new_land_area_sqm": 7584.0,
        "evidentiary_note": (
            "АУРА DDU template covers a new land plot at бул. Богдана Хмельницкого, "
            "16а, immediately adjacent on the same boulevard to pid=4326 (б-р Хмельницкого, "
            "20 — corpse-note property, Group 4, 100% destruction). Same-block "
            "candidate for the demolish-rebuild pattern; NOT an exact address match, "
            "confidence set lower than the Зелинского case accordingly."
        ),
    }, ensure_ascii=False)
    cur.execute("""
        INSERT INTO corroboration
          (property_id, kind, reference, source_doc_id, confidence,
           detail, dedup_key, captured_at, verdict)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), 'confirms')
        ON CONFLICT (dedup_key) DO UPDATE
            SET detail = EXCLUDED.detail, captured_at = NOW()
    """, (
        4326, KIND_SAME_BLOCK,
        "https://usi-mariupol.ru/assets/files/aura-2-2.pdf",
        src_aura, 0.65, detail,
        "usi_mariupol_khmelnickogo20_aura",
    ))
    loaded += 1
    log.info("loaded pid=4326 (бул. Хмельницкого, 20) — АУРА")

    # ── Case 3: Приморье perimeter — 23 already-demolished spine properties ──
    for pid in PRIMORYE_PIDS:
        detail = json.dumps({
            "developer": "GK YugStroyInvest",
            "project_name": "Приморье",
            "source_url": "https://usi-mariupol.ru/landing/primore-landing/",
            "match_type": "street_perimeter_only",
            "project_buildings": 13,
            "project_area_ga": 30.77,
            "project_floors": "12-17",
            "construction_type": "Монолит-каркас",
            "caveat": (
                "Perimeter match only — property's street name falls within the "
                "marketing page's bounding-street description of the Приморье site, "
                "but no cadastral number was published for the project, so this is "
                "NOT a confirmed parcel-level GIS overlay. Treat as a lead requiring "
                "map review, not a settled demolish-rebuild pair."
            ),
        }, ensure_ascii=False)
        cur.execute("""
            INSERT INTO corroboration
              (property_id, kind, reference, source_doc_id, confidence,
               detail, dedup_key, captured_at, verdict)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), 'confirms')
            ON CONFLICT (dedup_key) DO UPDATE
                SET detail = EXCLUDED.detail, captured_at = NOW()
        """, (
            pid, KIND_PERIMETER,
            "https://usi-mariupol.ru/landing/primore-landing/",
            src_primorye, 0.4, detail,
            f"usi_mariupol_primorye_perimeter_{pid}",
        ))
        loaded += 1

    conn.commit()
    conn.close()

    print(f"\n{'='*60}")
    print("usi-mariupol.ru corroboration load complete")
    print(f"  Зелинского 23 (exact)         : 1 row,  conf=0.90")
    print(f"  Хмельницкого 20 (same-block)  : 1 row,  conf=0.65")
    print(f"  Приморье (perimeter, caveat)  : {len(PRIMORYE_PIDS)} rows, conf=0.40")
    print(f"  Total loaded                 : {loaded}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
