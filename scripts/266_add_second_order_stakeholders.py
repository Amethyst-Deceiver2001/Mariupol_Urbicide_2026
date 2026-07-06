#!/usr/bin/env python3
"""Append the ~19 officials/entities surfaced by the second-order Telegram
sweep (`scripts/262`/`263`) and the document-content survey (`scripts/264`)
to the stakeholder graph — they're currently only in `docs/stakeholder_network.md`
prose, not in `data/parsed/stakeholder_{nodes,edges}.jsonl`, so they're
invisible to the compiled `stakeholder-network.jsx`/`.html` exhibit.

Unlike scripts/40's main build (which derives nodes/edges from loaded decree
tables), these officials come from Telegram posts and resident testimony —
there's no structured DB table to re-derive them from. This is a lean,
idempotent, hand-authored append: safe to re-run (skips node_ids already
present), matching the exact schema scripts/40 produces.

After running this, regenerate the compiled exhibit:
    .venv312/bin/python scripts/266_add_second_order_stakeholders.py
    .venv312/bin/python scripts/189_rebuild_stakeholder_jsx.py
    (then the esbuild pass scripts/189 prints instructions for)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

NODES_PATH = ROOT / "data" / "parsed" / "stakeholder_nodes.jsonl"
EDGES_PATH = ROOT / "data" / "parsed" / "stakeholder_edges.jsonl"

NEW_NODES = [
    {"node_id": "person:переверзева-т", "kind": "person", "canonical_name": "Переверзева Т.",
     "tier": "dnr", "roles": ["vice_premier"], "name_variants": ["Татьяна Переверзева"],
     "org": "Правительство ДНР (имущественные и земельные отношения)",
     "evidence": ["telegram:prav_dnr/42699 (TASS statement, 2026-05-01)"]},
    {"node_id": "person:бердников-д", "kind": "person", "canonical_name": "Бердников Д.",
     "tier": "dnr", "roles": ["first_vice_premier"], "name_variants": ["Дмитрий Бердников"],
     "org": "Правительство ДНР", "evidence": ["telegram second-order sweep 2026-07-06"]},
    {"node_id": "person:дубовка-в", "kind": "person", "canonical_name": "Дубовка В.",
     "tier": "dnr", "roles": ["minister"], "name_variants": ["Владимир Дубовка"],
     "org": "Минстрой ДНР", "evidence": ["telegram:minstroydnr (КРТ resettlement announcement)"]},
    {"node_id": "person:циганов-н", "kind": "person", "canonical_name": "Циганов Н.",
     "tier": "dnr", "roles": ["former_minister"], "name_variants": ["Николай Циганов"],
     "org": "Минстрой ДНР (prior)", "evidence": ["Постановление №61-1 compensation framework"]},
    {"node_id": "person:ярошевский-в", "kind": "person", "canonical_name": "Ярошевский В.",
     "tier": "dnr", "roles": ["acting_minister"], "name_variants": ["Владимир Ярошевский", "врио"],
     "org": "Минстрой ДНР (prior, врио)", "evidence": ["ГКО №27 unfinished-construction regime"]},
    {"node_id": "person:иванов-с", "kind": "person", "canonical_name": "Иванов С.",
     "tier": "dnr", "roles": ["deputy_minister"], "name_variants": ["Сергей Иванов"],
     "org": "Минстрой ДНР", "evidence": ["Указ №566 / 879-MKD аварийность program"]},
    {"node_id": "person:авдиенко-а", "kind": "person", "canonical_name": "Авдиенко А.",
     "tier": "dnr", "roles": ["signing_official"], "name_variants": ["Александр Авдиенко"],
     "org": "Минстрой ДНР (управление градостроительства и архитектуры)",
     "evidence": ["telegram:minstroydnr/3932,3933,3934 (Mariupol КРТ/ППТ demolition plans)"]},
    {"node_id": "person:сироватко-ю", "kind": "person", "canonical_name": "Сироватко Ю.",
     "tier": "dnr", "roles": ["head_of_agency"], "name_variants": ["Юрий Сироватко"],
     "org": "Управление Росреестра по ДНР",
     "evidence": ["telegram:rosreestr80 (ЕГРН-without-owner mechanism, ККР)",
                  "telegram:mrpl_besxozxata/10742 (addressee of resident complaint)"]},
    {"node_id": "person:вишневский-в", "kind": "person", "canonical_name": "Вишневский В.",
     "tier": "dnr", "roles": ["deputy_head"], "name_variants": ["Владислав Вишневский"],
     "org": "Управление Росреестра по ДНР", "evidence": ["telegram second-order sweep 2026-07-06"]},
    {"node_id": "person:трищенко-ю", "kind": "person", "canonical_name": "Трищенко Ю.",
     "tier": "dnr", "roles": ["deputy_head"], "name_variants": ["Юлия Трищенко"],
     "org": "Управление Росреестра по ДНР",
     "evidence": ["land-control изъятие under ЗК ст.42"]},
    {"node_id": "person:краснов-д", "kind": "person", "canonical_name": "Краснов Д.",
     "tier": "dnr", "roles": ["minister"], "name_variants": ["Дмитрий Краснов"],
     "org": "Минэкономразвития ДНР", "evidence": ["Инвесткомитет approvals for no-auction land grants"]},
    {"node_id": "person:кирьякулова-о", "kind": "person", "canonical_name": "Кирьякулова О.В.",
     "tier": "municipal", "roles": ["district_head"], "name_variants": ["Оксана Кирьякулова"],
     "org": "Управа Жовтневого внутригородского района",
     "evidence": ["Артёма 59/69 КРТ re-demolition собрания собственников"]},
    {"node_id": "person:кондратенко-и", "kind": "person", "canonical_name": "Кондратенко И.В.",
     "tier": "municipal", "roles": ["deputy_district_head"], "name_variants": [],
     "org": "Управа Жовтневого внутригородского района",
     "evidence": ["30-day-appearance / 60-day-registration deadline architecture"]},
    {"node_id": "org:фрт", "kind": "org", "canonical_name": "ППК «Фонд развития территорий» (ФРТ)",
     "tier": "federal", "roles": [], "name_variants": ["ФРТ"], "org": "",
     "evidence": ["telegram second-order sweep 2026-07-06"]},
    {"node_id": "person:шагиахметов-и", "kind": "person", "canonical_name": "Шагиахметов И.",
     "tier": "federal", "roles": ["ceo"], "name_variants": ["Ильшат Шагиахметов"],
     "org": "ППК «Фонд развития территорий»",
     "evidence": ["land register (3,388 га), аварийное-жильё resettlement funding"]},
    {"node_id": "person:максимова-ю", "kind": "person", "canonical_name": "Максимова Ю.",
     "tier": "federal", "roles": ["director"], "name_variants": ["Юлия Максимова"],
     "org": "ФАУ «РосКапСтрой»", "evidence": ["РКС-НР → РосКапСтрой → Минстрой РФ chain"]},
    {"node_id": "person:чернова-е", "kind": "person", "canonical_name": "Чернова Е.Н.",
     "tier": "dnr", "roles": ["cadastral_engineer"], "name_variants": ["Екатерина Чернова"],
     "org": "ППК «Роскадастр» филиал по ДНР",
     "evidence": ["telegram:zhovtnevyy/602 (Госконтракт №14/2024 ККР execution)"]},
    {"node_id": "person:колударова-о", "kind": "person", "canonical_name": "Колударова О.П.",
     "tier": "dnr", "roles": ["acting_minister"], "name_variants": [],
     "org": "Министерство образования и науки ДНР (и.о.)",
     "evidence": ["telegram:ssaniaworld/567 (alleged school-liquidation order, unconfirmed)"]},
    {"node_id": "person:найденов-с", "kind": "person", "canonical_name": "Найденов С.А.",
     "tier": "dnr", "roles": ["deputy_minister"], "name_variants": [],
     "org": "Министерство образования и науки ДНР",
     "evidence": ["telegram:ssaniaworld/567 (alleged school-liquidation order, unconfirmed)"]},
    {"node_id": "org:муп-коммунальник", "kind": "org", "canonical_name": "МУП АГМ «Коммунальник»",
     "tier": "municipal", "roles": ["demolition_contractor"], "name_variants": [], "org": "",
     "evidence": ["telegram:sport_dlya_vsekh_Mariupol/4655 (пер. Транспортный 14 demolition, 2023-12-22)"]},
]

NEW_EDGES = [
    {"src": "person:переверзева-т", "rel": "public_statement", "dst": "instr:dnr_normative_act",
     "count": 1, "date_min": "2026-05-01", "date_max": "2026-05-01",
     "source": "telegram:prav_dnr/42699", "refs": ["TASS 2026-05-01"]},
    {"src": "person:авдиенко-а", "rel": "signed", "dst": "instr:dnr_land_order",
     "count": 3, "date_min": "2023-10-06", "date_max": "2023-10-06",
     "source": "telegram:minstroydnr", "refs": ["3932", "3933", "3934"]},
    {"src": "person:сироватко-ю", "rel": "head_of_agency", "dst": "instr:dnr_normative_act",
     "count": 1, "date_min": "2023-10-24", "date_max": "2025-09-01",
     "source": "telegram:rosreestr80 + mrpl_besxozxata/10742", "refs": []},
    {"src": "person:чернова-е", "rel": "executed", "dst": "instr:dnr_normative_act",
     "count": 1, "date_min": "2024-02-07", "date_max": "2024-10-01",
     "source": "telegram:zhovtnevyy/602", "refs": ["Госконтракт №14/2024"]},
    {"src": "org:муп-коммунальник", "rel": "demolished", "dst": "instr:demolition_decree",
     "count": 1, "date_min": "2023-12-22", "date_max": "2023-12-22",
     "source": "telegram:sport_dlya_vsekh_Mariupol/4655", "refs": []},
]


def _load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    nodes = _load(NODES_PATH)
    existing_ids = {n["node_id"] for n in nodes}
    added_nodes = [n for n in NEW_NODES if n["node_id"] not in existing_ids]

    edges = _load(EDGES_PATH)
    existing_edge_keys = {(e["src"], e["rel"], e["dst"]) for e in edges}
    added_edges = [e for e in NEW_EDGES if (e["src"], e["rel"], e["dst"]) not in existing_edge_keys]

    if not added_nodes and not added_edges:
        print("Nothing to add — all node_ids/edges already present.", file=sys.stderr)
        return

    with open(NODES_PATH, "a", encoding="utf-8") as f:
        for n in added_nodes:
            f.write(json.dumps(n, ensure_ascii=False) + "\n")
    with open(EDGES_PATH, "a", encoding="utf-8") as f:
        for e in added_edges:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(f"Added {len(added_nodes)} nodes, {len(added_edges)} edges "
          f"(skipped {len(NEW_NODES) - len(added_nodes)} already-present nodes).", file=sys.stderr)


if __name__ == "__main__":
    main()
