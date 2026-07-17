"""Source 15 — VK photos + posts near / mentioning the address.

VK is likely the richest siege-era photo source after Telegram: local
community groups, resident albums, and comment threads. Two queries:
  * photos.search — geotagged photos within a radius of the point.
  * newsfeed.search — posts mentioning an address variant.
Needs a VK user access token (config.VK_ACCESS_TOKEN). VK is Russian
infrastructure → RUN=V: the user runs this from their Russia-routed VPS;
Claude never executes it. Skips cleanly if no token.

Noise, confirmed by manual review 2026-07-16 (pid=4837): both queries
return a lot of irrelevant results.
  * photos.search's `lat`/`long`/`radius` params do NOT reliably scope
    results to true geotagged photos near the point — VK's photo-geo
    index is sparse, so the API backfills with popularity-ranked photos
    that may carry no geo tag at all, including photos from other cities.
    Fixed by post-filtering: keep a photo only if it carries its own
    `lat`/`long` AND that point is within radius_m (x2 tolerance) of the
    bundle's point; everything else (untagged or off-radius) is dropped
    rather than surfaced as a false geo match.
  * newsfeed.search's `latitude`/`longitude` params are similarly weak —
    confirmed it surfaces posts mentioning the same street name (e.g.
    "Зелинского") in OTHER cities entirely. Fixed by appending "Мариуполь"
    to the query text itself (text search, not geo, is what actually
    scopes this API), and dropping results whose text doesn't mention
    Мариуполь/Мариуполя anywhere.
  * Neither fix is perfect — this is API-quality noise, not a bug in our
    code, so always spot-check `vk_post`/`vk_photo` findings manually
    before citing one. A missed genuinely-relevant post (e.g. one using
    an address abbreviation without "Мариуполь" in the same post) is a
    known false-negative risk of the newsfeed filter; if the automated
    search misses something, scripts/330_capture_vk_post.py captures a
    specific post by URL once you've found it by hand.

  * Second noise pattern found 2026-07-16 after the "Мариуполь" fix above:
    VK's text search matches the STREET NAME as a substring, ignoring the
    house number — so a query for "ул. Зелинского 17а" surfaces posts
    about Зелинского 33, Зелинского 45, or generic "Мариуполь" city-news
    posts that merely mention the street in passing, not this specific
    building. Fixed by reusing variants.match_regexes(bundle) — the same
    street-stem + house-number regex (with RU/UA letter-drift folding)
    already used by local_evidence.py's chat-corpus grep — as a second,
    stricter filter on top of the "Мариуполь" substring check.
"""
from __future__ import annotations

import logging
import time

import requests

from ... import config, forensics
from ..variants import match_regexes
from .base import SourceResult, http_headers, haversine_m

log = logging.getLogger(__name__)

NAME = "vk"
RUN = "V"
NETWORK = True
DESCRIPTION = "VK photos.search (geo) + newsfeed.search (address) — VPS, token-gated"

API = "https://api.vk.com/method/{method}"
API_VERSION = "5.199"
MAX_PHOTOS = 30
PAUSE = 0.35


def plan(bundle) -> str:
    if not config.VK_ACCESS_TOKEN:
        return "SKIP — no VK_ACCESS_TOKEN in .env"
    return "photos.search (geo radius) + newsfeed.search (top variants), capture images"


def _call(method: str, **params) -> dict | None:
    params.update({"access_token": config.VK_ACCESS_TOKEN, "v": API_VERSION})
    try:
        r = requests.get(API.format(method=method), params=params,
                         headers=http_headers(), timeout=40)
        r.raise_for_status()
        j = r.json()
        if "error" in j:
            log.warning("VK %s error: %s", method, j["error"].get("error_msg"))
            return None
        return j.get("response")
    except requests.RequestException as e:
        log.warning("VK %s request failed: %s", method, e)
        return None


def fetch(bundle, con, radius_m: float = 150.0) -> SourceResult:
    if not config.VK_ACCESS_TOKEN:
        return SourceResult(NAME, True, "skipped — no VK_ACCESS_TOKEN set (VPS-only source)")

    findings: list[dict] = []
    captured: list[str] = []

    # ── photos.search (geo) ────────────────────────────────────────────────
    # VK radius is one of {10,100,800,6000,50000} m — pick the smallest ≥ ask
    vk_radius = next(r for r in (10, 100, 800, 6000, 50000) if r >= radius_m)
    resp = _call("photos.search", lat=bundle.lat, long=bundle.lon,
                 radius=vk_radius, count=MAX_PHOTOS, sort=0)
    n_dropped_untagged = n_dropped_offradius = 0
    if resp:
        for item in resp.get("items", []):
            # VK's geo filter is unreliable (see module docstring) — verify
            # the photo actually carries a matching geo tag before trusting
            # it as a real "near this address" result.
            plat, plon = item.get("lat"), item.get("long")
            if plat is None or plon is None:
                n_dropped_untagged += 1
                continue
            dist = haversine_m(bundle.lat, bundle.lon, plat, plon)
            if dist > radius_m * 2:
                n_dropped_offradius += 1
                continue
            sizes = item.get("sizes", [])
            best = max(sizes, key=lambda s: s.get("width", 0), default={})
            rec = {
                "kind": "vk_photo", "id": f"{item.get('owner_id')}_{item.get('id')}",
                "text": (item.get("text") or "")[:200],
                "date": _fmt(item.get("date")),
                "url": f"https://vk.com/photo{item.get('owner_id')}_{item.get('id')}",
            }
            if best.get("url"):
                try:
                    ir = requests.get(best["url"], headers=http_headers(), timeout=60)
                    if ir.status_code == 200 and ir.content:
                        sha = forensics.capture_source(
                            ir.content, url=best["url"],
                            source_type="osint_vk_photo",
                            title=f"vk photo {rec['id']}",
                            description=(f"VK geo photo near pid={bundle.pid}, "
                                         f"{rec['date']}. {rec['url']}"),
                            content_type=ir.headers.get("Content-Type", "image/jpeg"),
                            http_status=ir.status_code, con=con,
                        )
                        rec["sha256"] = sha
                        captured.append(sha)
                        time.sleep(PAUSE)
                except requests.RequestException:
                    log.debug("vk photo fetch failed", exc_info=True)
            findings.append(rec)

    # ── newsfeed.search (top address variants) ─────────────────────────────
    # Append "Мариуполь" to the query text itself — VK's latitude/longitude
    # params on this endpoint don't reliably scope results (confirmed:
    # surfaces same-street-name posts from other cities), but text search
    # does actually filter on its query string. Second filter (see module
    # docstring): VK's text search matches the street name as a bare
    # substring, ignoring the house number, so a real street+house regex
    # (same one local_evidence.py's chat-corpus grep uses) is required too.
    house_regexes = match_regexes(bundle)
    n_dropped_no_city = 0
    n_dropped_wrong_house = 0
    seen_post_ids: set[str] = set()
    for v in [x for x in bundle.variants if x.kind == "typed"][:3]:
        resp = _call("newsfeed.search", q=f"{v.text} Мариуполь", count=20,
                     latitude=bundle.lat, longitude=bundle.lon)
        if not resp:
            continue
        for item in resp.get("items", []):
            text = item.get("text") or ""
            if "мариупол" not in text.lower():
                n_dropped_no_city += 1
                continue
            if house_regexes and not any(rx.search(text) for rx in house_regexes):
                n_dropped_wrong_house += 1
                continue
            oid, pid_ = item.get("owner_id"), item.get("id")
            post_id = f"{oid}_{pid_}"
            if post_id in seen_post_ids:
                continue  # same post surfaced by >1 query variant
            seen_post_ids.add(post_id)
            findings.append({
                "kind": "vk_post", "query": v.text,
                "date": _fmt(item.get("date")),
                "text": (item.get("text") or "")[:250].replace("\n", " | "),
                "url": f"https://vk.com/wall{oid}_{pid_}",
            })
        time.sleep(PAUSE)

    n_ph = sum(1 for f in findings if f["kind"] == "vk_photo")
    n_po = sum(1 for f in findings if f["kind"] == "vk_post")
    findings.append({"kind": "vk_filter_summary",
                     "dropped_untagged_photos": n_dropped_untagged,
                     "dropped_offradius_photos": n_dropped_offradius,
                     "dropped_no_city_posts": n_dropped_no_city,
                     "dropped_wrong_house_posts": n_dropped_wrong_house})
    return SourceResult(NAME, True,
                        f"{n_ph} VK photos, {n_po} VK posts "
                        f"(dropped {n_dropped_untagged} untagged + "
                        f"{n_dropped_offradius} off-radius photos, "
                        f"{n_dropped_no_city} no-city-mention + "
                        f"{n_dropped_wrong_house} wrong-house posts as noise)",
                        findings, captured)


def _fmt(epoch) -> str:
    if not epoch:
        return ""
    import datetime as _dt
    return _dt.datetime.utcfromtimestamp(epoch).strftime("%Y-%m-%d")
