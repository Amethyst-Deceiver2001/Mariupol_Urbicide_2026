#!/usr/bin/env python3
"""Load the churchyard grave-site record for ул. Гонды, 40А -- backyard of
the temple of Sv. Vera, Nadezhda, Lyubov i mat' ikh Sofia (Храм Веры,
Надежды, Любови и матери их Софии), 47°07'36.59"N 37°34'02.12"E.

No `property` row exists for this address (institutional/religious site,
genuinely off-spine -- confirmed 2026-07-21 by cross-referencing bordering
streets Металлургов 180-199, Покрышкина, and Гонды 2-105а, none of which
include "40А"). corroboration.property_id is left NULL; location and
address context are carried in `detail` instead, consistent with how
address-less court-island rows already work on this spine
(memory/court_islands_address_gap_2026-06.md).

Sources:
  - t.me/Z2022sw/558, 3-photo grave-marker album, captured by
    scripts/401_capture_gondy_grave_album.py. Names: Цыганкова Светлана
    Яковлевна, Бабич Анатолий Леонтьевич, Еременко Антонина (patronymic
    illegible), partial Науменко С.И. fragment.
  - Моторин Николай Владимирович -- cross photo supplied directly by the
    user in-session (not from a capturable t.me URL); dates partially
    cropped in the photo ("16.11.19??" / "20??"). Chain of custody for
    this one image is the session transcript, not the raw store -- flagged
    explicitly in its detail entry.
  - t.me/nmrpl/6259 (official Ilyichevsk district admin, АГО МАРИУПОЛЬ),
    captured by scripts/400_capture_gondy_clearance_post.py -- confirms
    50+ wartime burials, subsequent reburial elsewhere, and site
    landscaping, dated 2023-03-30.
  - Satellite timeline (user-supplied Google Earth screenshots, not
    programmatically accessible to this project): graves visible
    9 May 2022; site fully cleared by 8 Aug 2024. Independent Sentinel-2
    corroboration attempted (Planetary Computer, 4 windows) but confirmed
    too coarse (10m/pixel) to resolve grave-level detail -- noted, not
    loaded as a separate corroboration row.

Grave count: ~30 estimated from the 3-photo album (undercount -- the
official nmrpl/6259 post states "свыше 50-и погибших", i.e. the album
does not depict the full site). This is the same self-critical framing
used for the Грушевского 10/12 site loader (scripts/398): the *named*
count is exact, the *total* count is a floor, not a census.

kind='civilian_casualty' -- established precedent, see scripts/163
(Lenina 110), scripts/240 (Metallurgov 47), scripts/398 (Grushevskogo
10/12).

PRIVACY: all named individuals are DECEASED, named on public grave
markers photographed and posted to public Telegram channels -- not the
project's "living private owner" minimization rule (CLAUDE.md PRIVACY
section), which applies only to living owners.

Per project convention (CLAUDE.md "Generate scripts; do NOT auto-run
pandas/analysis. Let the user execute."), this writes to the canonical
Postgres spine and is NOT run by Claude -- run it yourself:

    PYTHONPATH=src .venv312/bin/python scripts/402_load_gondy_burial_site.py --dry-run
    PYTHONPATH=src .venv312/bin/python scripts/402_load_gondy_burial_site.py
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

SHA_GRAVE_ALBUM_EMBED = "5576f7bdc94e7c30dd8bb9fa44e5f5df5f7e6c92933a9bb37e68ecc386781f15"
SHA_GRAVE_ALBUM_PHOTOS = {
    "tsygankova_babich_naumenko": "186b1e977ad4b0e3cfd2e86f229369bc73098f51f5da329250bc5f46a4842ad6",
    "wide_second_angle": "c94db453e6e18360878fbf43ca897505db5be276bbff33ae18efcf7955c4ee14",
    "eremenko": "48b335ff0520a3d30ac75fc242f4f963126ad487a4c467be47c85bdc10ac0e0d",
}
SHA_CLEARANCE_EMBED = "a6f680e8dcdf563d6b9231711c5d08ba820b0d5d865197d677067118d9256935"
SHA_CLEARANCE_PHOTOS = {
    "backhoe_grading": "49cedb95c16cbce3845de53870477dd3836032d1b737a98ec3df0f42fb997df9",
    "backhoe_apartment_block_bg": "f7a0b58a249828267e3ec1dfdd25c1b8b2e61773432b89cf36e95718f57ee849",
    "backhoe_church_wide": "353c10a7a529e5e71568be2e6cf0f68bfe235199f10fc105175891738bd6123b",
}
# independent wide-angle photo found during the 2026-07-21 mariupolRIP
# systematic backlog review (msg 18005, dated 2022-05-02 -- earlier than
# any other reference point on file). Already resident in data/raw/ via
# scripts/310's media pull; not yet registered in source_document, which
# _upsert_source_doc_by_sha() does automatically from the SQLite forensic
# log at load time (same as every other sha referenced in this file).
SHA_WIDE_SHOT_MSG18005 = "0540f37d5a8fab3e9c6447b5a89ffa8405ad9af216a6bd071cf1e03cdd5b641f"

DETAIL = {
    "title": "Приходское захоронение, ул. Гонды 40А (у Храма Веры, Надежды, "
             "Любови и матери их Софии)",
    "coordinates": "47°07'36.59\"N 37°34'02.12\"E",
    "address_note": "Здание церкви/кладбище отсутствует в реестре property "
                     "(институциональный объект вне жилого фонда) -- "
                     "подтверждено сверкой сопредельных улиц (Металлургов "
                     "180-199, Покрышкина, Гонды 2-105а; \"40А\" среди них "
                     "не значится, только смежный дом \"40\") 2026-07-21.",
    "grave_album_source": "https://t.me/Z2022sw/558",
    "clearance_post_source": "https://t.me/nmrpl/6259",
    "clearance_post_date": "2023-03-30",
    "graves_total_estimate": 30,
    "graves_total_note": "Оценка по 3-фотографическому альбому -- заведомый "
                          "минимум, а не перепись: официальный пост "
                          "nmrpl/6259 указывает \"свыше 50-и погибших\", "
                          "т.е. альбом не охватывает весь участок.",
    "graves_named": 5,
    "deceased": [
        {
            "name": "Цыганкова Светлана Яковлевна",
            "dates": "06.1938 - 04.04.2022",
            "source_url": "https://t.me/Z2022sw/558",
        },
        {
            "name": "Бабич Анатолий Леонтьевич",
            "dates": "1941 - 09.04.2022",
            "source_url": "https://t.me/Z2022sw/558",
        },
        {
            "name": "Еременко Антонина",
            "name_note": "Отчество неразборчиво на маркере.",
            "dates": None,
            "source_url": "https://t.me/Z2022sw/558",
        },
        {
            "name": "Науменко С.И.",
            "name_note": "Пол и полное имя не установлены -- инициалы "
                          "видны фрагментарно на одном из маркеров.",
            "dates": None,
            "source_url": "https://t.me/Z2022sw/558",
        },
        {
            "name": "Моторин Николай Владимирович",
            "dates": "16.11.19?? - 20?? (даты частично обрезаны на фото креста)",
            "source_note": "Фотография креста предоставлена пользователем "
                            "напрямую в сессии, не из поста t.me/Z2022sw/558 "
                            "-- цепочка хранения для этого снимка: "
                            "стенограмма сессии, не сырое хранилище "
                            "(data/raw). Требует отдельного захвата, если "
                            "будет найден исходный URL.",
        },
    ],
    "clearance": {
        "official_text_excerpt": "«Во время боевых действий рядом с храмом "
                                  "пришлось захоронить свыше 50-и погибших. "
                                  "После перезахоронения на территории "
                                  "остались ямы, также необходимо было "
                                  "убрать ветки, сухостой и скопившийся "
                                  "мусор» -- Наталья Мартыненко, секретарь "
                                  "КСН «Центральный-2»",
        "date": "2023-03-30",
        "actors": ["МУП АГМ «Зеленстрой»",
                   "отдел коммунального хозяйства и благоустройства "
                   "Ильичевской райадминистрации",
                   "подрядная организация «Строймонолит»"],
        "named_individuals": ["Наталья Мартыненко (секретарь КСН "
                               "«Центральный-2»)", "отец Геннадий "
                               "(настоятель храма)"],
        "note": "Официальная формулировка -- \"перезахоронение\" (без "
                "указания места), а не эксгумация с целью идентификации; "
                "пост не упоминает уведомление семей, протоколы "
                "идентификации остан или место повторного захоронения.",
    },
    "satellite_timeline": {
        "2022-05-09": "могилы видны (Google Earth, снимок предоставлен "
                       "пользователем)",
        "2023-03-30": "начало работ по благоустройству (nmrpl/6259)",
        "2024-08-08": "участок полностью расчищен (Google Earth, снимок "
                       "предоставлен пользователем)",
        "sentinel2_note": "Независимая попытка через Planetary Computer "
                           "(4 окна: 2022-07-07/2023-08-06/2024-09-29/"
                           "2026-05-22) подтвердила разрешение 10 м/пиксель "
                           "недостаточным для детализации на уровне "
                           "отдельных могил -- полезно только для общей "
                           "проверки характера участка, не загружено как "
                           "отдельная запись corroboration.",
    },
    "bordering_properties_checked": {
        "Металлургов": "180-199 (16 объектов на спине)",
        "Покрышкина": "2,3,9,11,12,13,16,18,20,99 (10 объектов)",
        "Гонды": "2,36,38,40,42,46,48а,76,105а (8 объектов; \"40А\" "
                 "отсутствует, участок вне застройки)",
    },
    "independent_corroboration": {
        "source_url": "https://t.me/mariupolRIP/18005",
        "date": "2022-05-02",
        "note": "Широкоугольная фотография того же участка (читаются "
                "маркеры Цыганкова, Бабич, Еременко -- совпадают с уже "
                "загруженными записями), снятая на 3 недели раньше "
                "спутникового ориентира 9 мая 2022. В одном кадре видно "
                "не менее 15 отдельных могильных холмов -- независимо "
                "подтверждает масштаб участка и оценку \"~30, вероятно "
                "занижена\"; остальные маркеры на фото нечитаемы при "
                "имеющемся разрешении (без ложной точности новые имена "
                "не добавлены). Найдено при систематическом разборе "
                "накопленных находок mariupolRIP 2026-07-21.",
    },
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    import psycopg2
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    dedup_key = "civilian_casualty:gondy_40a_churchyard"
    if not args.dry_run:
        source_doc_id = _upsert_source_doc_by_sha(cur, SHA_GRAVE_ALBUM_EMBED)
        _upsert_source_doc_by_sha(cur, SHA_WIDE_SHOT_MSG18005)  # register in source_document too
        cur.execute(
            """INSERT INTO corroboration
                   (property_id, kind, reference, detail, dedup_key,
                    captured_at, source_doc_id, confidence, verdict)
               VALUES (NULL, 'civilian_casualty', %s, %s, %s, now(),
                       %s, %s, 'confirms')
               ON CONFLICT (dedup_key) DO UPDATE SET
                   detail = EXCLUDED.detail,
                   source_doc_id = EXCLUDED.source_doc_id""",
            ("Z2022sw grave album + nmrpl official clearance post "
             "(churchyard site, ~30 graves est., 5 named)",
             json.dumps(DETAIL, ensure_ascii=False), dedup_key,
             source_doc_id, 0.8),
        )
    log.info("%s dedup_key=%s (property_id=NULL, off-spine site; "
              "~30 graves est., 5 named)",
              "[DRY RUN] would load" if args.dry_run else "loaded",
              dedup_key)

    if not args.dry_run:
        con.commit()
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
