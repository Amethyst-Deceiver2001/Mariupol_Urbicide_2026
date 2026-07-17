#!/usr/bin/env python3
"""Assemble a per-address OSINT dossier from scripts/324 sweep results.

Reads data/reports/osint/<slug>/{bundle,<source>}.json and writes, in the
same directory:
  dossier.md    — human-readable, timeline-ordered; already-held spine
                  evidence up top, new finds below, every row linked to
                  its source URL + raw-store SHA.
  manifest.csv  — one machine row per artifact/finding.

Local only, no network — safe to run any time after any subset of sources.

Usage:
    PYTHONPATH=src .venv312/bin/python scripts/325_osint_dossier.py --pid 4837
    PYTHONPATH=src .venv312/bin/python scripts/325_osint_dossier.py --slug 4837_zelinskogo-17a
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures.osint.sources import REGISTRY  # noqa: E402

log = logging.getLogger(__name__)

OSINT_DIR = config.DATA_DIR / "reports" / "osint"


def find_dir(pid: int | None, slug: str | None) -> Path:
    if slug:
        d = OSINT_DIR / slug
        if d.exists():
            return d
        sys.exit(f"no sweep dir {d}")
    if pid is not None:
        hits = sorted(OSINT_DIR.glob(f"{pid}_*"))
        if hits:
            return hits[0]
        sys.exit(f"no sweep dir for pid {pid} under {OSINT_DIR}")
    sys.exit("need --pid or --slug")


def _date_key(f: dict) -> str:
    for k in ("date", "date_original", "release_date", "year", "created"):
        v = f.get(k)
        if v:
            return str(v)[:10]
    return ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int)
    ap.add_argument("--slug")
    args = ap.parse_args()
    d = find_dir(args.pid, args.slug)

    bundle = json.loads((d / "bundle.json").read_text(encoding="utf-8"))
    results: dict[str, dict] = {}
    for f in sorted(d.glob("*.json")):
        if f.stem in ("bundle",):
            continue
        try:
            results[f.stem] = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            log.warning("unreadable result: %s", f)

    lines: list[str] = []
    add = lines.append
    addr = bundle.get("occupation_address") or bundle.get("prewar_address") or "?"
    add(f"# OSINT dossier — {addr}")
    add("")
    add(f"- **pid**: {bundle.get('pid')}  •  **building_id**: `{bundle.get('building_id')}`")
    if bundle.get("prewar_address") and bundle.get("occupation_address") \
            and bundle["prewar_address"] != bundle["occupation_address"]:
        add(f"- **pre-war**: {bundle['prewar_address']}  •  "
            f"**occupation**: {bundle['occupation_address']}")
    add(f"- **point**: {bundle.get('lat'):.6f}, {bundle.get('lon'):.6f}")
    add(f"- **assembled**: {_dt.date.today().isoformat()}; sweep sources present: "
        f"{', '.join(sorted(results)) or 'none'}")
    add("")

    # ── already-held evidence ──────────────────────────────────────────────
    le = results.get("local_evidence", {})
    add("## Already on the spine")
    add("")
    if le:
        stages = [f for f in le.get("findings", []) if f.get("kind") == "seizure_stage"]
        fams = [f for f in le.get("findings", []) if f.get("kind") == "corroboration_family"]
        cw = [f for f in le.get("findings", []) if f.get("kind") == "crosswalk"]
        eis = [f for f in le.get("findings", []) if f.get("kind") == "eisghs_nearby"]
        if stages:
            add("| stage | events | first | last |")
            add("|---|---|---|---|")
            for s in stages:
                add(f"| {s['stage']} | {s['count']} | {s['first'][:10]} | {s['last'][:10]} |")
            add("")
        if fams:
            add("Corroboration families already loaded: " +
                ", ".join(f"{f['family']} ({f['count']})" for f in fams))
            add("")
        for c in cw:
            add(f"- **Crosswalk**: replaced by ЕИСЖС object {c.get('eisghs_id')} — "
                f"{c.get('note','')[:200]}")
        for e in eis:
            add(f"- ЕИСЖС nearby: {e.get('eisghs_id')} {e.get('address') or ''} "
                f"({e.get('developer') or '?'}, {e['distance_m']}m)")
        mentions = [f for f in le.get("findings", []) if f.get("kind") == "corpus_mention"]
        if mentions:
            add("")
            add(f"### Chat-corpus mentions ({len(mentions)} shown)")
            add("")
            for m in mentions[:20]:
                add(f"- [{m.get('date','')}]({m.get('url','')}) `{m['corpus']}` — "
                    f"{m['excerpt']}")
    else:
        add("_local_evidence not yet run_")
    add("")

    # ── original sources & archives ────────────────────────────────────────
    add("## Original sources & archives")
    add("")
    src_rows = [f for f in le.get("findings", []) if f.get("kind") == "source_document"]
    arch = results.get("archives", {})
    arch_by_url = {f["url"]: f for f in arch.get("findings", [])
                  if f.get("kind") == "archive_match"}
    if src_rows:
        add("Every original-source URL on record for this property. 🔒 = "
            "confirmed geoblocked from outside Russia in this project's own "
            "source catalogue (`docs/sources.md`) — **the link is still "
            "given regardless**, per project convention; access it with "
            "your Russia-routed connection and paste back what you find. "
            "Archive columns are best-effort automated lookups, not proof "
            "of absence — archive.today rate-limits scripts, so a blank "
            "there means check manually, not that no snapshot exists.")
        add("")
        add("| source | date | url | Wayback | archive.today |")
        add("|---|---|---|---|---|")
        for s in src_rows:
            badge = "🔒 " if s["geoblocked"] else ""
            a = arch_by_url.get(s["url"], {})
            wb = (f"[{a['wayback_timestamp'][:8]}]({a['wayback_url']})"
                  if a.get("wayback_url")
                  else "_rate-limited, re-run_" if a.get("wayback_rate_limited")
                  else "—" if a else "_not checked_")
            at = (f"[copy]({a['archive_today_url']})" if a.get("archive_today_url")
                  else "_check manually_")
            add(f"| {s['via']} | {s.get('date','')[:10]} | "
                f"{badge}[{s['url'][:70]}]({s['url']}) | {wb} | {at} |")
        if not arch:
            add("")
            add("_archives source not yet run — Wayback/archive.today "
                "columns above are empty; run `--sources archives`_")
    else:
        add("_no original-source URLs on record yet (or local_evidence not run)_")
    add("")

    # ── death records ──────────────────────────────────────────────────────
    dr = results.get("death_records", {})
    add("## Death records at this address")
    add("")
    if dr:
        victims = [f for f in dr.get("findings", []) if f.get("kind") == "victim"]
        anon = [f for f in dr.get("findings", []) if f.get("kind") == "address_mention"]
        for v in victims:
            recs = v.get("records", [])
            best = recs[0] if recs else {}
            add(f"- **{v['victim_name']}** — sources: {', '.join(v['sources'])}; "
                f"date {best.get('date','?')}; "
                + (f"[link]({best.get('url')})" if best.get("url") else ""))
        if anon:
            add(f"- _{len(anon)} further unnamed address mentions in "
                f"{len(set(a['source'] for a in anon))} sources (see manifest)_")
        if not victims and not anon:
            add("_none found in local corpora_")
    else:
        add("_death_records not yet run_")
    add("")

    # ── timeline of media/artifacts ────────────────────────────────────────
    add("## Media & artifact timeline")
    add("")
    add("| date | source | what | link | sha256 |")
    add("|---|---|---|---|---|")
    rows: list[tuple[str, str, str, str, str]] = []
    for sname, res in results.items():
        if sname in ("local_evidence", "death_records"):
            continue
        for f in res.get("findings", []):
            k = f.get("kind", "")
            date = _date_key(f)
            if k == "historical_photo":
                what = f"PastVu «{f.get('title','')[:60]}» ({f.get('year')}–{f.get('year2')})"
                link, sha = f.get("page_url", ""), f.get("sha256", "")
                date = str(f.get("year") or "")
            elif k == "commons_photo":
                what = f"Commons {f.get('title','')[:60]}"
                link, sha = f.get("page_url", ""), f.get("sha256", "")
            elif k == "eor_event":
                what = f"EoR {f.get('category','')}: {f.get('description','')[:80]}"
                link, sha = f.get("link", ""), ""
            elif k == "wayback_mosaic":
                what = f"Wayback satellite «{f['label']}» (release {f['release_date']}, z{f['zoom']})"
                link, sha = "", f.get("sha256", "")
                date = f.get("release_date", "")
            elif k == "mapillary_image":
                what = f"Mapillary street-level {f.get('id','')}"
                link, sha = f.get("url", ""), f.get("sha256", "")
            elif k == "panoramax_image":
                signs = f" ({f['n_sign_detections']} sign detections)" if f.get("n_sign_detections") else ""
                what = f"Panoramax street-level {f.get('id','')}{signs}"
                link, sha = f.get("url", ""), f.get("sha256", "")
            elif k == "kartaview_image":
                what = f"Kartaview street-level {f.get('id','')}"
                link, sha = f.get("url", ""), f.get("sha256", "")
            elif k == "planet_scene" and f.get("sha256"):
                cloud = f.get("cloud_cover")
                cloud_s = f" cloud={cloud:.0%}" if isinstance(cloud, (int, float)) else ""
                what = (f"Planet {f.get('item_type','')} scene exists{cloud_s} "
                       f"(date-corroboration only — whole-scene thumbnail, not "
                       f"address-cropped; trial has no Orders/tile access)")
                link, sha = f.get("url", ""), f.get("sha256", "")
                date = f.get("acquired", "")
            elif k == "pc_scene" and f.get("sha256"):
                cloud = f.get("cloud_cover")
                cloud_s = f" cloud={cloud:.1%}" if isinstance(cloud, (int, float)) else ""
                what = (f"Planetary Computer Sentinel-2 AOI-cropped true-color "
                       f"(10m/px){cloud_s} — genuine address-level crop, not a "
                       f"whole-scene thumbnail")
                link, sha = f.get("url", ""), f.get("sha256", "")
                date = f.get("acquired", "")
            elif k == "flickr_photo":
                what = f"Flickr «{f.get('title','')[:50]}» by {f.get('owner','')}"
                link, sha = f.get("url", ""), f.get("sha256", "")
                date = f.get("date_taken", "")[:10]
            elif k == "vk_photo":
                what = f"VK photo {f.get('text','')[:50]}"
                link, sha = f.get("url", ""), f.get("sha256", "")
            elif k == "prewar_listing_candidate" and f.get("address_verified"):
                what = f"pre-war listing ({f.get('host','')}) — address-verified"
                link, sha = f.get("wayback_url", ""), f.get("sha256", "")
                date = f.get("timestamp", "")[:8]
            else:
                continue
            rows.append((date, sname, what, link, sha))
    for date, sname, what, link, sha in sorted(rows, key=lambda r: r[0] or "9999"):
        link_md = f"[src]({link})" if link else ""
        add(f"| {date} | {sname} | {what} | {link_md} | `{sha[:12]}` |")
    if not rows:
        add("| — | — | _no media sources run yet_ | | |")
    add("")

    # ── OSM section ────────────────────────────────────────────────────────
    om = results.get("osm", {})
    if om:
        add("## OpenStreetMap")
        add("")
        for f in om.get("findings", []):
            if f.get("kind") == "osm_building":
                tags = f.get("tags", {})
                add(f"- `{f['osm_id']}` " +
                    ", ".join(f"{k}={v}" for k, v in tags.items()))
            elif f.get("kind") == "osm_history" and f.get("tag_events"):
                add(f"- history `{f['osm_id']}`: {f['n_versions']} versions "
                    f"{str(f.get('first'))[:10]}→{str(f.get('last'))[:10]}; "
                    f"events: {json.dumps(f['tag_events'][:3], ensure_ascii=False)[:200]}")
            elif f.get("kind") == "osm_note":
                add(f"- note [{f.get('created')}]({f.get('url')}) "
                    f"{f.get('first_comment','')[:120]}")
        add("")

    # ── Telegram corpus mentions (telegram_local) ──────────────────────────
    tl = results.get("telegram_local", {})
    tl_hits = [f for f in tl.get("findings", []) if f.get("kind") == "telegram_mention"]
    if tl_hits:
        add("## Telegram corpus mentions")
        add("")
        add(f"{tl.get('summary','')}. Across all already-captured channels:")
        add("")
        for f in tl_hits[:30]:
            add(f"- [{f.get('date','')}]({f.get('url','')}) `{f['corpus']}` — {f['excerpt']}")
        add("")

    # ── notable-building metadata (wikidata / wikipedia) ───────────────────
    wd = results.get("wikidata", {})
    wd_hits = [f for f in wd.get("findings", []) if f.get("kind") in
               ("wikidata_item", "wikipedia_article")]
    if wd_hits:
        add("## Notable-building metadata (Wikidata / Wikipedia)")
        add("")
        for f in wd_hits:
            if f["kind"] == "wikidata_item":
                add(f"- Wikidata [{f.get('qid')}]({f.get('url')}) {f.get('label','')} "
                    f"({f.get('distance_km')}km)")
            else:
                add(f"- Wikipedia [{f.get('title')}]({f.get('url')}) ({f.get('distance_m')}m)")
        add("")

    # ── Wikimapia crowd descriptions ───────────────────────────────────────
    wm = results.get("wikimapia", {})
    wm_hits = [f for f in wm.get("findings", []) if f.get("kind") == "wikimapia_place"]
    if wm_hits:
        add("## Wikimapia descriptions (pre-war function — crowd-sourced, ≥2-source rule)")
        add("")
        for f in wm_hits:
            add(f"- [{f.get('title','')}]({f.get('url','')}): {f.get('description','')}")
        add("")

    # ── Visicom pre-war UA spelling + footprint ─────────────────────────────
    vc = results.get("visicom", {})
    vc_hits = [f for f in vc.get("findings", []) if f.get("kind") == "visicom_geocode_hit"]
    vc_foot = [f for f in vc.get("findings", []) if f.get("kind") == "visicom_footprint"]
    if vc_hits or vc_foot:
        add("## Visicom — pre-war Ukrainian address + building footprint")
        add("")
        seen_fids = {}
        for f in vc_hits:
            seen_fids.setdefault(f.get("feature_id", ""), f)
        for fid, f in seen_fids.items():
            add(f"- **{f.get('name','')}** (`{fid}`) — {f.get('categories','')}, "
                f"({f.get('lat')}, {f.get('lon')})")
        for f in vc_foot:
            shape = "polygon" if f.get("has_polygon") else f.get("geometry_type", "point")
            add(f"- footprint `{f.get('feature_id','')}` — {f.get('name','')}: "
                f"{shape} geometry captured")
        add("")

    # ── pre-war UA listings (candidates + verified) ────────────────────────
    rp = results.get("realestate_prewar", {})
    rp_cands = [f for f in rp.get("findings", []) if f.get("kind") == "prewar_listing_candidate"]
    if rp_cands:
        add("## Pre-war Ukrainian listings (ownership + value evidence)")
        add("")
        add("Wayback-archived dom.ria/olx/lun/mesto listing snapshots. "
            "'verified' = the snapshot's own text matched this address.")
        add("")
        for f in sorted(rp_cands, key=lambda x: not x.get("address_verified")):
            v = ("✅ verified" if f.get("address_verified") else
                 "unverified" if f.get("address_verified") is False else "not fetched")
            add(f"- [{f.get('host')} {f.get('timestamp','')[:8]}]({f.get('wayback_url')}) "
                f"— {v}" + (f" `{f['sha256'][:12]}`" if f.get("sha256") else ""))
        add("")

    # ── Google Street View coverage ────────────────────────────────────────
    gi = results.get("google_imagery", {})
    for f in gi.get("findings", []):
        if f.get("kind") == "streetview_coverage":
            add("## Google Street View coverage")
            add("")
            add(f"- status **{f.get('status')}**, capture date {f.get('date','?') or '—'} "
                f"— {f.get('note','')}")
            add("")

    # ── Google Places nearby ────────────────────────────────────────────────
    gp_hits = [f for f in gi.get("findings", []) if f.get("kind") == "google_place"]
    if gp_hits:
        add("## Google Places nearby")
        add("")
        for f in gp_hits:
            types_str = ", ".join(f.get("types", [])[:4])
            add(f"- **{f.get('name','')}** ({types_str}) — {f.get('vicinity','')}")
        add("")

    # ── YouTube candidates ──────────────────────────────────────────────────
    yt_hits = [f for f in results.get("youtube", {}).get("findings", [])
              if f.get("kind") == "youtube_candidate"]
    if yt_hits:
        add("## YouTube candidates (metadata only — not yet downloaded)")
        add("")
        for f in yt_hits:
            dur = f.get("duration")
            dur_str = f"{int(dur//60)}:{int(dur%60):02d}" if dur else "?"
            add(f"- [{f.get('title','')[:80]}]({f.get('url','')}) — "
                f"{f.get('channel','')} ({dur_str}) — query: {f.get('query','')!r}")
        add("")

    # ── Telegram channel search + global discovery ──────────────────────────
    tc_hits = [f for f in results.get("telegram_channels", {}).get("findings", [])
              if f.get("kind") == "telegram_channel_hit"]
    if tc_hits:
        add("## Telegram in-channel search hits")
        add("")
        for f in tc_hits[:30]:
            add(f"- [{f.get('date','')}]({f.get('url','')}) @{f.get('channel','')} "
                f"(query {f.get('query','')!r}) — {f.get('excerpt','')}")
        if len(tc_hits) > 30:
            add(f"- _...and {len(tc_hits)-30} more, see telegram_channels.json_")
        add("")

    tg = results.get("telegram_global", {})
    tg_disc = [f for f in tg.get("findings", []) if f.get("kind") == "telegram_discovered_channel"]
    tg_hits = [f for f in tg.get("findings", []) if f.get("kind") == "telegram_global_hit"]
    if tg_disc or tg_hits:
        add("## Telegram global search (budgeted)")
        add("")
        if tg_disc:
            add("**Newly discovered channels:**")
            for f in tg_disc:
                add(f"- [{f.get('title','')}]({f.get('url','')}) (query {f.get('query','')!r})")
            add("")
        if tg_hits:
            add("**Message hits:**")
            for f in tg_hits[:30]:
                add(f"- [{f.get('channel','')}]({f.get('url','')}) "
                    f"(query {f.get('query','')!r}) — {f.get('excerpt','')}")
            if len(tg_hits) > 30:
                add(f"- _...and {len(tg_hits)-30} more, see telegram_global.json_")
            add("")

    # ── VK photos + posts ────────────────────────────────────────────────────
    vk_res = results.get("vk", {})
    vk_posts = [f for f in vk_res.get("findings", []) if f.get("kind") == "vk_post"]
    vk_photos = [f for f in vk_res.get("findings", []) if f.get("kind") == "vk_photo"]
    if vk_posts:
        add("## VK posts mentioning the address")
        add("")
        for f in vk_posts[:20]:
            add(f"- [{f.get('date','')}]({f.get('url','')}) "
                f"(query {f.get('query','')!r}) — {f.get('text','')}")
        if len(vk_posts) > 20:
            add(f"- _...and {len(vk_posts)-20} more, see vk.json_")
        add("")
    if vk_photos:
        add(f"_{len(vk_photos)} geotagged VK photos near the point also captured "
            "— see Media & artifact timeline above / vk.json_")
        add("")

    # ── occupation resale marketplace queries ───────────────────────────────
    rs_hits = [f for f in results.get("resale", {}).get("findings", [])
              if f.get("kind") == "resale_query"]
    if rs_hits:
        add("## Occupation resale-marketplace queries")
        add("")
        add("Raw result pages captured for this address as a search term — "
            "run the resale parser (scripts/51-style) to extract listings.")
        add("")
        for f in rs_hits:
            add(f"- **{f.get('board','')}**: [captured result page]({f.get('url','')}) "
                f"`{f.get('sha256','')[:12]}`")
        add("")

    # ── manual-assist / hand-off outputs ───────────────────────────────────
    assists: list[str] = []
    for f in results.get("google_earth_kml", {}).get("findings", []):
        if f.get("kind") == "google_earth_kml":
            assists.append(f"- **Google Earth Pro**: open `{Path(f['path']).name}` "
                           "(historical-imagery time slider)")
    for f in results.get("youtube", {}).get("findings", []):
        if f.get("kind") == "youtube_next_step":
            assists.append(f"- **YouTube**: {f['note']}")
    for f in results.get("sentinel2", {}).get("findings", []):
        if f.get("kind") in ("sentinel2_handoff", "sentinel2_covered"):
            assists.append(f"- **Sentinel-2**: {f.get('note','')}")
    yandex_hotspots = [f for f in results.get("yandex_maps", {}).get("findings", [])
                      if f.get("kind") == "yandex_photo_hotspot"]
    yandex_details = [f for f in results.get("yandex_maps", {}).get("findings", [])
                      if f.get("kind") == "yandex_photo_detail"]
    if yandex_hotspots:
        assists.append(f"- **Yandex Maps photo layer**: {len(yandex_hotspots)} photo "
                       f"hotspots found near the point (existence + approx. position; "
                       f"{len(yandex_details)} with full detail pulled) — see "
                       "yandex_maps.json / manifest")
    rev = [f for f in results.get("reverse_image", {}).get("findings", [])
           if f.get("kind") == "reverse_image_pivot"]
    if rev:
        n_url = sum(1 for f in rev if f.get("mode") == "by_url")
        n_local = sum(1 for f in rev if f.get("mode") == "local_upload")
        assists.append(f"- **Reverse-image pivot**: {len(rev)} captured images "
                       f"({n_url} with by-URL Yandex/Lens/TinEye links, "
                       f"{n_local} needing manual local-file upload) — "
                       "see reverse_image.json / manifest")
    if assists:
        add("## Manual-assist & hand-offs")
        add("")
        lines.extend(assists)
        add("")

    # ── gaps ───────────────────────────────────────────────────────────────
    missing = [n for n in REGISTRY if n not in results]
    add("## Not yet swept")
    add("")
    add(", ".join(missing) if missing else "_all P0 sources present_")
    add("")

    (d / "dossier.md").write_text("\n".join(lines), encoding="utf-8")

    with (d / "manifest.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["source", "kind", "date", "name_or_title", "url", "sha256",
                    "distance_m", "extra"])
        for sname, res in results.items():
            for f in res.get("findings", []):
                w.writerow([
                    sname, f.get("kind", ""), _date_key(f),
                    (f.get("victim_name") or f.get("title") or
                     f.get("label") or f.get("osm_id") or "")[:120],
                    f.get("url") or f.get("page_url") or f.get("link") or "",
                    f.get("sha256", ""),
                    f.get("distance_m", ""),
                    (f.get("excerpt") or f.get("description") or
                     f.get("note") or "")[:200],
                ])

    print(f"dossier → {d/'dossier.md'}")
    print(f"manifest → {d/'manifest.csv'}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
