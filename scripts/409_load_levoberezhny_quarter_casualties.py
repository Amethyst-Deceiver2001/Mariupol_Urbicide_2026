#!/usr/bin/env python3
"""Load the Levoberezhny quarter casualty tally (scripts/408 output,
data/parsed/levoberezhny_quarter_casualties.jsonl) into corroboration as
one civilian_casualty row per building -- 48 buildings, 196 records (118
confirmed dead + 78 listed missing/без вести), all resolved to properties
within the Lomizova/50 let Oktyabrya(Meotidy)/Azovstalskaya/Komsomolsky-
Morskoy quarter.

Every record's underlying source is a t.me/mariupolRIP post cited in the
mariupoldestruction.com TSV (URL preserved per-person in `detail.deceased[
].source_url`) -- those individual posts have NOT been independently
captured (196 posts is a bulk-capture job, out of scope for this loader;
hand to the user as a follow-on capture script if the case study needs
per-person forensic snapshots later). The single forensic anchor for every
row here is the TSV snapshot itself (scripts/407, sha256 f6a2a3b9...),
already captured and present in source_document via
_upsert_source_doc_by_sha().

dedup_key format: civilian_casualty:levoberezhny_quarter_tsv:<building_id>

PRIVACY: all named individuals are DECEASED or listed missing/presumed
dead, sourced from a public grave/casualty-tracking spreadsheet built from
public Telegram posts -- not the project's "living private owner"
minimization rule.

Per project convention, this writes to the canonical Postgres spine and is
NOT run by Claude -- run it yourself:

    PYTHONPATH=src .venv312/bin/python scripts/409_load_levoberezhny_quarter_casualties.py --dry-run
    PYTHONPATH=src .venv312/bin/python scripts/409_load_levoberezhny_quarter_casualties.py
"""
import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.db.load import _upsert_source_doc_by_sha  # noqa: E402

log = logging.getLogger(__name__)

TSV_SHA = "f6a2a3b9ad4b39cb207405382ee8ef2068cfbc983282a63f9f6f1d61665119cd"
IN_PATH = ROOT / "data" / "parsed" / "levoberezhny_quarter_casualties.jsonl"


def _building_id_to_property_id(cur, building_id: str) -> int | None:
    cur.execute("SELECT id FROM property WHERE building_id = %s", (building_id,))
    row = cur.fetchone()
    return row[0] if row else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    import psycopg2
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    records = [json.loads(l) for l in open(IN_PATH, encoding="utf-8")]

    source_doc_id = None
    if not args.dry_run:
        source_doc_id = _upsert_source_doc_by_sha(cur, TSV_SHA)

    n_loaded = 0
    n_dead_total = 0
    n_missing_total = 0
    for rec in records:
        building_id = rec["building_id"]
        property_id = _building_id_to_property_id(cur, building_id)
        if property_id is None:
            log.warning("SKIP %s -- not found on spine (should not happen, spine changed?)", building_id)
            continue

        dedup_key = f"civilian_casualty:levoberezhny_quarter_tsv:{building_id}"
        confidence = 0.7  # TSV-sourced, cross-referenced against mariupolRIP corpus, not individually re-verified per post
        detail = {
            "title": f"Levoberezhny quarter casualty tally -- {building_id}",
            "location_note": (
                "Часть систематической сверки квартала Ломизова/50 лет "
                "Октября(Меотиды)/Азовстальская/Комсомольский(Морской) -- "
                "квартал полностью снесён и не восстановлен (см. "
                "распоряжение ГКО ДНР №54 от 29.09.2022). Данные извлечены "
                "из TSV-снимка Mariupol Destruction and Victims Map "
                "(https://www.mariupoldestruction.com), сопоставлены с "
                "объектом спины по адресу; НЕ подтверждены визуально "
                "по каждому отдельному посту t.me/mariupolRIP -- см. "
                "scripts/408 для методологии сопоставления."
            ),
            "deceased": rec["deceased"],
            "graves_total": rec["n_deceased"] + rec["n_missing"],
            "graves_named": sum(1 for d in rec["deceased"] if d["name"]),
            "n_deceased": rec["n_deceased"],
            "n_missing": rec["n_missing"],
        }

        if not args.dry_run:
            cur.execute(
                """INSERT INTO corroboration
                       (property_id, kind, reference, detail, dedup_key,
                        captured_at, source_doc_id, confidence, verdict)
                   VALUES (%s, 'civilian_casualty', %s, %s, %s, now(),
                           %s, %s, 'confirms')
                   ON CONFLICT (dedup_key) DO UPDATE SET
                       detail = EXCLUDED.detail,
                       source_doc_id = EXCLUDED.source_doc_id""",
                (property_id,
                 "Mariupol Destruction and Victims Map -- Levoberezhny quarter tally",
                 json.dumps(detail, ensure_ascii=False),
                 dedup_key, source_doc_id, confidence),
            )
        n_loaded += 1
        n_dead_total += rec["n_deceased"]
        n_missing_total += rec["n_missing"]
        log.info("%s %s -> property_id=%s (%d dead, %d missing)",
                  "[DRY RUN] would load" if args.dry_run else "loaded",
                  building_id, property_id, rec["n_deceased"], rec["n_missing"])

    log.info("=== %d buildings, %d confirmed dead, %d missing ===",
              n_loaded, n_dead_total, n_missing_total)

    if not args.dry_run:
        con.commit()
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
