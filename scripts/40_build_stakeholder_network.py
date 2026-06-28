#!/usr/bin/env python3
"""Stage 4a: build the stakeholder network — every named occupation actor
(officials, judges, administrations, developers, contractors) consolidated
from the parsed evidence into one queryable graph.

Companion to docs/stakeholder_network.md (the curated framework; this script
generates the data-driven graph it describes).

Reads (all already-parsed local files; no network):
  data/parsed/ownerless_decrees.jsonl      -- signing_official (rung [A])
  data/parsed/demolition_decrees.jsonl     -- signing_official + commission ([C])
  data/parsed/dnr_land_orders.jsonl        -- Глава ДНР -> developer grants ([D])
  data/parsed/damage_assessment.jsonl      -- federal contractors ([E])
  data/parsed/pravo_region80_relevant.jsonl -- DNR signatory authorities
  data/parsed/egrul_inn_lookups.jsonl      -- developer INN/OGRN/directors
  data/parsed/open_source_investigations.jsonl -- curated journalism findings
Optionally (graceful skip if unreachable):
  PostgreSQL (config.DATABASE_URL)         -- judges + petitioners ([B])

PRIVACY (CLAUDE.md hard rule): housing-list claimants and lawful owners are
private individuals and are NEVER read by this script. In-scope actors are
occupation officials, judges, and beneficiaries acting in official or
commercial capacity only.

Output:
  data/parsed/stakeholder_nodes.jsonl  -- one row per actor/instrument-class
  data/parsed/stakeholder_edges.jsonl  -- one row per (src, rel, dst) with
                                          counts, date ranges, evidence refs
  data/reports/stakeholder_network.md  -- auto-generated summary tables
  data/reports/stakeholder_network.dot -- Graphviz export (dot -Tsvg ...)

Run locally, no network:  python3 scripts/40_build_stakeholder_network.py
(use .venv/bin/python3 if system python lacks psycopg2/dotenv)
"""
from __future__ import annotations

import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402

log = logging.getLogger(__name__)

PARSED_DIR = config.PROJECT_ROOT / "data" / "parsed"
REPORTS_DIR = config.PROJECT_ROOT / "data" / "reports"

NODES_OUT = PARSED_DIR / "stakeholder_nodes.jsonl"
EDGES_OUT = PARSED_DIR / "stakeholder_edges.jsonl"
REPORT_OUT = REPORTS_DIR / "stakeholder_network.md"
DOT_OUT = REPORTS_DIR / "stakeholder_network.dot"

# ---------------------------------------------------------------------------
# Instrument-class bridge nodes: officials sign INTO these, beneficiaries
# receive OUT of these. Keeps the graph readable instead of 1,000+ decree
# nodes; per-decree refs live in edge evidence.
# ---------------------------------------------------------------------------
INSTRUMENT_CLASSES = {
    "instr:ownerless_decree": "Ownerless decrees (rung A)",
    "instr:demolition_decree": "Demolition decrees (rung C)",
    "instr:court_proceedings": "Особое-производство transfers (rung B)",
    "instr:dnr_land_order": "DNR land-reallocation orders (rung D)",
    "instr:reconstruction": "Federal reconstruction contracts (rung E)",
    "instr:dnr_normative_act": "DNR normative acts (framework)",
}

# Locations that appear inside the damage-assessment contractor field --
# either as a city suffix ("Крост, Санкт-Петербург") or standing alone as a
# shef-region entry ("Тульская область").
_KNOWN_LOCATIONS = {
    "санкт-петербург", "москва", "московская область", "тульская область",
    "ленинградская область", "тула",
}

_INITIALS_FIRST_RE = re.compile(r"^([А-ЯЁ]\.\s*[А-ЯЁ]?\.?)\s+([А-ЯЁ][а-яё-]+)$")
_SURNAME_FIRST_RE = re.compile(r"^([А-ЯЁ][а-яё-]+)\s+([А-ЯЁ]\.\s*[А-ЯЁ]?\.?)$")
_FULL_FIO_RE = re.compile(
    r"^([А-ЯЁ][А-Яа-яЁё-]+)\s+([А-ЯЁ][А-Яа-яЁё-]+)\s+([А-ЯЁ][А-Яа-яЁё-]+)$"
)


def canon_person(raw: str) -> str | None:
    """Canonicalize a person name to 'Surname I.I.' form.

    'А.В. Кольцов' -> 'Кольцов А.В.';  'Д. В. Пушилин' -> 'Пушилин Д.В.';
    'Цыба Л.В.' -> 'Цыба Л.В.';  'ХАРЛАМОВА ТАТЬЯНА СЕРГЕЕВНА' ->
    'Харламова Т.С.' (full FIO also kept by the caller as a variant).
    Returns None if the value does not look like a person name.
    """
    s = re.sub(r"\s+", " ", raw or "").strip().strip(",")
    if not s:
        return None
    m = _INITIALS_FIRST_RE.match(s)
    if m:
        initials = m.group(1).replace(" ", "")
        return f"{m.group(2)} {initials}"
    m = _SURNAME_FIRST_RE.match(s)
    if m:
        initials = m.group(2).replace(" ", "")
        return f"{m.group(1)} {initials}"
    m = _FULL_FIO_RE.match(s)
    if m:
        surname, first, patro = (g.capitalize() for g in m.groups())
        return f"{surname} {first[0]}.{patro[0]}."
    return None


def org_key(raw: str) -> str:
    """Matching key for an organization: case/quote/legal-form-insensitive."""
    s = re.sub(r"\s+", " ", raw or "").strip()
    s = re.sub(r"[«»\"']", "", s)
    s = re.sub(r"\s*[—–-]\s*", "-", s)
    s = re.sub(
        r"^(ООО|АО|ГУП|МУП|ППК|ПАО)\s+", "", s, flags=re.I)
    s = re.sub(
        r"^(СПЕЦИАЛИЗИРОВАННЫЙ ЗАСТРОЙЩИК|СЗ)[-\s]*\d*\s*", "", s, flags=re.I)
    return s.upper()


def _slug(text: str) -> str:
    return re.sub(r"[^0-9a-zа-яё]+", "-", text.lower()).strip("-")


class Graph:
    """Accumulates deduplicated nodes and counted edges."""

    def __init__(self) -> None:
        self.nodes: dict[str, dict] = {}
        # (src, rel, dst) -> aggregate
        self.edges: dict[tuple[str, str, str], dict] = {}
        for nid, label in INSTRUMENT_CLASSES.items():
            self.nodes[nid] = {
                "node_id": nid, "kind": "instrument_class",
                "canonical_name": label, "tier": "pipeline",
                "roles": [], "name_variants": [], "evidence": [],
            }
        self._org_index: dict[str, str] = {}     # org_key -> node_id
        self._person_index: dict[str, str] = {}  # canon name -> node_id

    def person(self, raw: str, *, tier: str, role: str,
               org: str | None = None) -> str | None:
        canon = canon_person(raw)
        if canon is None:
            log.debug("not a person name, skipped: %r", raw)
            return None
        nid = self._person_index.get(canon)
        if nid is None:
            nid = f"person:{_slug(canon)}"
            self._person_index[canon] = nid
            self.nodes[nid] = {
                "node_id": nid, "kind": "person", "canonical_name": canon,
                "tier": tier, "roles": [], "name_variants": [],
                "org": org, "evidence": [],
            }
        node = self.nodes[nid]
        if role not in node["roles"]:
            node["roles"].append(role)
        if raw != canon and raw not in node["name_variants"]:
            node["name_variants"].append(raw)
        if org and not node.get("org"):
            node["org"] = org
        return nid

    def org(self, raw: str, *, tier: str, role: str, **attrs) -> str | None:
        name = re.sub(r"\s+", " ", raw or "").strip().strip(",")
        if not name:
            return None
        if len(name) > 120:
            log.warning("org name >120 chars looks like OCR garbage, "
                        "skipped: %.80r...", name)
            return None
        key = org_key(name)
        nid = self._org_index.get(key)
        if nid is None:
            nid = f"org:{_slug(key)}"
            self._org_index[key] = nid
            self.nodes[nid] = {
                "node_id": nid, "kind": "org", "canonical_name": name,
                "tier": tier, "roles": [], "name_variants": [],
                "evidence": [],
            }
        node = self.nodes[nid]
        if role not in node["roles"]:
            node["roles"].append(role)
        if name != node["canonical_name"] and name not in node["name_variants"]:
            node["name_variants"].append(name)
        for k, v in attrs.items():
            if v and not node.get(k):
                node[k] = v
        return nid

    def edge(self, src: str | None, rel: str, dst: str | None, *,
             source: str, ref: str | None = None,
             date: str | None = None) -> None:
        if not src or not dst:
            return
        key = (src, rel, dst)
        e = self.edges.get(key)
        if e is None:
            e = self.edges[key] = {
                "src": src, "rel": rel, "dst": dst, "count": 0,
                "date_min": None, "date_max": None,
                "source": source, "refs": [],
            }
        e["count"] += 1
        if date:
            e["date_min"] = min(e["date_min"] or date, date)
            e["date_max"] = max(e["date_max"] or date, date)
        if ref and len(e["refs"]) < 25 and ref not in e["refs"]:
            e["refs"].append(ref)

    def note_evidence(self, nid: str | None, source: str) -> None:
        if nid and source not in self.nodes[nid]["evidence"]:
            self.nodes[nid]["evidence"].append(source)


def _read_jsonl(path: Path):
    if not path.exists():
        log.warning("missing input, skipped: %s", path)
        return
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                log.error("%s line %d: bad JSON (%s)", path.name, i, e)


# ---------------------------------------------------------------------------
# Source loaders
# ---------------------------------------------------------------------------
def load_ownerless(g: Graph) -> None:
    src = "ownerless_decrees.jsonl"
    n = 0
    for rec in _read_jsonl(PARSED_DIR / src):
        official = rec.get("signing_official")
        if not official:
            continue
        nid = g.person(official, tier="municipal", role="signing_official",
                       org="Администрация городского округа Мариуполь")
        g.edge(nid, "signed", "instr:ownerless_decree", source=src,
               ref=rec.get("decree_number"), date=rec.get("decree_date"))
        g.note_evidence(nid, src)
        n += 1
    log.info("%s: %d signed rows", src, n)


def load_demolition(g: Graph) -> None:
    src = "demolition_decrees.jsonl"
    n = 0
    for rec in _read_jsonl(PARSED_DIR / src):
        signer = rec.get("signing_official")
        if signer:
            nid = g.person(signer, tier="municipal", role="signing_official",
                           org="Администрация городского округа Мариуполь")
            g.edge(nid, "signed", "instr:demolition_decree", source=src,
                   ref=rec.get("decree_number"), date=rec.get("decree_date"))
            g.note_evidence(nid, src)
        for off in rec.get("officials") or []:
            name = (off or {}).get("name", "")
            if not name or canon_person(name) == canon_person(signer or ""):
                continue
            role_raw = (off.get("role") or "").strip()
            # OCR truncates titles; МУП «Коммунальник» members keep their org
            org = ("МУП «Коммунальник»" if "Коммунальник" in role_raw
                   else "Администрация городского округа Мариуполь")
            nid = g.person(name, tier="municipal", role="commission_member",
                           org=org)
            g.edge(nid, "commission_member", "instr:demolition_decree",
                   source=src, ref=rec.get("decree_number"),
                   date=rec.get("decree_date"))
            g.note_evidence(nid, src)
        n += 1
    log.info("%s: %d decrees", src, n)


def load_land_orders(g: Graph) -> None:
    src = "dnr_land_orders.jsonl"
    n_grants = 0
    for rec in _read_jsonl(PARSED_DIR / src):
        signer_id = None
        if rec.get("signing_official"):
            signer_id = g.person(rec["signing_official"], tier="dnr",
                                 role="signing_official",
                                 org=rec.get("issuing_body") or "Глава ДНР")
            g.edge(signer_id, "signed", "instr:dnr_land_order", source=src,
                   ref=rec.get("decree_number"), date=rec.get("decree_date"))
            g.note_evidence(signer_id, src)
        beneficiary = rec.get("beneficiary_name")
        if beneficiary:
            dev_id = g.org(beneficiary, tier="commercial", role="developer",
                           inn=rec.get("beneficiary_inn"),
                           ogrn=rec.get("beneficiary_ogrn"))
            if dev_id:
                g.edge(dev_id, "received_grant", "instr:dnr_land_order",
                       source=src, ref=rec.get("decree_number"),
                       date=rec.get("decree_date"))
                if signer_id:
                    g.edge(signer_id, "granted_land_to", dev_id, source=src,
                           ref=rec.get("decree_number"),
                           date=rec.get("decree_date"))
                g.note_evidence(dev_id, src)
                n_grants += 1
    log.info("%s: %d beneficiary grants", src, n_grants)


def _split_contractors(raw: str) -> tuple[list[str], str | None]:
    """Split a contractor cell into org names + optional location.

    'Крост, Санкт-Петербург' -> (['Крост'], 'Санкт-Петербург')
    'ООО "Монотек Строй", АО "ИНТЕКО"' -> both orgs, no location
    'Тульская область' -> ([], 'Тульская область')  (shef-region row)
    """
    parts = [p.strip() for p in (raw or "").split(",") if p.strip()]
    orgs: list[str] = []
    location = None
    for p in parts:
        if p.lower() in _KNOWN_LOCATIONS:
            location = p
        else:
            orgs.append(p)
    return orgs, location


def load_damage_assessment(g: Graph) -> None:
    src = "damage_assessment.jsonl"
    executor_id = None
    n = 0
    for rec in _read_jsonl(PARSED_DIR / src):
        addr_ref = rec.get("address_raw")
        executor = rec.get("responsible_executor")
        if executor:
            executor_id = g.org(executor, tier="federal",
                                role="responsible_executor")
            g.note_evidence(executor_id, src)
        contractor = rec.get("contractor")
        if not contractor:
            continue
        orgs, location = _split_contractors(contractor)
        if not orgs and location:
            # shef-region listed as the executing entity itself
            rid = g.org(location, tier="federal", role="shef_region")
            g.edge(rid, "received_contract", "instr:reconstruction",
                   source=src, ref=addr_ref)
            g.note_evidence(rid, src)
            continue
        for org_name in orgs:
            cid = g.org(org_name, tier="federal", role="contractor",
                        location=location)
            g.edge(cid, "received_contract", "instr:reconstruction",
                   source=src, ref=addr_ref)
            if executor_id:
                g.edge(executor_id, "oversees", cid, source=src)
            g.note_evidence(cid, src)
        n += 1
    log.info("%s: %d contracted buildings", src, n)


def load_region80(g: Graph) -> None:
    src = "pravo_region80_relevant.jsonl"
    n = 0
    for rec in _read_jsonl(PARSED_DIR / src):
        for auth in rec.get("signatory_authorities") or []:
            # 'Донецкая Народная Республика' as authority = the laws signed
            # by the Глава; keep it as the issuing org it names.
            aid = g.org(auth, tier="dnr", role="signatory_authority")
            g.edge(aid, "issued", "instr:dnr_normative_act", source=src,
                   ref=f"{rec.get('document_type','')} {rec.get('number','')}".strip(),
                   date=(rec.get("document_date") or "")[:10] or None)
            g.note_evidence(aid, src)
        n += 1
    log.info("%s: %d acts", src, n)


def load_egrul(g: Graph) -> None:
    src = "egrul_inn_lookups.jsonl"
    n = 0
    for rec in _read_jsonl(PARSED_DIR / src):
        name = rec.get("short_name") or rec.get("beneficiary_name")
        if not name:
            continue
        dev_id = g.org(name, tier="commercial", role="developer",
                       inn=rec.get("inn"), ogrn=rec.get("ogrn"),
                       ogrn_date=rec.get("ogrn_date"),
                       address=rec.get("address"),
                       status=rec.get("status"))
        g.note_evidence(dev_id, src)
        # also index the land-order spelling so both resolve to one node
        if rec.get("beneficiary_name"):
            g.org(rec["beneficiary_name"], tier="commercial", role="developer")
        director = rec.get("director")
        if director and dev_id:
            pid = g.person(director, tier="commercial", role="director")
            g.edge(pid, "directs", dev_id, source=src, ref=rec.get("inn"))
            g.note_evidence(pid, src)
            n += 1
    log.info("%s: %d director links", src, n)


def load_open_source_investigations(g: Graph) -> None:
    """Curated findings from published investigative journalism (dossier.center,
    The Insider, Novaya Gazeta Europa, Current Time) -- federal-tier actors not
    discoverable through court/decree/EGRUL records alone (e.g. a Moscow MoD
    contractor chain with no DNR-local SPV). Each record in
    open_source_investigations.jsonl is a single named-source finding; add via
    the same file, not by hand-editing the generated nodes/edges output."""
    src = "open_source_investigations.jsonl"
    n = 0
    for rec in _read_jsonl(PARSED_DIR / src):
        local_ids: dict[str, str] = {}
        for o in rec.get("orgs", []):
            oid = g.org(o["canonical_name"], tier=o.get("tier", "commercial"),
                        role=o.get("role", "contractor"),
                        inn=o.get("inn"), ogrn=o.get("ogrn"),
                        address=o.get("address"))
            if oid:
                local_ids[o["canonical_name"]] = oid
                for nv in o.get("name_variants", []):
                    if nv not in g.nodes[oid]["name_variants"]:
                        g.nodes[oid]["name_variants"].append(nv)
                if o.get("notes"):
                    g.nodes[oid]["notes"] = o["notes"]
                g.note_evidence(oid, src)
        for p in rec.get("persons", []):
            pid = g.person(p["canonical_name"], tier=p.get("tier", "commercial"),
                           role=p.get("role", "founder"), org=p.get("org"))
            if pid:
                local_ids[p["canonical_name"]] = pid
                for nv in p.get("name_variants", []):
                    if nv not in g.nodes[pid]["name_variants"]:
                        g.nodes[pid]["name_variants"].append(nv)
                if p.get("notes"):
                    g.nodes[pid]["notes"] = p["notes"]
                g.note_evidence(pid, src)
        for e in rec.get("edges", []):
            s_id = local_ids.get(e["src"])
            d_id = local_ids.get(e["dst"])
            g.edge(s_id, e["rel"], d_id, source=src, ref=e.get("ref"))
        n += 1
    log.info("%s: %d findings", src, n)


# Court-portal petitioner strings are clerk-typed free text with heavy typos
# ('Администарция грода Мариупоял', ...). Deterministic keyword buckets ->
# canonical org; the raw spelling is preserved in name_variants. Canonical
# DNR-organ names match the region80 spellings so the nodes merge.
_PETITIONER_BUCKETS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"прокурор", re.I),
     "Прокуратура города Мариуполя", "dnr"),
    (re.compile(r"имущественных", re.I),
     "Министерство имущественных и земельных отношений "
     "Донецкой Народной Республики", "dnr"),
    (re.compile(r"фонд государственного имущества|^ФГИ\b", re.I),
     "Фонд государственного имущества Донецкой Народной Республики", "dnr"),
    (re.compile(r"строительства", re.I),
     "Министерство строительства и ЖКХ Донецкой Народной Республики", "dnr"),
    (re.compile(r"морского порта", re.I),
     "ГУП ДНР «Администрация морского порта г. Мариуполя»", "dnr"),
    (re.compile(r"орджоникидзевского района", re.I),
     "Администрация Орджоникидзевского района г. Мариуполя", "municipal"),
    # the dominant petitioner, in dozens of misspellings of 'Мариуполь'
    (re.compile(r"(администрац|муниципальное образование).*(мар|г\.\s*м)",
                re.I | re.S),
     "Администрация городского округа Мариуполь", "municipal"),
]

# NB: no IGNORECASE here -- the strict-case classes are what keep lowercase
# title words ('советник юстиции') out of the captured name.
_PROSECUTOR_PERSON_RE = re.compile(
    r"[Пп]рокурор.*?((?:[А-ЯЁ]\.\s*){1,2}[А-ЯЁ][а-яё-]+|"
    r"[А-ЯЁ][а-яё-]+\s+(?:[А-ЯЁ]\.\s*){1,2})", re.S)

# Fuzzy fallback for clerk typos the keyword buckets miss ('Адмиистрация',
# 'Мриуполь', 'М ариуполя', ...). Compares ONLY the extracted city/raion
# token against 'мариуполь', not the whole templated string -- the region's
# many absorbed-jurisdiction courts (Торез, Дебальцево, Иловайск, ...) share
# the same "Администрация городского округа <city>" boilerplate, so a
# whole-string ratio (token_set_ratio against a 'мариуполь'-named prototype)
# scored those at 0.82-0.99 even though the one token that actually
# identifies the entity -- the city -- is completely different. Isolating
# that token first fixed it: genuine Mariupol typos still score 0.94-1.00,
# real other-city administrations score 0.14-0.32. Per CLAUDE.md, every
# fuzzy match is confidence-scored; >=0.8 required.
_CITY_TOKEN_RE = re.compile(
    r"(?:городского округа|города)\s+(?:г\.\s*)?([А-Яа-яЁё-]+)", re.I)


def canon_petitioner(raw: str) -> tuple[str | None, str, float]:
    """Bucket a raw petitioner string -> (canonical org, tier, confidence).

    Keyword-bucket hits are deterministic (confidence 1.0); otherwise a
    rapidfuzz pass on the extracted city token (claim-grade threshold 0.8).
    Returns (None, '', 0.0) when nothing matches.
    """
    for pat, canonical, tier in _PETITIONER_BUCKETS:
        if pat.search(raw):
            return canonical, tier, 1.0
    m = _CITY_TOKEN_RE.search(raw)
    if not m:
        return None, "", 0.0
    try:
        from rapidfuzz import fuzz
    except ImportError:
        log.warning("rapidfuzz unavailable — typo-variant petitioners "
                    "kept unconsolidated")
        return None, "", 0.0
    score = fuzz.ratio(m.group(1).lower(), "мариуполь") / 100
    if score >= 0.8:
        canonical = "Администрация городского округа Мариуполь"
        log.info("fuzzy petitioner match (%.2f): %r -> %r", score, raw, canonical)
        return canonical, "municipal", score
    return None, "", 0.0


def load_postgres(g: Graph) -> None:
    """Judges + petitioners from the DB; skipped with a warning if down."""
    try:
        import psycopg2
        con = psycopg2.connect(config.DATABASE_URL)
    except Exception as e:  # noqa: BLE001 -- any driver/conn issue = skip
        log.warning("PostgreSQL unavailable (%s) — judges/petitioners "
                    "skipped; rerun when the DB is up", e)
        return
    src = "postgres:court_case/actor"
    try:
        with con, con.cursor() as cur:
            cur.execute("""
                SELECT judge, court, COUNT(*), MIN(decided_date), MAX(decided_date)
                FROM court_case WHERE judge IS NOT NULL
                GROUP BY judge, court""")
            for judge, court, cnt, dmin, dmax in cur.fetchall():
                nid = g.person(judge, tier="judicial", role="judge", org=court)
                if nid is None:
                    nid = g.org(judge, tier="judicial", role="judge")
                for _ in range(cnt):
                    g.edge(nid, "ruled_in", "instr:court_proceedings",
                           source=src, date=str(dmin) if dmin else None)
                e = g.edges.get((nid, "ruled_in", "instr:court_proceedings"))
                if e:
                    e["date_min"] = str(dmin) if dmin else e["date_min"]
                    e["date_max"] = str(dmax) if dmax else e["date_max"]
                g.note_evidence(nid, src)

            # Court petitioners-of-record. The actor table mixes two
            # populations under role='signing_official' with NULL org:
            # decree signers (linked to seizure events by the decree
            # loaders -- already counted from the parsed files above, so
            # re-adding them here would double-count) and court petitioners
            # (upserted by the case loader WITHOUT event links). Keep only
            # the zero-event-link rows.
            cur.execute("""
                SELECT a.full_name
                FROM actor a
                LEFT JOIN event_actor ea ON ea.actor_id = a.id
                WHERE a.role = 'signing_official' AND a.org IS NULL
                GROUP BY a.id, a.full_name
                HAVING COUNT(ea.seizure_event_id) = 0""")
            for (name,) in cur.fetchall():
                # 'Прокурор ... в интересах <municipality>' -> keep the organ,
                # drop the beneficiary clause (it can exceed the length guard)
                name = re.split(r"\s+в интересах\s+", name, flags=re.I)[0]
                canonical, tier, confidence = canon_petitioner(name)
                if canonical:
                    nid = g.org(canonical, tier=tier, role="petitioner")
                    node = g.nodes[nid]
                    if name != canonical and name not in node["name_variants"]:
                        node["name_variants"].append(name)
                    if confidence < 1.0:
                        node.setdefault("fuzzy_variants", {})[name] = round(
                            confidence, 2)
                    # a prosecutor petition naming the officeholder also
                    # yields a person node (e.g. 'старший советник юстиции
                    # Д.В. Гнездилов')
                    m = _PROSECUTOR_PERSON_RE.search(name)
                    if m:
                        pid = g.person(m.group(1), tier="dnr",
                                       role="petitioner", org=canonical)
                        g.edge(pid, "petitioned", "instr:court_proceedings",
                               source=src)
                        g.note_evidence(pid, src)
                else:
                    # unbucketed: person petitioner or unrecognized org --
                    # kept under its raw spelling
                    nid = (g.person(name, tier="municipal", role="petitioner")
                           or g.org(name, tier="municipal", role="petitioner"))
                g.edge(nid, "petitioned", "instr:court_proceedings",
                       source=src)
                g.note_evidence(nid, src)
        log.info("postgres: judges + petitioners loaded")
    except Exception as e:  # noqa: BLE001
        log.error("postgres query failed (%s) — partial court data", e)
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
def write_outputs(g: Graph) -> None:
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with NODES_OUT.open("w", encoding="utf-8") as f:
        for node in g.nodes.values():
            f.write(json.dumps(node, ensure_ascii=False) + "\n")
    with EDGES_OUT.open("w", encoding="utf-8") as f:
        for e in g.edges.values():
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    log.info("wrote %d nodes -> %s", len(g.nodes), NODES_OUT)
    log.info("wrote %d edges -> %s", len(g.edges), EDGES_OUT)

    _write_report(g)
    _write_dot(g)


def _write_report(g: Graph) -> None:
    by_tier: dict[str, list[dict]] = defaultdict(list)
    for n in g.nodes.values():
        if n["kind"] != "instrument_class":
            by_tier[n["tier"]].append(n)

    out_deg: dict[str, int] = defaultdict(int)
    for e in g.edges.values():
        out_deg[e["src"]] += e["count"]

    lines = [
        "# Stakeholder network — auto-generated summary",
        "",
        f"Nodes: **{sum(len(v) for v in by_tier.values())}** actors "
        f"(+{len(INSTRUMENT_CLASSES)} instrument classes) · "
        f"Edges: **{len(g.edges)}** distinct relations, "
        f"**{sum(e['count'] for e in g.edges.values())}** evidenced acts.",
        "",
        "Curated framework: `docs/stakeholder_network.md`. "
        "Regenerate: `python3 scripts/40_build_stakeholder_network.py`.",
        "",
    ]
    tier_order = ["federal", "dnr", "municipal", "judicial", "commercial"]
    for tier in tier_order + sorted(set(by_tier) - set(tier_order)):
        actors = by_tier.get(tier)
        if not actors:
            continue
        lines += [f"## {tier} ({len(actors)} actors)", "",
                  "| Actor | Kind | Roles | Evidenced acts | Sources |",
                  "|---|---|---|---|---|"]
        for n in sorted(actors, key=lambda x: -out_deg[x["node_id"]]):
            lines.append(
                f"| {n['canonical_name']} | {n['kind']} | "
                f"{', '.join(n['roles'])} | {out_deg[n['node_id']]} | "
                f"{', '.join(n['evidence'])} |")
        lines.append("")

    lines += ["## Top relations", "",
              "| From | rel | To | Count | Dates | Sample refs |",
              "|---|---|---|---|---|---|"]
    name = {nid: n["canonical_name"] for nid, n in g.nodes.items()}
    for e in sorted(g.edges.values(), key=lambda x: -x["count"])[:40]:
        dates = (f"{e['date_min']}…{e['date_max']}"
                 if e["date_min"] else "")
        refs = ", ".join(str(r) for r in e["refs"][:5])
        lines.append(f"| {name[e['src']]} | {e['rel']} | {name[e['dst']]} | "
                     f"{e['count']} | {dates} | {refs} |")
    lines.append("")
    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")
    log.info("wrote report -> %s", REPORT_OUT)


_TIER_COLOR = {
    "federal": "#b13c3c", "dnr": "#b07a2a", "municipal": "#2a6db0",
    "judicial": "#6b4fa0", "commercial": "#2a8a57", "pipeline": "#666666",
}


def _write_dot(g: Graph) -> None:
    lines = ["digraph stakeholders {",
             '  rankdir=LR; node [shape=box, style="rounded,filled", '
             'fontname="Helvetica", fontsize=10];']
    for n in g.nodes.values():
        color = _TIER_COLOR.get(n["tier"], "#999999")
        shape = "ellipse" if n["kind"] == "instrument_class" else "box"
        label = n["canonical_name"].replace('"', "'")
        lines.append(
            f'  "{n["node_id"]}" [label="{label}", shape={shape}, '
            f'fillcolor="{color}22", color="{color}"];')
    for e in g.edges.values():
        lines.append(
            f'  "{e["src"]}" -> "{e["dst"]}" '
            f'[label="{e["rel"]} ×{e["count"]}", fontsize=8];')
    lines.append("}")
    DOT_OUT.write_text("\n".join(lines), encoding="utf-8")
    log.info("wrote graphviz -> %s  (render: dot -Tsvg -O %s)",
             DOT_OUT, DOT_OUT.name)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    g = Graph()
    load_ownerless(g)
    load_demolition(g)
    load_land_orders(g)
    load_damage_assessment(g)
    load_region80(g)
    load_egrul(g)
    load_open_source_investigations(g)
    load_postgres(g)
    write_outputs(g)

    persons = sum(1 for n in g.nodes.values() if n["kind"] == "person")
    orgs = sum(1 for n in g.nodes.values() if n["kind"] == "org")
    log.info("done: %d persons, %d orgs, %d edges",
             persons, orgs, len(g.edges))


if __name__ == "__main__":
    main()
