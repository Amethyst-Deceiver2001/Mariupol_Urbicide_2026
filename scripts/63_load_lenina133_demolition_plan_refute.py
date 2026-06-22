#!/usr/bin/env python3
"""Load a corroboration(kind='testimony_ref', verdict='refutes') row for
property 4442 (просп. Ленина (Мира), 133), refuting the "100% destruction /
Phase II demolish" implication of corroboration id 1412 (mirror_source, the
federal damage/reconstruction tracker).

Background: id 1412 lists this building (group="4"/demolish, destruction_pct
=100.0, priority_phase="II", contractor "ГК Трансстройинвест", responsible
executor ППК "Единый заказчик"). The @Lenina133 resident chat (scripts 62)
shows this corresponds to a real, dated official "ПАСПОРТ ОБЪЕКТА"
demolish-and-rebuild plan posted 9 Dec 2022 for пр. Мира 133 (Застройщик =
Минстрой РФ, Заказчик = ППК "Единый заказчик", Генподрядчик = ООО "РКС-НР",
начало строительства IV кв. 2022 -> окончание III кв. 2023) and a sister
plan for the neighboring пр. Мира 135.

But residents had ALREADY reoccupied and self-repaired the building (new
windows, roof, electrical/plumbing, entrance canopy -- msgs 11-54, 99/100,
Nov-Dec 2022) BEFORE this passport was even posted, residents themselves
flagged the "construction not капремонт" designation as suspicious (msg 149,
21 Dec 2022: "плиты перекрытия слабые .. озвучила комиссия из Москвы", no
resident notification/meeting held), and as of 2026 the building still
stands -- never demolished -- with individual apartments (2, 19, 33) instead
being seized piecemeal via the "ownerless" registry track (corroboration id
5417). The official demolish-rebuild plan that id 1412 reflects was never
executed.

No schema change: corroboration.kind/.detail free-form, verdict CHECK allows
'refutes'. Idempotent: dedup_key = 'testimony_ref:<passport_photo_sha>:4442:demolition_plan_refute'.
"""
import json
import logging
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.db.load import _upsert_source_doc_by_sha  # noqa: E402

log = logging.getLogger("load_lenina133_demolition_plan_refute")

BUILDING_ID = "AVENUE:ленина|133"

# msg 91 media: "ПАСПОРТ ОБЪЕКТА" sign posted on пр. Мира 133 itself
# (9-этажный, 4440 m2, Застройщик Минстрой РФ, Заказчик ППК "Единый заказчик",
# Генподрядчик ООО "РКС-НР", начало стр-ва IV кв.2022 -> окончание III кв.2023)
PASSPORT_133_PHOTO_SHA = "b14fb5cee22aaad6ec93d306fee87bc751d17a42e9bf6d891b24a16fd7eac6b2"
# msg 92 media: sister "ПАСПОРТ ОБЪЕКТА" sign for the neighboring пр. Мира 135
PASSPORT_135_PHOTO_SHA = "d090b996ecb41516e6cb80a59426b2d9c493fd115e89abef3b97e85ed293930a"
# msg 51 media: "Остекление со стороны сгоревших балконов" (25 Nov 2022) --
# reglazing of the fire-damaged side already underway
REGLAZING_PHOTO_SHA = "d8868a43ac198d9b361f0ba7cb893ee954c54235d4e66bc8c28126bf76fbd997"
# msg 99 media: repaired exterior, new windows + renewed entrance canopy
# (10 Dec 2022)
REPAIRED_EXTERIOR_PHOTO_SHA = "d2153ab0f7441a076ac135ef23b29cc037e9a956e86abdf7b3c3b8fd4f39d915"
# msg 149 text: residents' own commentary flagging "construction not
# капремонт", weak floor slabs, "commission from Moscow", no resident
# notification (21 Dec 2022)
COMMENTARY_MSG_SHA = "c0d97bf77bdca69fbaa2ab48c7d560bb5916ae92d04c3235851a1e56c24039f1"

UPSERT_CORRO_SQL = """
    INSERT INTO corroboration
        (property_id, kind, reference, detail, dedup_key, captured_at,
         source_doc_id, confidence, verdict, observed_start, observed_end)
    VALUES (%s, 'testimony_ref', %s, %s, %s, now(), %s, %s, 'refutes', %s, %s)
    ON CONFLICT (dedup_key) DO UPDATE
        SET reference      = EXCLUDED.reference,
            detail         = EXCLUDED.detail,
            captured_at    = now(),
            source_doc_id  = EXCLUDED.source_doc_id,
            confidence     = EXCLUDED.confidence,
            verdict        = EXCLUDED.verdict,
            observed_start = EXCLUDED.observed_start,
            observed_end   = EXCLUDED.observed_end
    RETURNING id
"""


def main() -> None:
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    cur.execute("SELECT id FROM property WHERE building_id = %s", (BUILDING_ID,))
    row = cur.fetchone()
    if row is None:
        raise SystemExit(f"property with building_id={BUILDING_ID!r} not found")
    property_id = row[0]
    log.info("property_id=%s (building_id=%s)", property_id, BUILDING_ID)

    source_doc_id = _upsert_source_doc_by_sha(cur, PASSPORT_133_PHOTO_SHA)
    log.info("source_document id for passport photo (%s) -> %s",
             PASSPORT_133_PHOTO_SHA, source_doc_id)

    detail = {
        "source": "telegram_chat",
        "channel": "Lenina133",
        "refutes_corroboration_id": 1412,
        "refutes_claim": (
            "damage_assessment row for property 4442 (seq_no 122): "
            "group='4' (demolish), destruction_pct=100.0, "
            "priority_phase='II', contractor='ГК Трансстройинвест', "
            "responsible_executor='ППК \"Единый заказчик\"'"
        ),
        "official_plan_found": {
            "doc_type": "ПАСПОРТ ОБЪЕКТА",
            "address": "г. Мариуполь, проспект Мира, д. 133",
            "застройщик": "Министерство строительства РФ",
            "заказчик": 'ППК "Единый заказчик в сфере строительства"',
            "генеральный_подрядчик": 'ООО "РКС-НР"',
            "площадь_м2": 4440,
            "этажность": 9,
            "начало_строительства": "2022-Q4",
            "окончание_строительства": "2023-Q3",
            "photo_post_date": "2022-12-09",
            "photo_sha256": PASSPORT_133_PHOTO_SHA,
            "post_url": "https://t.me/Lenina133/91",
            "sister_passport_for_neighboring_building": {
                "address": "г. Мариуполь, проспект Мира, д. 135",
                "площадь_м2": 1900,
                "этажность": 5,
                "photo_sha256": PASSPORT_135_PHOTO_SHA,
                "post_url": "https://t.me/Lenina133/92",
            },
        },
        "as_built_reality": {
            "summary": (
                "Building 133 was NOT demolished. Residents document "
                "active reoccupation and self/contractor repair (new "
                "roof, windows, electrical/plumbing, entrance canopy) "
                "FROM 21 Nov 2022, i.e. BEFORE the 9 Dec 2022 demolish-"
                "rebuild passport was even posted. The same structure "
                "stands as of 2026, still bearing the fire-damage scars "
                "visible in the reglazing photo. Instead of wholesale "
                "demolition/reconstruction, individual apartments "
                "(2, 19, 33) were later seized piecemeal via the "
                "'ownerless' registry track (see corroboration id 5417, "
                "apt 19, sealed Oct 2025)."
            ),
            "reoccupation_start": "2022-11-21",
            "reglazing_of_fire_damaged_balconies": {
                "date": "2022-11-25",
                "photo_sha256": REGLAZING_PHOTO_SHA,
                "post_url": "https://t.me/Lenina133/51",
            },
            "repaired_exterior_new_windows_and_canopy": {
                "date": "2022-12-10",
                "photo_sha256": REPAIRED_EXTERIOR_PHOTO_SHA,
                "post_url": "https://t.me/Lenina133/99",
            },
            "resident_commentary": {
                "date": "2022-12-21",
                "text_excerpt": (
                    "Чётко указано начало и окончание строительства но не "
                    "РЕМОНТА КАПИТАЛЬНОГО....возможно опечатка НО ВРЯД ЛИ.."
                    "..дома хотели СНЕСТИ И ПОСТРОИТЬ НОВЫЕ....ЛУЧШЕ БЫ ТАК "
                    "И СДЕЛАЛИ ПОТОМУ КАК ПЛИТЫ ПЕРЕКРЫТИЯ СЛАБЫЕ...."
                    "ОЗВУЧИЛА КОМИССИЯ ИЗ МОСКВЫ"
                ),
                "sha256": COMMENTARY_MSG_SHA,
                "post_url": "https://t.me/Lenina133/149",
                "note": (
                    "Residents themselves flag the demolish-rebuild "
                    "designation as suspicious -- no resident meeting or "
                    "notification preceded it (msg 150, same date)."
                ),
            },
        },
        "interpretation": (
            "id 1412 is not a wrong-building mismatch -- it reflects a "
            "real, dated (Dec 2022) official demolish-rebuild "
            "designation for this exact building. But that designation "
            "describes an unexecuted PLAN, not as-built reality: the "
            "100% destruction / demolish classification was never "
            "carried out, the building stands today, and the occupation "
            "pursued individual-apartment 'ownerless' seizure instead."
        ),
    }
    reference = (
        "@Lenina133 resident chat (scripts 62): dated photos/posts "
        "(Nov-Dec 2022) show the building reoccupied and repaired before "
        "and after a 9 Dec 2022 official 'ПАСПОРТ ОБЪЕКТА' demolish-"
        "rebuild plan was posted for the same address; the plan (which "
        "corroboration id 1412 reflects) was never executed -- refutes "
        "the demolition/100%-destruction outcome implied by id 1412"
    )
    dedup_key = (
        f"testimony_ref:{PASSPORT_133_PHOTO_SHA}:{property_id}:"
        "demolition_plan_refute"
    )

    cur.execute(UPSERT_CORRO_SQL, (
        property_id, reference, json.dumps(detail, ensure_ascii=False),
        dedup_key, source_doc_id, 0.85, "2022-11-21", "2022-12-21",
    ))
    corro_id = cur.fetchone()[0]
    con.commit()
    cur.close()
    con.close()
    log.info("upserted corroboration id=%s for property_id=%s (dedup_key=%s)",
             corro_id, property_id, dedup_key)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    main()
