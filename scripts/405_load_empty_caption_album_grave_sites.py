#!/usr/bin/env python3
"""Load 13 distinct grave/casualty records surfaced by the 2026-07-21
visual review of all 144 unique photos across the 66 empty-caption
mariupolRIP albums (scripts/399's blind-spot sweep -> scripts/404's
capture -> this review). Every photo was opened and inspected -- no
caption text existed to pre-filter on, so nothing here came from a
keyword match. ~120 of 144 photos were portraits/memorial-template
graphics with no grave or address content and are not loaded (not
itemized here; see session log).

A second pass (same day, user-identified pattern) checked the message
immediately following each loaded album for a text-only narrative post
explaining the same grave -- caption-less albums on this channel are
often followed by a separate post with the names/address spelled out
(e.g. the 5-grave cluster below was precisely located this way: "Мира
42, у памятника Шевченко"). This upgraded 3 records from unaddressed to
address-matched or landmark-precise, and surfaced 2 unrelated NEW leads
sitting immediately next to already-loaded albums (Солнцев, Пухова) --
these two have no grave photo, only a strong textual identification, so
their source sha is a captured text post (scripts/406) rather than an
album photo.

2 more finds from this same review were investigated and closed as OUT
OF SCOPE (not property-linked seizure/burial evidence, so deliberately
NOT loaded and NOT flagged for further follow-up):
  - msg 16213: a numbered grave marker ("214, Сараев Николай Николаевич,
    02.08.1969") whose own UI chrome reads "6892 из 6971" -- initially
    read as a large systematic mass-grave documentation gallery, but
    confirmed (user, 2026-07-21) to just be the poster's total phone
    photo count, not a dedicated cemetery-documentation project. No
    further action.
  - msg 22930: a 2-photo, 95-row numbered table (ПІБ / дата рождения /
    смерти). Its companion post t.me/mariupolRIP/22932 identifies the
    source: "Умершие в период 'апрель - май' в бывшей областной
    больнице интенсивного лечения г. Мариуполь" -- a hospital mortality
    list (deaths at the former regional intensive-care hospital), not
    a property-linked burial site. Out of this project's scope (no
    property/seizure link); not loaded, not pursued further.

3 name-only leads with no address or grave photo at all remain noted
but unloaded: Дишливенко
    Людмила (21.05.1971 - март 2022), Белеванцева Лиана (23.12.1968,
    died with her son under rubble, exact date unknown), and "Ируся,
    Лия, София, Надежда" (4 women, first names only, died 22.03.2022
    together) -- pure obituary/memorial posts, no located grave to
    attach a corroboration row to.

Sites loaded here (all kind='civilian_casualty'):
  1. Демченко family (4 named) -- ул. Энгельса, 73. Killed together by
     shelling 18.03.2022 (marker states this explicitly). No property
     row for house 73 (street coverage on spine gaps between 64 and 39 --
     genuinely off-spine, not a matching failure); property_id NULL.
  2. Галстян Грагик Ашотович, 11.01.1973-22.03.2022 -- courtyard grave by
     a playground (distinctive red slide), matched to an Instagram
     portrait (handle g.galstyaan) in the same 2-photo album. No address
     visible; property_id NULL.
  3. Корпас Марэн Богданович, 08.07.1993-12.03.2022 -- roadside grave,
     unaddressed; property_id NULL.
  4. Татар Рома, 1995-III.2022 -- grave near a pink apartment building,
     unaddressed; property_id NULL.
  5. 5-grave cluster (msg 24395): Расщупкина Мария Ивановна (d.
     31.03.2022), Голодова Инна Ивановна (12.10.1931-03.2022), Пупай
     Николай Андреевич (25.06.1934-06.03.2022), 1 unnamed woman
     (~65-70 y.o.), Боголюбова Тамара Васильевна (21.07.1936-3.04.2022)
     -- unaddressed street scene with damaged buildings; property_id
     NULL.
  6. Вершанская Тамара Ивановна, 12.11.1940-06.03.2022 -- torn marker,
     overgrown site near a damaged building; property_id NULL.
  7. Маринец Раиса Николаевна, 25.11.1952-17.03.2022 -- by a distinctive
     black metal gate fronting a heavily shelled building; property_id
     NULL.
  8. 5-person grave, ул. Ломизова, 1 (property_id 50040, ON SPINE):
     Данилова Анжела (27.12.1964), Звягинцев Владимир (24.02.1953),
     Федюсимова Татьяна (195?, digit obscured), Солдатенко Владимир
     (1957), Меркулов Сергей (23.01.1983). Marker states time of death:
     22.03.2022, 9:20 AM.

PRIVACY: all named individuals are DECEASED, named on public grave
markers photographed and posted to a public Telegram channel -- not the
project's "living private owner" minimization rule.

Per project convention, this writes to the canonical Postgres spine and
is NOT run by Claude -- run it yourself:

    PYTHONPATH=src .venv312/bin/python scripts/405_load_empty_caption_album_grave_sites.py --dry-run
    PYTHONPATH=src .venv312/bin/python scripts/405_load_empty_caption_album_grave_sites.py
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
        "dedup_key": "civilian_casualty:mariupolrip_15678:demchenko_engelsa73",
        "property_id": None,
        "sha": "77e0dd6ccafc1f70616b011ccffc3c0c56d4d07a940a4fd5a1ec7039878222bb",
        "confidence": 0.85,
        "detail": {
            "title": "Захоронение семьи Демченко, ул. Энгельса, 73",
            "location_note": "Табличка: «ПОГИБЛИ В РЕЗУЛЬТАТЕ ОБСТРЕЛА "
                              "18.03.2022г. ДОМА ПО УЛ. ЭНГЕЛЬСА 73». Дом "
                              "73 отсутствует на спине -- проверено "
                              "2026-07-21 по пользовательским скриншотам "
                              "Google Street View/Yandex: дома 71 и 75 "
                              "(частный сектор, нечётная сторона) стоят "
                              "почти вплотную, дома 73 физически нет между "
                              "ними; самодельная могила, вероятно, во "
                              "дворе/переулке за одним из этих домов. "
                              "Оба варианта названия улицы (Энгельса и её "
                              "alias «Архитектора Нильсена») проверены на "
                              "спине -- ни 69, ни 71, ни 73, ни 75, ни 77 "
                              "нигде не встречаются; это, вероятно, "
                              "отражает системный пробел покрытия для "
                              "частных одноэтажных домов (наши источники -- "
                              "реестр бесхозяйного имущества, декреты, "
                              "суды -- касаются почти исключительно "
                              "многоквартирных домов), а не ошибку "
                              "сопоставления одного адреса; property_id "
                              "NULL. Подтверждающий пост-нарратив "
                              "t.me/mariupolRIP/15685 (та же лента, "
                              "следующее сообщение -- систематический "
                              "паттерн, обнаруженный пользователем "
                              "2026-07-21: подписи часто идут отдельным "
                              "постом сразу после альбома без подписи): "
                              "«Ракетный обстрел. Ул Арх Нильсона 73. "
                              "Похоронены мною там же.» -- независимо "
                              "подтверждает адрес и способ гибели "
                              "(ракетный обстрел) от лица человека, "
                              "лично похоронившего погибших.",
            "source_url": "https://t.me/mariupolRIP/15678",
            "source_date": "2022-04-25",
            "deceased": [
                {"name": "Демченко Анна Яковлевна", "dates": "03.01.1938 - 02.04.2022"},
                {"name": "Демченко Ольга Сергеевна", "dates": "12.01.1999 - 18.03.2022"},
                {"name": "Демченко Анна Сергеевна", "dates": "12.01.1999 - 18.03.2022",
                 "note": "Дата рождения совпадает с Ольгой Сергеевной -- вероятно близнецы."},
                {"name": "Демченко Алевтина Анатольевна", "dates": "22.11.1966 - 18.03.2022"},
            ],
            "graves_total": 4,
            "graves_named": 4,
            "photo_context": "Альбом также содержит портретные фото "
                              "(предположительно, погибших) без подписей "
                              "-- не сопоставлены поимённо с конкретными "
                              "фото за отсутствием иных опознавательных "
                              "признаков.",
        },
    },
    {
        "dedup_key": "civilian_casualty:mariupolrip_17770:galstyan_playground",
        "property_id": 4393,  # бульвар Шевченко, 64а
        "sha": "8c2a56577acc1e5f3221a48c48644ba05f8ac9fa4019d370572d450b2708ae32",
        "confidence": 0.85,
        "detail": {
            "title": "Захоронение у детской площадки, бульвар Шевченко, 64а",
            "location_note": "Могила рядом с приметной детской площадкой "
                              "(красная горка), повреждённое многоэтажное "
                              "здание на заднем плане. Адрес подтверждён "
                              "пост-нарративом t.me/mariupolRIP/17772 "
                              "(следующее сообщение после альбома без "
                              "подписи): «Мой зять (муж дочери) Бульвар "
                              "Шевченко 64а. погиб 22 марта. Галстян Грач "
                              "Ашотович» -- от лица родственника "
                              "(тёщи/тестя). Имя-отчество на кресте "
                              "читается как «Грагик»; родственник пишет "
                              "«Грач» -- вероятно ласкательная форма или "
                              "неточность транскрипции, не отдельное лицо. "
                              "property_id 4393 (бульвар Шевченко, 64а) "
                              "сопоставлен на спине.",
            "source_url": "https://t.me/mariupolRIP/17770",
            "source_date": "2022-05-01",
            "deceased": [{"name": "Галстян Грагик Ашотович",
                          "name_note": "Родственник пишет «Грач Ашотович».",
                          "dates": "11.01.1973 - 22.03.2022"}],
            "graves_total": 1,
            "graves_named": 1,
        },
    },
    {
        "dedup_key": "civilian_casualty:mariupolrip_18681:korpas_roadside",
        "property_id": None,
        "sha": "8200af1495fb4637237587c3c56648cae78406ad210d54905564367a01094fe8",
        "confidence": 0.7,
        "detail": {
            "title": "Придорожное захоронение",
            "location_note": "Придорожная могила у улицы с повреждёнными "
                              "зданиями; конкретный адрес не установлен.",
            "source_url": "https://t.me/mariupolRIP/18681",
            "source_date": "2022-05-04",
            "deceased": [{"name": "Корпас Марэн Богданович",
                          "name_note": "Написание фамилии по табличке "
                                       "неоднозначно (Корпас/Карпас).",
                          "dates": "08.07.1993 - 12.03.2022"}],
            "graves_total": 1,
            "graves_named": 1,
        },
    },
    {
        "dedup_key": "civilian_casualty:mariupolrip_20088_tatar_pink_building",
        "property_id": None,
        "sha": "a5bf89cdd04f03b61aad0160aae2e011694e27e8a1fe837a56f95cc7a7606efd",
        "confidence": 0.7,
        "detail": {
            "title": "Захоронение у розового жилого дома",
            "location_note": "Могила на газоне у розового/лососевого "
                              "многоэтажного дома; конкретный адрес не "
                              "установлен. Личность подтверждена по "
                              "Instagram-портрету того же альбома "
                              "(handle romchiktarane).",
            "source_url": "https://t.me/mariupolRIP/20088",
            "source_date": "2022-05-10",
            "deceased": [{"name": "Татар Рома",
                          "name_note": "Полное отчество/фамилия не "
                                       "уточнены по табличке.",
                          "dates": "1995 - III.2022"}],
            "graves_total": 1,
            "graves_named": 1,
        },
    },
    {
        "dedup_key": "civilian_casualty:mariupolrip_24395:street_cluster5",
        "property_id": None,
        "sha": "4f1dd5496bbc4916738df31a07817839a9437bfb204b48ca33e3fa64dea26963",
        "confidence": 0.85,
        "detail": {
            "title": "Групповое захоронение (5 могил), ул. Мира 42, у "
                      "памятника Шевченко (район драмтеатра)",
            "location_note": "Precisely located by the post-narrative "
                              "t.me/mariupolRIP/24401 (next message after "
                              "the caption-less album -- user-identified "
                              "recurring pattern, 2026-07-21): «Мира 42, "
                              "возле памятника Шевченко с правой стороны "
                              "под тополем (центр города район "
                              "драмтеатра) похоронено 5 человек». This is "
                              "a public square/monument, not a residential "
                              "courtyard -- no property row exists for it "
                              "(the spine models buildings, not public "
                              "landmarks), so property_id stays NULL "
                              "despite the address now being exact. "
                              "24401 also corrects 2 names slightly: "
                              "«Голоядова» (not Голодова) Инна Ивановна, "
                              "«Пупий» (not Пупай) Николай Андреевич.",
            "source_url": "https://t.me/mariupolRIP/24395",
            "source_date": "2022-06-14",
            "deceased": [
                {"name": "Расщупкина Мария Ивановна", "dates": "? - 31.03.2022",
                 "note": "Дата рождения обрезана на фото."},
                {"name": "Голоядова Инна Ивановна",
                 "name_note": "На кресте читалось «Голодова» -- "
                               "исправлено по t.me/mariupolRIP/24401.",
                 "dates": "12.10.1931 - 03.2022"},
                {"name": "Пупий Николай Андреевич",
                 "name_note": "На кресте читалось «Пупай» -- исправлено "
                               "по t.me/mariupolRIP/24401.",
                 "dates": "25.06.1934 - 06.03.2022"},
                {"name": None, "note": "Табличка: «Женщина, 65-70 лет» -- без имени."},
                {"name": "Боголюбова Тамара Васильевна", "dates": "21.07.1936 - 3.04.2022"},
            ],
            "graves_total": 5,
            "graves_named": 4,
        },
    },
    {
        "dedup_key": "civilian_casualty:mariupolrip_29517:vershanskaya",
        "property_id": None,
        "sha": "cad98f35d177e3cffd845184c96b0b52b1a7a416d83ef6331722dee0f829406d",
        "confidence": 0.65,
        "detail": {
            "title": "Захоронение (заброшенное, табличка разорвана)",
            "location_note": "Заросший участок у повреждённого здания; "
                              "конкретный адрес не установлен. Табличка "
                              "надорвана и частично закрыта растительностью.",
            "source_url": "https://t.me/mariupolRIP/29517",
            "source_date": "2022-08-30",
            "deceased": [{"name": "Вершанская Тамара Ивановна",
                          "dates": "12.11.1940 - 06.03.2022"}],
            "graves_total": 1,
            "graves_named": 1,
        },
    },
    {
        "dedup_key": "civilian_casualty:mariupolrip_33107:marinets_blackgate",
        "property_id": None,
        "sha": "2eddb8426b1835df49f0fd8f6a7327a52171dc3267d50fe9cbd145779341dbbc",
        "confidence": 0.8,
        "detail": {
            "title": "Захоронение у чёрных металлических ворот, у "
                      "левобережного РОВД",
            "location_note": "Могила у приметных чёрных металлических "
                              "ворот, ведущих к тяжело разрушенному зданию "
                              "(каменная кладка полностью выбита). "
                              "Landmark confirmed by the post immediately "
                              "BEFORE the photo album (t.me/mariupolRIP/"
                              "33106 -- narrative posts on this channel "
                              "can precede as well as follow the "
                              "caption-less photos): «Маринец Раиса "
                              "Николаевна, 25.11.1952 - 17.03.2022. "
                              "Могила на сегодняшний день возле "
                              "левобережного РОВД.» РОВД (районный отдел "
                              "внутренних дел) -- институциональное "
                              "здание, отсутствует на спине (как и "
                              "церковь на ул. Гонды); property_id NULL.",
            "source_url": "https://t.me/mariupolRIP/33107",
            "source_date": "2022-11-08",
            "deceased": [{"name": "Маринец Раиса Николаевна",
                          "dates": "25.11.1952 - 17.03.2022"}],
            "graves_total": 1,
            "graves_named": 1,
        },
    },
    {
        "dedup_key": "civilian_casualty:mariupolrip_56249:lomizova1_group5",
        "property_id": 50040,  # ул. Ломизова, 1
        "sha": "de52ff3c18e45b2411036eb5ceee854558d43dc8ef38c7df7623281f7af19390",
        "confidence": 0.85,
        "detail": {
            "title": "Групповое захоронение (5 человек), ул. Ломизова, 1",
            "location_note": "Табличка прямо указывает адрес: «Мариуполь. "
                              "Ломизова 1». Объект сопоставлен на спине "
                              "(property_id 50040). Полное отчество "
                              "Даниловой подтверждено пост-нарративом "
                              "t.me/mariupolRIP/56251 (4-летие годовщины): "
                              "«Данилова Анжела Васильевна 27.12.1964 - "
                              "22.03.2022».",
            "source_url": "https://t.me/mariupolRIP/56249",
            "source_date": "2026-03-22",
            "time_of_death": "22.03.2022, 9:20 утра (указано на табличке)",
            "deceased": [
                {"name": "Данилова Анжела Васильевна",
                 "name_note": "Отчество подтверждено по t.me/mariupolRIP/56251.",
                 "dates": "27.12.1964 - 22.03.2022"},
                {"name": "Звягинцев Владимир", "dates": "24.02.1953 - 22.03.2022"},
                {"name": "Федюсимова Татьяна",
                 "name_note": "Год рождения частично неразборчив (195?).",
                 "dates": "195? - 22.03.2022"},
                {"name": "Солдатенко Владимир", "dates": "1957 - 22.03.2022"},
                {"name": "Меркулов Сергей", "dates": "23.01.1983 - 22.03.2022"},
            ],
            "graves_total": 5,
            "graves_named": 5,
        },
    },
    {
        # Not from a caption-less album -- found immediately after the
        # Корпас album (msg 18681-18682) while checking that album's own
        # post-narrative follow-up for the pattern the user flagged
        # 2026-07-21. A distinct, unrelated individual whose own post
        # happens to name a precise address.
        "dedup_key": "civilian_casualty:mariupolrip_18683:solntsev_morskoy20a",
        "property_id": None,
        "sha": "cb8399a32cba0b159f562a56b0c3a80bc118168869a78f8a568c1184cc6bda1b",
        "confidence": 0.7,
        "detail": {
            "title": "Солнцев Алексей Леонидович -- Бульвар Морской, 20а",
            "location_note": "Текстовый пост (без фото могилы): «Друг "
                              "семьи и ЧЕЛОВЕК по-жизни....не описать "
                              "словами боль утраты. Солнцев Алексей "
                              "Леонидович 06.12.1977, погиб в конце марта "
                              "Б-р Морской, 20а...Закрыл собою ребенка во "
                              "время авиаудара». Дом «20а» отсутствует на "
                              "спине (сопоставлены только 8, 9, 14, 42, "
                              "44а, 46а, 52а) -- проверено 2026-07-21; "
                              "property_id NULL. Нет фотографии "
                              "захоронения -- только текстовое "
                              "свидетельство о месте и обстоятельствах "
                              "гибели (закрыл собой ребёнка при авиаударе).",
            "source_url": "https://t.me/mariupolRIP/18683",
            "source_date": "2022-05-04",
            "deceased": [{"name": "Солнцев Алексей Леонидович",
                          "dates": "06.12.1977 - конец марта 2022",
                          "circumstance": "Погиб, закрыв собой ребёнка во "
                                           "время авиаудара (по "
                                           "свидетельству друга семьи)."}],
            "graves_total": 0,
            "graves_named": 1,
            "note": "Загружено как civilian_casualty без фотографии "
                    "захоронения -- достаточно сильное текстовое "
                    "свидетельство (имя, дата, адрес, обстоятельства от "
                    "друга семьи).",
        },
    },
    {
        # Found immediately after the Маринец album (msg 33107-33108)
        # while checking for the same post-narrative pattern.
        "dedup_key": "civilian_casualty:mariupolrip_33110:pukhova_pobedy75",
        "property_id": 5335,  # проспект Победы, 75
        "sha": "19045070409394093238f56c413525865ca60ccca2146c26527a2c3b658c9880",
        "confidence": 0.75,
        "detail": {
            "title": "Пухова Нина Александровна -- проспект Победы, 75, кв.53",
            "location_note": "Текстовый пост (без фото могилы): «Пухова "
                              "Нина Александррвна, погибла 18.03.2022 от "
                              "прямого попадания в свою комнату. "
                              "Проживала проспект Победы, дом 75, к. 53.» "
                              "Адрес сопоставлен объекту на спине "
                              "(property_id 5335). Погибла в своей "
                              "квартире от прямого попадания -- это "
                              "адрес смерти, а не обязательно места "
                              "захоронения (место погребения в посте не "
                              "указано).",
            "source_url": "https://t.me/mariupolRIP/33110",
            "source_date": "2022-11-08",
            "deceased": [{"name": "Пухова Нина Александровна",
                          "name_note": "В посте опечатка «Александррвна».",
                          "dates": "? - 18.03.2022",
                          "circumstance": "Прямое попадание в квартиру "
                                           "(проспект Победы, 75, кв.53)."}],
            "graves_total": 0,
            "graves_named": 1,
            "note": "Загружено как civilian_casualty без фотографии "
                    "захоронения -- адрес относится к месту гибели "
                    "(квартира), не подтверждённому месту погребения.",
        },
    },
    {
        # Found immediately after the Татар Рома album (msg 20088-20089)
        # while re-checking that album for a narrative follow-up.
        "dedup_key": "civilian_casualty:mariupolrip_20086:bukhtoyarova_meotidy4",
        "property_id": 10703,  # б-р 50 лет Октября, 4 (dual-named "Меотиды" on user's map)
        "sha": "f75e1e0c351b778d059c52ca464dd421e5713d4b47baa3c8ad8ff23686984976",
        "confidence": 0.85,
        "detail": {
            "title": "Бухтоярова Ольга Яковлевна -- бул. 50 лет Октября "
                      "(Меотиды), 4",
            "location_note": "Текстовый пост (без фото могилы): "
                              "«Бухтоярова Ольга Яковлевна 06.08.1939. "
                              "Погибла 20 марта 2022, дом начал гореть в "
                              "6 утра, сгорела заживо в подвале, бульвар "
                              "Меотиды 4, во втором подъезде.» «Меотиды 4» "
                              "не найден под именем STREET/BOULEVARD "
                              "«меотид*» на спине -- но пользователь "
                              "предоставил кадастровую карту (2026-07-21) "
                              "показывающую, что \"бульв. Меотиди\" на "
                              "этом отрезке -- альтернативное название "
                              "\"бульв. 50 лет Октября\" (тот же дом "
                              "\"4\", подтверждено существующим alias-"
                              "объектом id 10704 «Б-Р 50ЛЕТ ОКТЯБРЯ "
                              "(МЕОТИДЫ), 40/41»). property_id 10703 "
                              "(б-р 50 лет Октября, 4). Дом находится на "
                              "краю квартала (Азовстальська-Меотиди/50 "
                              "лет Октября-Морський/Комсомольський-"
                              "Ломізова), полностью снесённого по "
                              "Распоряжению ГКО ДНР №54 от 29.09.2022 "
                              "(многоквартирные дома этого квартала, "
                              "включая ул. Ломизова 3-19 и б-р 50 лет "
                              "Октября 4/6/8/10, все с demolition "
                              "stage=2022-09-29 в seizure_event) -- тот "
                              "же квартал, где уже загружено захоронение "
                              "5 человек по ул. Ломизова 1 "
                              "(lomizova1_group5, выше). Найдены 2 "
                              "земельных отвода на той же улице (№365 "
                              "16.10.2025, «Синее море», 44А; №395 "
                              "06.11.2025, «Эводом-5»/ЖК «Чувства.Азарт», "
                              "уч. 40а) -- НЕ подтверждено, что это тот "
                              "же физический квартал (номера домов 40-44 "
                              "далеко от дома 4 на длинном бульваре, "
                              "координаты дома 44а не геокодированы) -- "
                              "требует отдельной геопроверки, не "
                              "утверждается как связь.",
            "source_url": "https://t.me/mariupolRIP/20086",
            "source_date": "2022-05-10",
            "deceased": [{"name": "Бухтоярова Ольга Яковлевна",
                          "dates": "06.08.1939 - 20.03.2022",
                          "circumstance": "Дом начал гореть в 6 утра, "
                                           "сгорела заживо в подвале "
                                           "(бульвар Меотиды 4, 2-й "
                                           "подъезд)."}],
            "graves_total": 0,
            "graves_named": 1,
            "note": "Загружено как civilian_casualty без фотографии "
                    "захоронения -- сильное текстовое свидетельство "
                    "(адрес, обстоятельства гибели).",
        },
    },
    {
        # Found 2 messages before the Корпас album (msg 18681-18682)
        # while re-checking that album for a narrative lead-in.
        "dedup_key": "civilian_casualty:mariupolrip_18679:rudakov_novoselovka",
        "property_id": None,
        "sha": "b8f98ec0e6fd585a682ff88e12a390361184c55f217ef790617798cdfa0e2d49",
        "confidence": 0.65,
        "detail": {
            "title": "Рудаков Николай -- старое кладбище Новоселовки "
                      "(воронка от снаряда)",
            "location_note": "Текстовый пост (без фото могилы): "
                              "«Рудаков Николай погиб 15 марта, от "
                              "осколочного ранения в голову. Год рождения "
                              "20 сентября 1966. Похоронен в воронке от "
                              "снаряда на старом кладбище Новоселовки.» "
                              "Formal/old cemetery within the Новосёловка "
                              "district, not a residential courtyard -- "
                              "no specific street address; property_id "
                              "NULL.",
            "source_url": "https://t.me/mariupolRIP/18679",
            "source_date": "2022-05-04",
            "deceased": [{"name": "Рудаков Николай",
                          "name_note": "Отчество/фамилия не уточнены в посте.",
                          "dates": "20.09.1966 - 15.03.2022",
                          "circumstance": "Осколочное ранение в голову; "
                                           "похоронен в воронке от снаряда."}],
            "graves_total": 0,
            "graves_named": 1,
            "note": "Загружено как civilian_casualty без фотографии "
                    "захоронения -- сильное текстовое свидетельство.",
        },
    },
    {
        # Found immediately before the Дядечко post (msg 21709) while
        # re-checking that lead for a narrative context.
        "dedup_key": "civilian_casualty:mariupolrip_21705:zimenko_moskovskaya15",
        "property_id": None,
        "sha": "0da8786e2df41f2b5a6f39e4ed7aa299606bcf16b1e99c873d9b60dc44a71e5e",
        "confidence": 0.7,
        "detail": {
            "title": "Зименко Николай и Зименко Нина Андреевна -- "
                      "ул. Московская, 15, кв.20",
            "location_note": "Текстовый пост (без фото могилы): «28 марта "
                              "в результате прямого попадания во двор, "
                              "были ранены, а затем от ран скончались "
                              "Зименко Николай 20.12.1961 и его мама "
                              "Зименко Нина Андреевна 19.12.1938, "
                              "проживающие раньше по Московской 15, "
                              "кв.20.» Дом «15» отсутствует на спине "
                              "(нумерация разрывается между 7 и 16) -- "
                              "проверено 2026-07-21; property_id NULL. "
                              "«Проживали раньше» -- адрес относится к "
                              "месту проживания/ранения, не обязательно "
                              "к месту погребения (место захоронения в "
                              "посте не указано).",
            "source_url": "https://t.me/mariupolRIP/21705",
            "source_date": "2022-05-20",
            "deceased": [
                {"name": "Зименко Николай", "dates": "20.12.1961 - 28.03.2022(?)",
                 "circumstance": "Ранен прямым попаданием во двор "
                                  "28.03.2022, скончался от ран."},
                {"name": "Зименко Нина Андреевна", "dates": "19.12.1938 - 28.03.2022(?)",
                 "circumstance": "Мать Николая Зименко, ранена тем же "
                                  "попаданием, скончалась от ран."},
            ],
            "graves_total": 0,
            "graves_named": 2,
            "note": "Загружено как civilian_casualty без фотографии "
                    "захоронения -- сильное текстовое свидетельство "
                    "(имена, даты, адрес, обстоятельства).",
        },
    },
]

CLOSED_OUT_OF_SCOPE = [
    ("https://t.me/mariupolRIP/16213",
     "Numbered grave marker (\"214, Сараев Николай Николаевич, "
     "02.08.1969\"); \"6892 из 6971\" in the screenshot chrome initially "
     "read as a systematic mass-grave documentation gallery, but "
     "confirmed (user, 2026-07-21) to just be the poster's total phone "
     "photo count. Not a project lead -- closed, no further action."),
    ("https://t.me/mariupolRIP/22930",
     "2-photo, 95-row numbered mortality table. Companion post "
     "t.me/mariupolRIP/22932 identifies it as a list of deaths at the "
     "former regional intensive-care hospital ('бывшая областная "
     "больница интенсивного лечения'), April-May -- a hospital "
     "mortality list, not a property-linked burial site. Out of this "
     "project's scope; closed, no further action."),
]

NAME_ONLY_NO_SITE = [
    ("https://t.me/mariupolRIP/55697",
     "Дишливенко Людмила, 21.05.1971 - март 2022 -- no grave photo or address."),
    ("https://t.me/mariupolRIP/56198",
     "Белеванцева Лиана, 23.12.1968, died with her son under building "
     "rubble March 2022 (exact date unknown) -- no grave photo or address."),
    ("https://t.me/mariupolRIP/56298",
     "\"Ируся, Лия, София, Надежда\" -- 4 women, first names only, died "
     "together 22.03.2022 -- no surname or address recoverable."),
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
                 f"mariupolRIP empty-caption album review -- {site['detail']['title']}",
                 json.dumps(site["detail"], ensure_ascii=False),
                 site["dedup_key"], source_doc_id, site["confidence"]),
            )
        log.info("%s dedup_key=%s (property_id=%s, %d graves, %d named)",
                  "[DRY RUN] would load" if args.dry_run else "loaded",
                  site["dedup_key"], site["property_id"],
                  site["detail"]["graves_total"], site["detail"]["graves_named"])

    log.info("=== %d leads investigated and closed as out of scope ===",
              len(CLOSED_OUT_OF_SCOPE))
    for url, why in CLOSED_OUT_OF_SCOPE:
        log.info("  %s -- %s", url, why)
    log.info("=== %d name-only leads with no locatable site, NOT loaded ===",
              len(NAME_ONLY_NO_SITE))
    for url, why in NAME_ONLY_NO_SITE:
        log.info("  %s -- %s", url, why)

    if not args.dry_run:
        con.commit()
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
