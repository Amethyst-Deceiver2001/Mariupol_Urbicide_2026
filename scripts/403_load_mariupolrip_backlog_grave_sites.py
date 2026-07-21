#!/usr/bin/env python3
"""Load 5 distinct grave-site records surfaced by the 2026-07-21 systematic
review of the mariupolRIP "explicit_grave_ref" media backlog
(scripts/311_review_mariupolrip_grave_media.py, score +5 tier). Every
candidate image in that tier was opened and visually inspected (not
trusted from text/keyword match alone -- see
memory/lifecycle_classifier_unreliable_siege_damage.md): several turned
out to be portrait photos of the deceased with no located grave, or
individuals already properly reburied at the formal Старокрымское
кладбище, and are deliberately NOT loaded here as grave-site records.

Sites loaded (all kind='civilian_casualty', one row each):
  1. Дядечко Ж.И. -- "могила возле греческого центра" (near the Greek
     center). No property match attempted; landmark-only location,
     property_id NULL.
  2. Супруненко Екатерина Анатольевна + 1 unnamed grave -- "напротив пр.
     Металлургов 83, рядом с забором школы" (opposite Металлургов 83,
     by the school fence). property_id 4544 (проспект Металлургов, 83)
     already on spine; attached there since the marker explicitly says
     "opposite" that building, closest available anchor.
  3. 7-name site near Гимназия №1, ул. Воинов-Освободителей, Левобережный
     район: Хаченкова Марина Валерьевна, Хижнякова Лидия Яковлевна,
     Гайдалим Галина Павловна, Кострыкина Лидия Фёдоровна, Проволоцкая
     Вера Васильевна, Проволоцкий Анатолий Леонидович, Рыжова Галина
     Алексеевна. Only 1 of 7 markers photographed (Хаченкова) -- property
     unspecified beyond "near Гимназия №1"; property_id NULL rather than
     guess a specific building on a street with 20+ candidates (no false
     precision -- address_normalization_pitfalls.md).
  4. Катыхин В.И. -- roadside grave on пр. Строителей opposite "Автоимперия"
     (a car dealership, not itself on the property spine). property_id
     NULL, landmark-only.
  5. Unnamed grave -- opposite "магазин Мариуполь", левый берег, near the
     stadium. No name recoverable from the marker (blank board); loaded
     anyway since the location + photo are independently evidentiary
     (a real grave existed there), consistent with how unnamed graves are
     already carried inside the Грушевского/Гонды multi-grave records.

Source images already reside in data/raw/ (pulled by
scripts/310_pull_mariupolrip_flagged_media.py); this loader registers
each into Postgres source_document via _upsert_source_doc_by_sha() from
the existing SQLite forensic log, same pattern as every other loader in
this project -- no new capture step needed.

PRIVACY: all named individuals are DECEASED, named on public grave
markers photographed and posted to a public Telegram channel -- not the
project's "living private owner" minimization rule.

Per project convention, this writes to the canonical Postgres spine and
is NOT run by Claude -- run it yourself:

    PYTHONPATH=src .venv312/bin/python scripts/403_load_mariupolrip_backlog_grave_sites.py --dry-run
    PYTHONPATH=src .venv312/bin/python scripts/403_load_mariupolrip_backlog_grave_sites.py
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

SITES = [
    {
        "dedup_key": "civilian_casualty:mariupolrip_21709:dyadechko_greek_center",
        "property_id": None,
        "sha": "8cc69d58ad549ad67cbe5f5f72e52286afc86471213696204f3cc25ac66b7bfd",
        "confidence": 0.75,
        "detail": {
            "title": "Могила у греческого центра",
            "location_note": "«Могила возле греческого центра» -- ориентир "
                              "не сопоставлен с конкретным объектом на "
                              "спине; координаты не установлены.",
            "source_url": "https://t.me/mariupolRIP/21709",
            "source_date": "2022-05-20",
            "deceased": [{"name": "Дядечко Ж.И.", "dates": "03.10.1938 - 01.04.2022"}],
            "graves_total": 1,
            "graves_named": 1,
        },
    },
    {
        "dedup_key": "civilian_casualty:mariupolrip_22738:suprunenko_metallurgov83",
        "property_id": 4544,  # проспект Металлургов, 83
        "sha": "1f2b0246adb5b06e2ac1a831c215e4d7cb08221b61d1ec73af8668e8317f121e",
        "confidence": 0.8,
        "detail": {
            "title": "Захоронение напротив пр. Металлургов 83",
            "location_note": "«Напротив пр Металлургов 83, рядом с забором "
                              "школы» -- привязано к property_id 4544 как "
                              "ближайшему ориентиру на спине; фактическое "
                              "место могилы находится через дорогу от "
                              "здания, не во дворе.",
            "source_url": "https://t.me/mariupolRIP/22738",
            "source_date": "2022-05-30",
            "deceased": [{"name": "Супруненко Екатерина Анатольевна",
                          "dates": "04.12.1985 - 19.03.2022"}],
            "unnamed_graves": [{"note": "безымянная могила рядом, "
                                         "упомянута в тексте поста"}],
            "graves_total": 2,
            "graves_named": 1,
        },
    },
    {
        "dedup_key": "civilian_casualty:mariupolrip_23965:gimnaziya1_voinov_osvoboditeley",
        "property_id": None,
        "sha": "b50390674b859c4a8186dfe91af486e1ca0f4000ebfb89175ea0e6b625a5a99e",
        "confidence": 0.7,
        "detail": {
            "title": "Могилы возле Гимназии №1, ул. Воинов-Освободителей "
                      "(Левобережный район)",
            "location_note": "«Могилы возле первой гимназии. Улица "
                              "воинов освободителей. Левый [берег].» -- "
                              "улица Воинов-Освободителей несёт 20+ "
                              "объектов на спине; конкретное здание не "
                              "указано в посте, property_id намеренно "
                              "оставлен NULL, а не угадан (см. "
                              "address_normalization_pitfalls.md).",
            "source_url": "https://t.me/mariupolRIP/23965",
            "source_date": "2022-06-09",
            "deceased": [
                {"name": "Хаченкова Марина Валерьевна",
                 "dates": "19.01.1969 - 12.03.2022",
                 "marker_note": "Табличка на кресте: «Я мама, очень прошу "
                                 "сообщить куда перезахоронили мою дочь. "
                                 "[Мкр...], бульвар 58» -- материнская "
                                 "просьба; адрес на табличке -- контактный "
                                 "адрес матери, не место могилы. Единственный "
                                 "из 7 маркеров, сфотографированный крупным "
                                 "планом.",
                 "photo": True},
                {"name": "Хижнякова Лидия Яковлевна", "photo": False},
                {"name": "Гайдалим Галина Павловна", "photo": False},
                {"name": "Кострыкина Лидия Фёдоровна", "photo": False},
                {"name": "Проволоцкая Вера Васильевна", "photo": False},
                {"name": "Проволоцкий Анатолий Леонидович", "photo": False},
                {"name": "Рыжова Галина Алексеевна", "photo": False},
            ],
            "graves_total": 7,
            "graves_named": 7,
            "note": "6 из 7 имён известны только по тексту поста -- "
                    "отдельные маркеры не сфотографированы/не приложены.",
        },
    },
    {
        "dedup_key": "civilian_casualty:mariupolrip_28308:katykhin_stroiteley_avtoimperiya",
        "property_id": None,
        "sha": "bc0b1d6a169663ec7f886af3a22da4f69efd5e0155d7944d08461ba7e3146af6",
        "confidence": 0.75,
        "detail": {
            "title": "Придорожное захоронение, пр. Строителей "
                      "(напротив «Автоимперии»)",
            "location_note": "«Катыхин В.И., 1930-2022г., захоронен возле "
                              "дороги по пр.Строителей, напротив "
                              "Автоимперии.» -- «Автоимперия» (автосалон) "
                              "не является объектом на спине; property_id "
                              "оставлен NULL.",
            "source_url": "https://t.me/mariupolRIP/28308",
            "source_date": "2022-08-11",
            "deceased": [{"name": "Катыхин В.И.", "dates": "1930 - 2022"}],
            "graves_total": 1,
            "graves_named": 1,
        },
    },
    {
        "dedup_key": "civilian_casualty:mariupolrip_44999:unnamed_levoberezhny_stadium",
        "property_id": None,
        "sha": "58e8dd51ac615431176f14625cb3d5fbd42bc35a0da1e537b0c28204d16c2fca",
        "confidence": 0.55,
        "detail": {
            "title": "Безымянная могила, левый берег (у стадиона)",
            "location_note": "«Находится напротив магазина Мариуполь. "
                              "(левый берег, стадион)» -- ни магазин, ни "
                              "стадион не идентифицированы как конкретный "
                              "объект на спине; property_id NULL.",
            "source_url": "https://t.me/mariupolRIP/44999",
            "source_date": "2024-04-16",
            "deceased": [{"name": None, "note": "Табличка на месте не "
                                                  "читается/пуста на фото; "
                                                  "автор поста прямо "
                                                  "просит помощи в "
                                                  "идентификации."}],
            "graves_total": 1,
            "graves_named": 0,
        },
    },
]

NOT_LOADED_FALSE_POSITIVES = [
    ("https://t.me/mariupolRIP/14132", "Чаплыгина А.В. / Чаплыгин Н.К. -- "
     "портрет пары, могила прямо названа неизвестной в тексте поста "
     "(«Прах мамы под завалами, могила папы неизвестно где»)."),
    ("https://t.me/mariupolRIP/23319", "Гомзякова Ю. + сын + отец -- "
     "портрет, семья прямо сообщает, что не может найти могилу."),
    ("https://t.me/mariupolRIP/28544", "Баскаков И.О. -- портрет, "
     "перезахоронен на Старокрымском кладбище (формальное кладбище, "
     "не дворовое/стихийное захоронение)."),
    ("https://t.me/mariupolRIP/30027", "Нарожная Н.А. -- портрет, "
     "перезахоронена на Старокрымском кладбище."),
    ("https://t.me/mariupolRIP/44432", "Нарожная Н.А. (повторный пост) -- "
     "то же самое, портретный коллаж."),
    ("https://t.me/mariupolRIP/55197", "Хаджава С.В. -- портрет, дата "
     "смерти 02.02.2025 (не связана напрямую с периодом боевых действий "
     "2022 г.); текст поста упоминает гибель сына/невестки/внучки во "
     "время боевых действий -- отдельный, ещё не задокументированный "
     "лид, не входящий в объём этого загрузчика."),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    import psycopg2
    con = psycopg2.connect(config.DATABASE_URL)
    cur = con.cursor()

    for site in SITES:
        if not args.dry_run:
            source_doc_id = _upsert_source_doc_by_sha(cur, site["sha"])
            cur.execute(
                """INSERT INTO corroboration
                       (property_id, kind, reference, detail, dedup_key,
                        captured_at, source_doc_id, confidence, verdict)
                   VALUES (%s, 'civilian_casualty', %s, %s, %s, now(),
                           %s, %s, 'confirms')
                   ON CONFLICT (dedup_key) DO UPDATE SET
                       detail = EXCLUDED.detail,
                       source_doc_id = EXCLUDED.source_doc_id""",
                (site["property_id"],
                 f"mariupolRIP backlog review -- {site['detail']['title']}",
                 json.dumps(site["detail"], ensure_ascii=False),
                 site["dedup_key"], source_doc_id, site["confidence"]),
            )
        log.info("%s dedup_key=%s (property_id=%s, %d graves, %d named)",
                  "[DRY RUN] would load" if args.dry_run else "loaded",
                  site["dedup_key"], site["property_id"],
                  site["detail"]["graves_total"], site["detail"]["graves_named"])

    log.info("=== %d false positives reviewed and deliberately NOT loaded ===",
              len(NOT_LOADED_FALSE_POSITIVES))
    for url, why in NOT_LOADED_FALSE_POSITIVES:
        log.info("  %s -- %s", url, why)

    if not args.dry_run:
        con.commit()
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
