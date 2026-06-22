"""Stage 1i: capture Mariupol new-construction objects from ЕИСЖС (наш.дом.рф).

WHY THIS EXISTS
---------------
The federal ЕИСЖС registry (Единая информационная система жилищного
строительства) contains the official declaration of each new МКД under
construction in Russia, including occupied Mariupol.  For the demolish→rebuild
pipeline it provides:

  1.  Project name + developer + address of the REPLACEMENT building.
  2.  Land cadastral numbers tied to that project — the same cadastrals that
      appear in the GKO/administration land allocation decrees.
  3.  Площадь участка (land area) — cross-checks against decree area (e.g.
      3,501 m² for РКС-Девелопмент decree №291).

For the ТСЖ «Троянда-М» chain specifically:
  - РКС-Девелопмент ИНН 9310007980 holds the land parcel (decree №291, 07.09.2023)
  - Project name: «Дом с часами»
  - Land cadastrals: 93:37:0010106:91, 93:37:0010106:92, 93:37:0010107:91

API STRUCTURE (confirmed from browser DevTools, 2026-06-09)
------------------------------------------------------------
Two distinct APIs with DIFFERENT auth models:

kn/ API — developer/ЖК registry:
  Base: https://xn--80az8a.xn--d1aqf.xn--p1ai/сервисы/api/kn/
  Auth: Authorization: Basic MTpxd2U= (1:qwe — public hardcoded token)
  Key endpoints: devGk, developers, places

object/ API — individual building data:
  Base: https://xn--80az8a.xn--d1aqf.xn--p1ai/сервисы/api/object/
  Auth: SESSION COOKIES (set by navigating the catalog page in browser)
        Basic auth header must NOT be present — server returns 403 if it is.
  Warm-up: GET /сервисы/каталог-новостроек/ then /сервисы/каталог-новостроек/объект/<id>
  Key endpoints: <id>, detail/<id>, permits/<id>, documentation/<id>,
                 infrastructure/<id>, rpd/<id>, report/<id>, other/<id>,
                 construction/progress/photo/<id>

Place ID for Mariupol: 0-1158  (confirmed from browser; beyond pos 1000 in places list)
"""
from __future__ import annotations

import json
import logging
import time
from urllib.parse import urljoin, urlencode

try:
    from curl_cffi import requests
    _CURL_CFFI = True
except ImportError:
    import requests  # type: ignore[no-redef]
    import urllib3
    _CURL_CFFI = False

from .. import config, forensics

log = logging.getLogger(__name__)

if not _CURL_CFFI and not config.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ORIGIN = "https://xn--80az8a.xn--d1aqf.xn--p1ai"  # наш.дом.рф

# ЕИСЖС developer/ЖК registry API (places, developers, devGk list)
API_BASE = "/сервисы/api/kn/"

# Object-level API (confirmed from browser DevTools 2026-06-09):
# /сервисы/api/object/construction/progress/photo/71399
# Separate base from /api/kn/ — handles individual buildings (объекты)
OBJECT_API_BASE = "/сервисы/api/object/"

# Public hardcoded Basic Auth token (1:qwe base64) — not a secret
API_AUTH = "Basic MTpxd2U="

# Mariupol place ID in ЕИСЖС (from places?regionCd=93)
PLACE_ID = "0-1158"

# ДНР region code
REGION_CD = 93

# Targets for the demolish→rebuild crosswalk
TARGET_INN = "9310007980"          # РКС-Девелопмент
TARGET_PROJECT = "Дом с часами"    # project name from decree №291
TARGET_CADASTRALS = [
    "93:37:0010106:91",
    "93:37:0010106:92",
    "93:37:0010107:91",
]
# ООО СЗ «Новое время 2» — contractor named in Троянда-М ruling
TARGET_INN_2 = "9310010191"  # unverified

# Additional developer SPVs from dnr_land_orders
TARGET_INNS_SECONDARY = [
    "9303038232",   # ЭВОЛДОМ-5 (INN unverified)
]


def _new_session(*, with_basic_auth: bool = False):
    """Create a curl_cffi Chrome-impersonating session (bypasses servicepipe.ru WAF)."""
    if _CURL_CFFI:
        s = requests.Session(impersonate="chrome124")
    else:
        log.warning("curl_cffi not installed — falling back to requests (likely WAF-blocked); "
                    "install with: pip install curl_cffi")
        s = requests.Session()
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    if with_basic_auth:
        headers["Authorization"] = API_AUTH
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})
    s.headers.update(headers)
    return s


# Pre-encoded Referer paths (curl_cffi headers reject non-ASCII values)
_REFERER_KN = (
    ORIGIN + "/%D0%BD%D0%BE%D0%B2%D0%BE%D1%81%D1%82%D1%80%D0%BE%D0%B9%D0%BA%D0%B8"
    "/%D0%BC%D0%B0%D1%80%D0%B8%D1%83%D0%BF%D0%BE%D0%BB%D1%8C/"
)
# /сервисы/каталог-новостроек/
_REFERER_OBJ_BASE = (
    ORIGIN + "/%D1%81%D0%B5%D1%80%D0%B2%D0%B8%D1%81%D1%8B"
    "/%D0%BA%D0%B0%D1%82%D0%B0%D0%BB%D0%BE%D0%B3-%D0%BD%D0%BE%D0%B2%D0%BE%D1%81%D1%82%D1%80%D0%BE%D0%B5%D0%BA/"
)
# /сервисы/каталог-новостроек/объект/71399
_REFERER_OBJ_71399 = _REFERER_OBJ_BASE + "%D0%BE%D0%B1%D1%8A%D0%B5%D0%BA%D1%82/71399"

# Warm-up URLs (requests lib accepts Unicode; curl_cffi's .get() also does)
_WARM_URL_1 = ORIGIN + "/сервисы/каталог-новостроек/"
_WARM_URL_2 = ORIGIN + "/сервисы/каталог-новостроек/объект/71399"


def make_session():
    """Session for /сервисы/api/kn/ — uses Basic auth token."""
    s = _new_session(with_basic_auth=True)
    s.headers["Referer"] = _REFERER_KN
    return s


def make_object_session():
    """Session for /сервисы/api/object/ — NO Basic auth; uses session cookies.

    The object/ API returns 403 when Authorization: Basic is present.
    Cookies are set by visiting the catalog page before making API calls.
    """
    s = _new_session(with_basic_auth=False)
    s.headers["Referer"] = _REFERER_OBJ_BASE
    return s


def warm_object_session(s_obj) -> bool:
    """Visit the ЕИСЖС catalog pages to acquire session cookies for the object API.

    Must be called before any /сервисы/api/object/ requests.
    Returns True if cookies were obtained.
    """
    for url in (_WARM_URL_1, _WARM_URL_2):
        try:
            r = s_obj.get(url, timeout=(15, 30), verify=config.SSL_VERIFY)
            cookies = dict(s_obj.cookies) if hasattr(s_obj.cookies, "items") else {}
            log.info("obj-session warm %s → HTTP %d, cookies=%s",
                     url, r.status_code, list(cookies.keys()))
            time.sleep(1.5)
        except Exception as e:
            log.warning("obj-session warm failed for %s: %s", url, e)
    # Point Referer at the object page for subsequent API calls
    s_obj.headers["Referer"] = _REFERER_OBJ_71399
    cookies = dict(s_obj.cookies) if hasattr(s_obj.cookies, "items") else {}
    if not cookies:
        log.warning("obj-session warm: no cookies obtained — object API calls may fail")
        return False
    log.info("obj-session warm complete: %d cookies set", len(cookies))
    return True


def _api(path: str) -> str:
    """Build full URL for an API endpoint."""
    return ORIGIN + API_BASE + path.lstrip("/")


def _polite_sleep() -> None:
    time.sleep(2.0)


def _get(s: requests.Session, url: str, params: dict | None = None):
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            r = s.get(url, params=params, timeout=(15, config.TIMEOUT),
                      verify=config.SSL_VERIFY)
            if r.status_code not in (200, 404):
                log.warning("HTTP %d from %s — body: %s",
                            r.status_code, url, r.text[:200])
            return r
        except requests.RequestException as e:
            wait = min(60, 2 ** attempt)
            log.warning("GET %s failed (attempt %d/%d): %s; wait %ds",
                        url, attempt, config.MAX_RETRIES, e, wait)
            time.sleep(wait)
    log.error("giving up on %s", url)
    return None


def _capture(con, r, url: str, source_type: str, title: str, description: str) -> str:
    return forensics.capture_source(
        r.content, url=url,
        source_type=source_type, title=title, description=description,
        content_type=r.headers.get("Content-Type", "application/json"),
        http_status=r.status_code, con=con,
    )


def _json_list(r) -> list[dict]:
    """Parse response as JSON; return list regardless of envelope shape.

    Handles both flat {"data": [...]} and nested {"data": {"list": [...], "total": N}}
    which is the actual ЕИСЖС envelope shape (confirmed from browser DevTools).
    """
    try:
        data = r.json()
    except ValueError:
        return []
    if isinstance(data, list):
        return data
    for key in ("data", "items", "result", "content"):
        val = data.get(key) if isinstance(data, dict) else None
        if isinstance(val, list):
            return val
        if isinstance(val, dict):
            for inner in ("list", "items", "content"):
                v = val.get(inner)
                if isinstance(v, list):
                    return v
    return []


def capture_gk_list(s, con, offset: int = 0, limit: int = 30) -> list[dict]:
    """Capture one page of ЖК (residential complexes) for Mariupol."""
    url = _api("devGk")
    params = {
        "place": PLACE_ID,
        "status[]": "allFlg",
        "offset": offset,
        "limit": limit,
        "sortType": "asc",
    }
    r = _get(s, url, params=params)
    _polite_sleep()
    if r is None or r.status_code != 200:
        log.warning("devGk offset=%d failed", offset)
        return []
    full_url = r.url
    _capture(con, r, full_url, "eisghs_gk_list",
             f"ЕИСЖС Mariupol ЖК list offset={offset}",
             f"List of residential complexes (ЖК) in Mariupol (place {PLACE_ID}), "
             f"offset {offset}. Includes project name, developer, address, status.")
    return _json_list(r)


def capture_developers_list(s, con) -> list[dict]:
    """Capture list of developers active in Mariupol."""
    url = _api("developers")
    params = {
        "place": PLACE_ID,
        "status[]": "allFlg",
        "offset": 0,
        "limit": 100,
        "sortType": "asc",
        "sortField": "devShortCleanNm",
    }
    r = _get(s, url, params=params)
    _polite_sleep()
    if r is None or r.status_code != 200:
        log.warning("developers list failed")
        return []
    _capture(con, r, r.url, "eisghs_developers_list",
             "ЕИСЖС Mariupol developers list",
             "All developers with active projects in Mariupol (place 0-1158). "
             "Cross-reference ИНН against РКС-Девелопмент 9310007980.")
    return _json_list(r)


def _obj_api(path: str) -> str:
    """Build full URL for an object-level API endpoint."""
    return ORIGIN + OBJECT_API_BASE + path.lstrip("/")


def capture_mariupol_objects(s_obj, con) -> list[dict]:
    """Capture all building objects in Mariupol via the object API.

    The /api/object/list endpoint uses addrAreaId (plain integer, not the 0-1158 kn/ form).
    Confirmed from object 71399 detail: addrAreaId=1158.
    Also tries companyGroupId per ЖК if area-level search fails.
    """
    key = "eisghs_mariupol_objects_area"
    if forensics.is_done(con, key):
        log.info("Mariupol object list already captured")
        return []

    # Area-level probes — try different parameter names for addrAreaId
    area_id = "1158"  # confirmed from object 71399 detail (addrAreaId field)
    area_probes = [
        {"addrAreaId": area_id, "offset": 0, "limit": 100},
        {"areaId": area_id, "offset": 0, "limit": 100},
        {"place": PLACE_ID, "offset": 0, "limit": 100},         # kn-style place id
        {"place": area_id, "offset": 0, "limit": 100},          # plain integer form
        {"region": REGION_CD, "offset": 0, "limit": 100},
        {"regionCd": REGION_CD, "offset": 0, "limit": 100},
    ]
    url = _obj_api("list")
    for params in area_probes:
        r = _get(s_obj, url, params=params)
        _polite_sleep()
        status = r.status_code if r else "None"
        size = len(r.content) if r else 0
        log.info("obj-area probe params=%s → HTTP %s, %d bytes", params, status, size)
        if r is None or r.status_code != 200:
            if r is not None and r.status_code not in (400, 404):
                log.info("  raw: %s", r.text[:300])
            continue
        items = _json_list(r)
        if not items:
            log.info("  200 but empty; raw: %s", r.text[:300])
            continue
        _capture(con, r, r.url, "eisghs_objects_by_area",
                 f"ЕИСЖС all objects in Mariupol (addrAreaId={area_id})",
                 "All МКД construction objects in Mariupol returned by object API. "
                 "Each item: object ID, address, developer, ЖК group ID, status.")
        forensics.mark_done(con, key)
        log.info("area-level capture: %d objects in Mariupol", len(items))
        return items

    log.warning("area-level object enumeration failed — falling back to per-ЖК probes")
    return []


def capture_gk_houses(s_obj, con, gk_id: str | int, gk_name: str) -> list[dict]:
    """Capture list of individual buildings (объекты) for one ЖК.

    Uses /сервисы/api/object/ base (confirmed 2026-06-09 from browser DevTools).
    s_obj must be a cookie-warmed session (make_object_session + warm_object_session).
    The correct ЖК parameter in the object API is companyGroupId (from object 71399
    detail: companyGroupId=5731), not gkId.
    """
    key = f"eisghs_houses::{gk_id}"
    if forensics.is_done(con, key):
        log.debug("houses for gk %s already captured", gk_id)
        return []
    for path, params in (
        # companyGroupId confirmed from object 71399 detail field
        ("list", {"companyGroupId": gk_id, "offset": 0, "limit": 100}),
        ("list", {"groupId": gk_id, "offset": 0, "limit": 100}),
        ("list", {"gkId": gk_id, "offset": 0, "limit": 100}),
        ("list", {"devGkId": gk_id, "offset": 0, "limit": 100}),
    ):
        url = _obj_api(path)
        r = _get(s_obj, url, params=params)
        _polite_sleep()
        log.info("obj-list probe gk=%s params=%s → HTTP %s, %d bytes",
                 gk_id, list(params.keys())[0], r.status_code if r else "None",
                 len(r.content) if r else 0)
        if r is None or r.status_code != 200:
            if r is not None and r.status_code not in (400, 404):
                log.info("  raw: %s", r.text[:200])
            continue
        items = _json_list(r)
        if not items:
            log.info("  200 but empty; raw: %s", r.text[:200])
            continue
        _capture(con, r, r.url, "eisghs_houses_list",
                 f"ЕИСЖС object list for ЖК '{gk_name}' (id={gk_id})",
                 f"Individual buildings (объекты) within ЖК '{gk_name}'. "
                 "Contains postal addresses and building metadata.")
        forensics.mark_done(con, key)
        log.info("  captured %d objects for ЖК %s '%s'", len(items), gk_id, gk_name)
        return items
    log.warning("no object list found for ЖК %s", gk_id)
    return []


def capture_house_detail(s_obj, con, house_id: str | int, gk_name: str) -> dict | None:
    """Capture detail and sub-resources for one building (объект).

    s_obj must be a cookie-warmed session (make_object_session + warm_object_session).
    Sub-endpoints confirmed from browser DevTools 2026-06-09.
    """
    key = f"eisghs_house::{house_id}"
    if forensics.is_done(con, key):
        log.debug("house %s already captured", house_id)
        return None

    captured_any = False
    result = None

    for path in (str(house_id), f"detail/{house_id}", f"info/{house_id}"):
        url = _obj_api(path)
        r = _get(s_obj, url)
        _polite_sleep()
        log.info("obj-detail probe id=%s path='%s' → HTTP %s, %d bytes",
                 house_id, path, r.status_code if r else "None",
                 len(r.content) if r else 0)
        if r is None or r.status_code != 200:
            continue
        _capture(con, r, r.url, "eisghs_house_detail",
                 f"ЕИСЖС object detail — {gk_name} id={house_id}",
                 f"Main detail record for building id={house_id} in ЖК '{gk_name}'.")
        captured_any = True
        try:
            result = r.json()
        except ValueError:
            pass
        break

    sub_endpoints = [
        ("permits", f"permits/{house_id}", "permits (разрешение на строительство)"),
        ("documentation", f"documentation/{house_id}", "project documentation (ПД/РД)"),
        ("infrastructure", f"infrastructure/{house_id}", "infrastructure obligations"),
        ("rpd", f"rpd/{house_id}", "расчёт платежей"),
        ("report", f"report/{house_id}", "строительный отчёт"),
        ("other", f"other/{house_id}", "other documents"),
    ]
    for sub_type, sub_path, desc in sub_endpoints:
        url = _obj_api(sub_path)
        r = _get(s_obj, url)
        _polite_sleep()
        if r is None or r.status_code != 200:
            log.info("  sub %s → HTTP %s, %d bytes: %s",
                     sub_path, r.status_code if r else "None",
                     len(r.content) if r else 0,
                     r.text[:150] if r else "")
            continue
        _capture(con, r, r.url, f"eisghs_house_{sub_type}",
                 f"ЕИСЖС {desc} — {gk_name} id={house_id}",
                 f"{desc.capitalize()} for building id={house_id} in ЖК '{gk_name}'.")
        log.info("  captured sub-resource: %s (%d bytes)", sub_type, len(r.content))
        captured_any = True

    # Capture linked PDFs from the detail response
    if result and isinstance(result.get("data"), dict):
        d = result["data"]

        # RPD declaration PDF
        rpd_url = d.get("rpdPdfLink")
        if rpd_url and not forensics.is_done(con, f"eisghs_rpd_pdf::{house_id}"):
            r = _get(s_obj, rpd_url)
            _polite_sleep()
            if r is not None and r.status_code == 200:
                _capture(con, r, rpd_url, "eisghs_rpd_pdf",
                         f"ЕИСЖС RPD declaration PDF — {gk_name} id={house_id}",
                         "Разрешение на проектирование (RPD) PDF declaration "
                         f"for building id={house_id} in ЖК '{gk_name}'.")
                forensics.mark_done(con, f"eisghs_rpd_pdf::{house_id}")
                log.info("  captured RPD PDF (%d bytes)", len(r.content))
            else:
                log.info("  RPD PDF → HTTP %s", r.status_code if r else "None")

        # РнВ (разрешение на ввод в эксплуатацию) — commissioning permits
        for rnv in d.get("rnvDTO") or []:
            rnv_url = rnv.get("fileUrl")
            rnv_num = rnv.get("docObjRnvNum", "")
            rnv_dt = rnv.get("docObjRnvDt", "")
            if not rnv_url:
                continue
            rnv_key = f"eisghs_rnv::{house_id}::{rnv_num}"
            if forensics.is_done(con, rnv_key):
                continue
            r = _get(s_obj, rnv_url)
            _polite_sleep()
            if r is not None and r.status_code == 200:
                _capture(con, r, rnv_url, "eisghs_rnv_pdf",
                         f"ЕИСЖС РнВ (commissioning permit) — {gk_name} id={house_id} №{rnv_num}",
                         f"Разрешение на ввод в эксплуатацию №{rnv_num} dated {rnv_dt} "
                         f"for building id={house_id} '{gk_name}'. "
                         "Final link in seizure→demolish→build→commission chain.")
                forensics.mark_done(con, rnv_key)
                log.info("  captured РнВ PDF №%s (%d bytes)", rnv_num, len(r.content))
            else:
                log.info("  РнВ PDF %s → HTTP %s", rnv_num, r.status_code if r else "None")

    # Scrape the object's own SSR page — different structure from ЖК pages.
    # pageProps contains object-specific data (PD, cadastrals, permits) not pageProps.houses.
    pd_key = f"eisghs_obj_page::{house_id}"
    if not forensics.is_done(con, pd_key):
        obj_page_url = ORIGIN + f"/сервисы/каталог-новостроек/объект/{house_id}"
        r = _get(s_obj, obj_page_url)
        _polite_sleep()
        if r is not None and r.status_code == 200:
            _capture(con, r, r.url, "eisghs_obj_page",
                     f"ЕИСЖС object SSR page — {gk_name} id={house_id}",
                     f"Next.js SSR page for building {house_id} '{gk_name}'. "
                     "pageProps contains PD, cadastrals, permits, construction progress.")
            forensics.mark_done(con, pd_key)
            captured_any = True
            log.info("  captured object SSR page (%d bytes)", len(r.content))
        else:
            log.info("  object SSR page → HTTP %s", r.status_code if r else "None")

    if captured_any:
        forensics.mark_done(con, key)
    else:
        log.warning("object %s: no endpoints responded", house_id)
    return result


def run_by_ids(ids: list[str]) -> None:
    """Capture full detail (+ sub-resources, PDFs, SSR page) for an explicit
    list of object IDs harvested manually from the catalog map/cards.

    The kn/devGk pagination (place=0-1158) only surfaces 5 ЖК / 20 objects,
    far short of the 91 listings shown on the public "Новостройки в
    Мариуполе" catalog page. Each card/pin on that page links to
    /сервисы/каталог-новостроек/объект/<5-digit-id> -- this function takes
    those IDs directly and reuses the same capture_house_detail() path as
    the full run(), so output is fully compatible with
    scripts/18_parse_eisghs_mariupol.py.
    """
    con = forensics.open_state()
    s_obj = make_object_session()
    warm_object_session(s_obj)

    log.info("capturing detail for %d object IDs", len(ids))
    n_captured = 0
    for house_id in ids:
        house_id = str(house_id).strip()
        if not house_id:
            continue
        if forensics.is_done(con, f"eisghs_house::{house_id}"):
            log.info("object %s already captured, skipping", house_id)
            continue
        result = capture_house_detail(s_obj, con, house_id, gk_name="manual_catalog")
        if result is not None:
            n_captured += 1
    log.info("done: %d/%d objects newly captured", n_captured, len(ids))


def _parse_nextdata_houses(html: str) -> list[dict]:
    """Extract props.pageProps.houses from a Next.js SSR HTML page."""
    import re as _re
    m = _re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html, _re.DOTALL)
    if not m:
        return []
    try:
        nd = json.loads(m.group(1))
    except ValueError:
        return []
    # Confirmed structure: props.pageProps.houses[]{objId, objAddr, developer, ...}
    houses = nd.get("props", {}).get("pageProps", {}).get("houses", [])
    if houses:
        return houses
    # Fallback: find any list whose first item has objId
    def _walk(obj, depth=0):
        if depth > 8:
            return []
        if isinstance(obj, list) and obj and isinstance(obj[0], dict) and "objId" in obj[0]:
            return obj
        items = obj.values() if isinstance(obj, dict) else (obj if isinstance(obj, list) else [])
        for v in items:
            result = _walk(v, depth + 1)
            if result:
                return result
        return []
    return _walk(nd.get("props", {}))


def capture_gk_nextdata(s_obj, con, gk_id: str | int, gk_name: str) -> list[dict]:
    """Extract building list from the ЖК SSR page via __NEXT_DATA__.

    Confirmed working URL: /сервисы/новостройки/мариуполь/жк/{gk_id}
    Returns houses list; each item has objId, objAddr, developer.devInn, etc.
    First re-parses any already-captured raw page before fetching from network.
    """
    key = f"eisghs_gk_nextdata::{gk_id}"
    if forensics.is_done(con, key):
        log.debug("gk %s __NEXT_DATA__ already parsed", gk_id)
        return []

    # Re-parse from already-captured raw page (avoids re-fetching)
    existing = con.execute(
        "SELECT raw_path FROM source_document "
        "WHERE source_type='eisghs_gk_page' AND title LIKE ? "
        "ORDER BY captured_at DESC LIMIT 1",
        (f"%id={gk_id}%",)
    ).fetchone()
    if existing and existing[0]:
        from pathlib import Path as _Path
        try:
            html = _Path(existing[0]).read_bytes().decode("utf-8", errors="replace")
            houses = _parse_nextdata_houses(html)
            if houses:
                forensics.mark_done(con, key)
                log.info("gk %s: parsed %d objects from cached page", gk_id, len(houses))
                return houses
            log.info("gk %s: cached page has no houses — will re-fetch", gk_id)
        except Exception as e:
            log.warning("gk %s: cached page read error: %s", gk_id, e)

    # Fetch from network — confirmed working path from previous run
    url = ORIGIN + f"/сервисы/новостройки/мариуполь/жк/{gk_id}"
    r = _get(s_obj, url)
    _polite_sleep()
    if r is None or r.status_code != 200:
        log.warning("gk-page %s → HTTP %s", gk_id, r.status_code if r else "None")
        return []
    _capture(con, r, r.url, "eisghs_gk_page",
             f"ЕИСЖС ЖК page — {gk_name} (id={gk_id})",
             f"SSR /новостройки page for ЖК '{gk_name}' (id={gk_id}). "
             "props.pageProps.houses[] contains building IDs, addresses, developer ИНН.")
    houses = _parse_nextdata_houses(r.text)
    forensics.mark_done(con, key)
    log.info("gk-page %s → %d objects", gk_id, len(houses))
    return houses


def capture_gk_detail(s, con, gk_id: str | int, name: str) -> dict | None:
    """Capture full detail for one ЖК by its ЕИСЖС ID."""
    key = f"eisghs_gk::{gk_id}"
    if forensics.is_done(con, key):
        log.debug("gk %s already captured", gk_id)
        return None
    url = _api(f"devGk/{gk_id}")
    r = _get(s, url)
    _polite_sleep()
    if r is None or r.status_code != 200:
        log.warning("gk detail %s failed — HTTP %s body: %s",
                    gk_id, r.status_code if r else "None",
                    r.text[:200] if r else "")
        return None
    _capture(con, r, r.url, "eisghs_gk_detail",
             f"ЕИСЖС ЖК detail — {name} (id={gk_id})",
             f"Full detail for ЖК '{name}' (ЕИСЖС id {gk_id}). "
             "Contains postal address, developer ИНН, cadastral numbers, "
             "land area, completion dates, building count.")
    forensics.mark_done(con, key)
    try:
        return r.json()
    except ValueError:
        return None


def _flatten_places(data) -> list[dict]:
    """Extract a flat list of place dicts from whatever envelope shape is returned."""
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("data", "items", "result", "content", "list"):
        v = data.get(key)
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            for inner_key in ("list", "items", "content"):
                inner = v.get(inner_key)
                if isinstance(inner, list):
                    return inner
    return []


_OCCUPIED_TERMS = ("мариупол", "жданов", "луганск", "донецк", "херсон", "мелитопол",
                   "бердянск", "запорож", "днр", "лнр", "новороссия")


def _search_places_for_mariupol(places: list[dict]) -> str | None:
    """Search a places list for Mariupol or any occupied-territory entry."""
    hits = []
    for p in places:
        pid = str(p.get("id") or "")
        name = str(p.get("name") or p.get("placeName") or p.get("cityName") or "")
        nl = name.lower()
        if any(t in nl for t in _OCCUPIED_TERMS):
            log.info("  occupied-territory match: id=%s name=%s", pid, name)
            hits.append((pid, name))
    if hits:
        for pid, name in hits:
            if "мариупол" in name.lower() or "жданов" in name.lower():
                log.info("  *** Mariupol place found: id=%s name=%s", pid, name)
                return pid
    return None


def _find_place_id(s, con) -> str | None:
    """Try multiple strategies to find Mariupol's place ID in ЕИСЖС."""
    url = _api("places")

    # Strategy 1–3: paginate with regionCd=93, try no filter, try text search
    attempts = [
        {"regionCd": REGION_CD, "offset": 0, "limit": 1000},
        {"offset": 0, "limit": 1000},
        {"search": "Мариуполь"},
        {"q": "Мариуполь"},
        {"name": "Мариуполь"},
    ]
    for params in attempts:
        r = _get(s, url, params=params)
        _polite_sleep()
        log.info("places probe params=%s → HTTP %s, %d bytes",
                 params, r.status_code if r else "None",
                 len(r.content) if r else 0)
        if r is None or r.status_code != 200:
            continue
        _capture(con, r, r.url, "eisghs_places_list",
                 f"ЕИСЖС places list probe (params={params})",
                 "Used to discover Mariupol's correct place ID in ЕИСЖС.")
        try:
            data = r.json()
        except ValueError:
            log.warning("places: non-JSON response body: %s", r.text[:200])
            continue

        places = _flatten_places(data)
        log.info("  parsed %d place entries; raw keys: %s",
                 len(places), list(data.keys()) if isinstance(data, dict) else type(data).__name__)

        if not places:
            # Dump raw for inspection (first 500 chars)
            log.info("  raw response: %s", r.text[:500])
            continue

        pid = _search_places_for_mariupol(places)
        if pid:
            return pid

        log.info("  Mariupol not found; sample entries:")
        for p in places[:20]:
            log.info("    %s", p)
        if len(places) > 20:
            log.info("    ... (%d more)", len(places) - 20)

    log.error("Could not find Mariupol place ID after all strategies")
    return None


def _check_api(s) -> bool:
    """Quick probe to confirm the API is accessible with current credentials."""
    url = _api("places")
    params = {"regionCd": REGION_CD}
    r = _get(s, url, params=params)
    if r is None:
        log.error("API probe failed — no response")
        return False
    if r.status_code == 200:
        log.info("API probe OK — HTTP 200, %d bytes", len(r.content))
        return True
    log.error("API probe HTTP %d: %s", r.status_code, r.text[:200])
    return False


def run() -> None:
    global PLACE_ID
    con = forensics.open_state()

    # Two separate sessions: Basic auth for kn/ API, cookie-based for object/ API.
    s_kn = make_session()
    s_obj = make_object_session()

    if not _check_api(s_kn):
        return

    log.info("Using confirmed place ID: %s", PLACE_ID)

    # Warm the object session before any /api/object/ calls.
    # This visits the catalog page so the server sets session cookies.
    # Without cookies the object/ API returns 403 (Basic auth not accepted there).
    warm_object_session(s_obj)

    # Clear object-API done-flags so all object/ endpoints are retried.
    # kn/ done-flags (developers, gk_list) are left intact.
    deleted = con.execute(
        "DELETE FROM done WHERE key LIKE 'eisghs_houses::%' "
        "   OR key LIKE 'eisghs_house::%' "
        "   OR key LIKE 'eisghs_mariupol_objects%' "
        "   OR key LIKE 'eisghs_rpd_pdf::%' "
        "   OR key LIKE 'eisghs_gk_nextdata::%' "
        "   OR key LIKE 'eisghs_rnv::%' "
        "   OR key LIKE 'eisghs_obj_page::%'"
    ).rowcount
    con.commit()
    log.info("cleared %d object-API done-flags for fresh retry", deleted)

    # ── 1. Capture developers list (cross-reference ИНН) ─────────────────────
    devs = capture_developers_list(s_kn, con)
    log.info("developers in Mariupol: %d", len(devs))
    for d in devs:
        inn = str(d.get("inn") or d.get("devInn") or "")
        name = d.get("name") or d.get("shortNm") or d.get("devShortCleanNm") or ""
        dev_id = d.get("id") or d.get("devId") or ""
        gk_id = d.get("devGkId") or d.get("gkId") or None
        if inn in (TARGET_INN, TARGET_INN_2) or inn in TARGET_INNS_SECONDARY:
            if gk_id:
                log.info("  TARGET developer: %s ИНН=%s internal_id=%s → ЖК id=%s",
                         name, inn, dev_id, gk_id)
            else:
                log.warning("  TARGET developer %s ИНН=%s internal_id=%s "
                            "— NO ЖК registered in ЕИСЖС (проектная декларация not filed)",
                            name, inn, dev_id)

    # ── 2. Paginate through all Mariupol ЖК ──────────────────────────────────
    all_gk: list[dict] = []
    offset = 0
    limit = 30
    while True:
        page = capture_gk_list(s_kn, con, offset=offset, limit=limit)
        if not page:
            break
        all_gk.extend(page)
        log.info("ЖК page offset=%d: %d results (total %d)", offset, len(page), len(all_gk))
        if len(page) < limit:
            break
        offset += limit
    log.info("total ЖК in Mariupol: %d", len(all_gk))

    # ── 3a. Try area-level object enumeration first ───────────────────────────
    # addrAreaId=1158 confirmed from object 71399 detail response.
    all_objects = capture_mariupol_objects(s_obj, con)
    for obj in all_objects:
        obj_id = obj.get("id") or obj.get("objId") or ""
        addr = obj.get("address") or obj.get("addr") or ""
        gk_name = obj.get("nameObj") or obj.get("name") or ""
        log.info("  area object id=%s name='%s' addr=%s", obj_id, gk_name, addr)
        if obj_id:
            capture_house_detail(s_obj, con, obj_id, gk_name)

    # ── 3b. Per-ЖК enumeration (fallback: __NEXT_DATA__ scraping) ────────────
    for gk in all_gk:
        gk_id = str(gk.get("id") or gk.get("gkId") or "")
        name = gk.get("name") or gk.get("gkName") or gk.get("shortNm") or ""
        log.info("  ЖК: id=%s name='%s'", gk_id, name)
        if not gk_id:
            continue

        # Try __NEXT_DATA__ scraping from SSR ЖК page
        houses = capture_gk_nextdata(s_obj, con, gk_id, name)
        if not houses:
            # Fall back to object API list probes (companyGroupId etc.)
            houses = capture_gk_houses(s_obj, con, gk_id, name)

        for h in houses:
            h_id = h.get("id") or h.get("houseId") or h.get("objId") or ""
            addr = (h.get("address") or h.get("addr") or h.get("fullAddress") or "")
            log.info("    object id=%s addr=%s", h_id, addr)
            if h_id:
                capture_house_detail(s_obj, con, h_id, name)

    # ── 4. Capture known object 71399 and its sub-resources ──────────────────
    log.info("capturing known object 71399 (ЖК Нахимовский 2 очередь / КОРПОРАЦИЯ СМУ-5)")
    capture_house_detail(s_obj, con, 71399, "ЖК Нахимовский 2 очередь")

    n = con.execute(
        "SELECT COUNT(*) FROM source_document WHERE source_type LIKE 'eisghs_%'"
    ).fetchone()[0]
    log.info("done — %d ЕИСЖС artifacts in store", n)
