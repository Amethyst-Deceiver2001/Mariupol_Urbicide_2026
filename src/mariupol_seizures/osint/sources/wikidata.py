"""Source 20 — Wikidata + Wikipedia geosearch near the address.

Notable-building metadata (heritage status, architect, construction date,
former use) for the rare property that has a Wikidata item, plus nearby
Wikipedia articles. Keyless, non-geoblocked — Claude-runnable.
"""
from __future__ import annotations

import logging

import requests

from ... import forensics
from .base import SourceResult, http_headers

log = logging.getLogger(__name__)

NAME = "wikidata"
RUN = "C"
NETWORK = True
DESCRIPTION = "Wikidata items + Wikipedia articles geosearch (notable-building metadata)"

WD_SPARQL = "https://query.wikidata.org/sparql"
WP_API = "https://ru.wikipedia.org/w/api.php"


def plan(bundle) -> str:
    return f"Wikidata SPARQL radius query + ru.wikipedia geosearch at the point"


def fetch(bundle, con, radius_m: float = 300.0) -> SourceResult:
    findings: list[dict] = []
    captured: list[str] = []
    km = radius_m / 1000.0

    # ── Wikidata: items within radius, with coords + labels ────────────────
    query = f"""
    SELECT ?item ?itemLabel ?dist ?coord WHERE {{
      SERVICE wikibase:around {{
        ?item wdt:P625 ?coord .
        bd:serviceParam wikibase:center "Point({bundle.lon} {bundle.lat})"^^geo:wktLiteral .
        bd:serviceParam wikibase:radius "{km}" .
        bd:serviceParam wikibase:distance ?dist .
      }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ru,uk,en". }}
    }} ORDER BY ?dist LIMIT 25
    """
    try:
        r = requests.get(WD_SPARQL, params={"query": query, "format": "json"},
                         headers=http_headers(), timeout=45)
        r.raise_for_status()
        captured.append(forensics.capture_source(
            r.content, url=WD_SPARQL + f"#around/{bundle.slug}",
            source_type="osint_wikidata_sparql",
            title=f"wikidata around {bundle.slug}",
            description=f"Wikidata items within {radius_m:.0f}m of pid={bundle.pid}.",
            content_type="application/json", http_status=r.status_code, con=con,
        ))
        for b in r.json().get("results", {}).get("bindings", []):
            findings.append({
                "kind": "wikidata_item",
                "qid": b.get("item", {}).get("value", "").rsplit("/", 1)[-1],
                "label": b.get("itemLabel", {}).get("value", ""),
                "distance_km": round(float(b.get("dist", {}).get("value", 0)), 3),
                "url": b.get("item", {}).get("value", ""),
            })
    except requests.RequestException as e:
        log.warning("wikidata SPARQL failed: %s", e)
        findings.append({"kind": "error", "stage": "wikidata", "error": str(e)})

    # ── Wikipedia (ru): geosearch ──────────────────────────────────────────
    try:
        r = requests.get(WP_API, params={
            "action": "query", "list": "geosearch",
            "gscoord": f"{bundle.lat}|{bundle.lon}",
            "gsradius": str(int(min(radius_m, 10000))), "gslimit": "20",
            "format": "json",
        }, headers=http_headers(), timeout=30)
        r.raise_for_status()
        for g in r.json().get("query", {}).get("geosearch", []):
            title = g.get("title", "")
            findings.append({
                "kind": "wikipedia_article",
                "title": title,
                "distance_m": g.get("dist"),
                "url": f"https://ru.wikipedia.org/wiki/{title.replace(' ', '_')}",
            })
    except requests.RequestException as e:
        log.warning("wikipedia geosearch failed: %s", e)

    n_wd = sum(1 for f in findings if f["kind"] == "wikidata_item")
    n_wp = sum(1 for f in findings if f["kind"] == "wikipedia_article")
    return SourceResult(NAME, True, f"{n_wd} Wikidata items, {n_wp} Wikipedia articles",
                        findings, captured)
