#!/usr/bin/env python3
"""Load the courtyard grave-site record for ул. Грушевского, 10/12
(occupation address "ул. 60 лет СССР, 10/12" -- decommunization rename;
property_id 4690/4691) into the Postgres spine.

Sources:
  - Video, t.me/mariupolRIP/17883 (sha fa96a0e880a4...), posted 2026-05-02,
    an ~87s courtyard pan. Reviewed frame-by-frame (2026-07-21): 8 distinct
    graves confirmed, one (grave 1) self-identifying via a carved inscription
    "...дом кв.9 ул. Грушевского" -- the marker itself names the street.
  - 4-photo companion album, t.me/mariupolRIP/16611-16614 (grouped_id
    13208641807002994), posted 2026-04-27, captured by
    scripts/397_capture_grushevskogo_burial_album.py -- full-resolution
    close-ups that confirmed/corrected the video-frame reads of the 4 named
    markers (video misread grave 1's carved name as "Ищат"; full-res photo
    confirms "Шмат").

kind='civilian_casualty' -- established precedent, see scripts/163 (Lenina
110) and scripts/240 (Metallurgov 47). One record, all named + unnamed graves
in the detail payload, mirroring the shared-record pattern.

PRIVACY: all 4 named individuals are DECEASED, named on public grave markers
photographed and posted to a public Telegram channel -- not the project's
"living private owner" minimization rule (CLAUDE.md PRIVACY section), which
applies only to living owners.

Per project convention (CLAUDE.md "Generate scripts; do NOT auto-run
pandas/analysis. Let the user execute."), this writes to the canonical
Postgres spine and is NOT run by Claude -- run it yourself:

    PYTHONPATH=src .venv312/bin/python scripts/398_load_grushevskogo_burial_site.py --dry-run
    PYTHONPATH=src .venv312/bin/python scripts/398_load_grushevskogo_burial_site.py
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

# ул. Грушевского, 10 and 12 -- both properties share the one courtyard
PROPERTY_IDS = (4690, 4691)

SHA_VIDEO = "fa96a0e880a48a60c656006c5c1d198d90777813792d74173f2ab32bf93a17fb"
SHA_ALBUM_EMBED = "ada85802c38f69bd518e7f4494962f0ba63c04c8d959d2e2c4adabf740521950"
SHA_ALBUM_PHOTOS = {
    "vykhodtsev": "d923d82fd2c77d091328c5a46586f7f220e85869dd78f2c8c8336efbec220129",
    "golovina": "0a375c3449cbdc69764db47bbeaaf4c8a594c200a2b55efca522664458ad8227",
    "vasilenko": "aea5a9ef3c0bd7ac92420db818f333289549c823501e05c11f866c270e619018",
    "shmat": "5bccebc0fb3ca6ef0de9b50aa17a53716751425b264a1be82d5bb1103b9fc941",
}

DETAIL = {
    "title": "Дворовое захоронение, ул. Грушевского 10/12 (курс. \"ул. 60 лет СССР\")",
    "video_source": "https://t.me/mariupolRIP/17883",
    "video_date": "2026-05-02",
    "album_source": "https://t.me/mariupolRIP/16611",
    "album_date": "2026-04-27",
    "graves_total": 8,
    "graves_named": 4,
    "deceased": [
        {
            "name": "Шмат Борис Петрович",
            "dates": "1939 - 2022",
            "grave_no": 1,
            "circumstance": None,
            "marker_note": "Крест несёт также резную надпись \"...дом кв.9 "
                            "ул. Грушевского\" -- маркер сам указывает адрес.",
            "source_url": "https://t.me/mariupolRIP/16611",
            "additional_source": "https://t.me/mariupolRIP/17883 (видео, "
                                  "0:00-0:05, читалось как \"Ищат\" до "
                                  "уточнения по фотоальбому)",
        },
        {
            "name": "Василенко В.А.",
            "name_note": "Инициалы подтверждены пользователем как В.А. "
                          "(не В.Я., как ошибочно читалось с видео и с фото "
                          "крупного плана). Ни пол, ни полное имя не "
                          "прослеживаются по другим источникам (проверено "
                          "против всего корпуса t.me/mariupolRIP, 5,960 "
                          "сообщений, 2026-07-21) -- инициалы остаются "
                          "единственной опознавательной информацией.",
            "dates": None,
            "date_of_death": "2022-03-27",
            "grave_no": 4,
            "circumstance": None,
            "source_url": "https://t.me/mariupolRIP/16611",
            "additional_source": "https://t.me/mariupolRIP/17883 (видео, "
                                  "0:09-0:20)",
        },
        {
            "name": "Выходцев Александр Петрович",
            "dates": "27.02.1954 - 21.03.2022",
            "grave_no": 6,
            "circumstance": None,
            "source_url": "https://t.me/mariupolRIP/16611",
            "additional_source": "https://t.me/mariupolRIP/17883 (видео, "
                                  "0:25-0:40, имя было частично разборчиво "
                                  "до уточнения по фотоальбому)",
        },
        {
            "name": "Головина Марина",
            "dates": None,
            "date_of_death": "2022-03-16",
            "grave_no": 7,
            "circumstance": None,
            "marker_note": "Имя вырезано непосредственно в перекладине "
                            "креста (не на отдельной табличке); не было "
                            "разборчиво ни на одном сэмплированном кадре "
                            "видео до того, как пользователь указал на "
                            "конкретный скриншот, подтвердивший крест №7.",
            "source_url": "https://t.me/mariupolRIP/16611",
            "additional_source": "https://t.me/mariupolRIP/17883 (видео, "
                                  "~0:48-0:50)",
        },
    ],
    "unnamed_graves": [
        {"grave_no": 2, "marker": "белый металлический (трубный) крест, без таблички"},
        {"grave_no": 3, "marker": "белый металлический (трубный) крест, без таблички"},
        {"grave_no": 5, "marker": "чёрный декоративный металлический крест, "
                                   "бело-зелёный венок; табличка отсутствует "
                                   "на всех проверенных ракурсах"},
        {"grave_no": 8, "marker": "малый крест, холм полностью укрыт зелёным "
                                   "покрытием; видимый белый фрагмент -- "
                                   "цветок, не табличка"},
    ],
    "note": "8 могил подтверждено методичным покадровым просмотром видео "
            "(87 кадров, 1 fps) -- панорама представляет собой замкнутый "
            "проход по одному двору, не несколько отдельных площадок "
            "(кадры 070-087 возвращаются к тем же двум трубным крестам, "
            "видимым в кадре 001). Метод: см. лог сессии 2026-07-21.",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    import psycopg2
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    for property_id in PROPERTY_IDS:
        dedup_key = f"civilian_casualty:grushevskogo_10_12:{property_id}"
        if not args.dry_run:
            source_doc_id = _upsert_source_doc_by_sha(cur, SHA_VIDEO)
            cur.execute(
                """INSERT INTO corroboration
                       (property_id, kind, reference, detail, dedup_key,
                        captured_at, source_doc_id, confidence, verdict)
                   VALUES (%s, 'civilian_casualty', %s, %s, %s, now(),
                           %s, %s, 'confirms')
                   ON CONFLICT (dedup_key) DO UPDATE SET
                       detail = EXCLUDED.detail,
                       source_doc_id = EXCLUDED.source_doc_id""",
                (property_id, "mariupolRIP video + photo album "
                              "(courtyard grave site, 8 graves, 4 named)",
                 json.dumps(DETAIL, ensure_ascii=False), dedup_key,
                 source_doc_id, 0.85),
            )
        log.info("%s property_id %s -> dedup_key=%s (8 graves, 4 named)",
                  "[DRY RUN] would load" if args.dry_run else "loaded",
                  property_id, dedup_key)

    if not args.dry_run:
        con.commit()
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
