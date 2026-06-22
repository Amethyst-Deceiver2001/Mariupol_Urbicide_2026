"""Central configuration. No hardcoded paths anywhere else in the project."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parents[2]))
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
STATE_DB = DATA_DIR / "state.sqlite"

# Geoblocked access: required for the court portals. Set in .env.
PROXY = os.environ.get("COURT_PROXY", "")

# OSM Nominatim usage policy requires an identifying contact in the User-Agent
# (email or project URL) -- set in .env. Used by scripts/22_geocode_addresses.py.
GEOCODE_CONTACT = os.environ.get("GEOCODE_CONTACT", "")

# Google Geocoding API key (Tier A3 fallback for buildings Nominatim/Overpass
# can't resolve). Set in .env -- requires a GCP project with the Geocoding
# API enabled. Used by scripts/24_geocode_google.py.
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")

# Russian Gosuslugi / DNR court portals use certificates from the Russian
# national CA (Минцифры), which is not in standard trust stores outside Russia.
# SSL_VERIFY=False disables certificate validation for all crawl requests.
# Set SSL_VERIFY=true in .env only if you have installed the Russian CA bundle.
SSL_VERIFY: bool = os.environ.get("SSL_VERIFY", "false").lower() == "true"

# Postgres/PostGIS
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://localhost:5432/mariupol_seizures"
)

# ── Telegram (MTProto) — demand-side resale scan (scripts/50) ──────────────────
# Reading public channel history needs an api_id/api_hash from my.telegram.org.
# Set in .env. The session file persists the login so re-runs are non-interactive
# after the first (the first run prompts for the SMS/app login code). The session
# holds an auth token → treat as a secret; it lives under data/ (gitignored).
TELEGRAM_API_ID = int(os.environ.get("TELEGRAM_API_ID", "0") or "0")
TELEGRAM_API_HASH = os.environ.get("TELEGRAM_API_HASH", "")
TELEGRAM_PHONE_NUMBER = os.environ.get("TELEGRAM_PHONE_NUMBER", "")
TELEGRAM_SESSION = os.environ.get(
    "TELEGRAM_SESSION", str(DATA_DIR / "telegram_session")
)

# Channels to scan for residential-apartment SALE offers. Mixed-content channels
# (sale/rent/buy/commercial all interleaved) — filtering happens in the parser
# (scripts/51), NOT here; the scanner captures every message verbatim. Edit this
# list freely; @username (no @) or numeric id both work. Seeded with the two the
# user named + dedicated Mariupol real-estate classified channels found 2026-06-12.
TELEGRAM_CHANNELS = [
    "nemariupol",            # user-named general Mariupol channel (carries ads)
    "mariupolskiy_uezd",     # user-named general Mariupol channel (carries ads)
    "Mariupol_Nedvizhimost", # «НЕДВИЖИМОСТЬ. МАРИУПОЛЬ» — dedicated classifieds
    "Mariupol_house",        # «Недвижимость - Мариуполь» — dedicated classifieds
    "prodamMariupol",        # «Мой Мариуполь» marketplace (t.me/prodamMariupol)
    "rieltorspivak",         # «СПИВАК Недвижимость» agency channel
]

# Optionally download photo media attached to a matched message. Off by default:
# the raw store is already 5.6 GB and message text carries the evidentiary fields
# (price/address/rooms). Turn on only for a curated shortlist (e.g. demolish→
# rebuild new-build resales) where the listing photo is itself evidence.
TELEGRAM_FETCH_MEDIA = os.environ.get("TELEGRAM_FETCH_MEDIA", "false").lower() == "true"

# ── Web real-estate marketplaces — demand-side resale scan (scripts/49) ────────
# Each target is a sale-scoped Mariupol search entry point. The crawler captures
# the result pages + follows into per-listing detail pages; the parser (scripts/51)
# applies the residential-apartment-only / sell-only filter. Most are anti-bot and
# geoblocked → run from the VPS (config.PROXY), like the court portals. Edit/extend
# freely. `paginate` is a Python format string with a {page} placeholder, or null
# if the entry URL is a single page. `sale_scoped` records whether the URL already
# filters to "продажа квартир" (so the parser can trust it more).
REALESTATE_TARGETS = [
    {
        "key": "avito",
        "name": "Avito — Мариуполь, продажа квартир",
        "entry": "https://www.avito.ru/mariupol/kvartiry/prodam-ASgBAgICAUSSA8YQ",
        "paginate": "https://www.avito.ru/mariupol/kvartiry/prodam-ASgBAgICAUSSA8YQ?p={page}",
        "sale_scoped": True,
    },
    {
        "key": "cian",
        "name": "ЦИАН — Мариуполь, купить квартиру",
        "entry": "https://mariupol.cian.ru/kupit-kvartiru/",
        "paginate": "https://mariupol.cian.ru/kupit-kvartiru/?p={page}",
        "sale_scoped": True,
    },
    {
        "key": "domclick",
        "name": "Домклик — Мариуполь, купить квартиру (Сбер, 2% ипотека)",
        "entry": "https://domclick.ru/search?deal_type=sale&category=living&offer_type=flat&address=Мариуполь",
        "paginate": "https://domclick.ru/search?deal_type=sale&category=living&offer_type=flat&address=Мариуполь&offset={page}",
        "sale_scoped": True,
    },
    {
        "key": "mirkvartir",
        "name": "Мир Квартир — Мариуполь, продажа квартир",
        "entry": "https://mariupol.mirkvartir.ru/prodazha/kvartiry/",
        "paginate": "https://mariupol.mirkvartir.ru/prodazha/kvartiry/?page={page}",
        "sale_scoped": True,
    },
    {
        "key": "ayax",
        "name": "Аякс — Мариуполь, продажа квартир",
        "entry": "https://mariupol.ayax.ru/kvartiry/",
        "paginate": "https://mariupol.ayax.ru/kvartiry/?page={page}",
        "sale_scoped": True,
    },
    {
        "key": "ligakvartir",
        "name": "Лига Квартир — Мариуполь, купить квартиру",
        "entry": "https://www.ligakvartir.ru/mariupol/kupit-kvartiru",
        "paginate": "https://www.ligakvartir.ru/mariupol/kupit-kvartiru?page={page}",
        "sale_scoped": True,
    },
]

# Safety caps so a run is bounded (politeness + resource envelope).
REALESTATE_MAX_PAGES = int(os.environ.get("REALESTATE_MAX_PAGES", "20"))
REALESTATE_MAX_DETAIL = int(os.environ.get("REALESTATE_MAX_DETAIL", "400"))

# Crawl window: Law 66-RZ era through past the 01.07.2026 reregistration deadline.
DATE_FROM = os.environ.get("CRAWL_DATE_FROM", "01.03.2024")
DATE_TO = os.environ.get("CRAWL_DATE_TO", "01.07.2026")

# Politeness
REQUEST_DELAY = (4.0, 9.0)   # (min, max) seconds
MAX_RETRIES = 4
TIMEOUT = 45
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# RESULTS_TEMPLATE captured from mar-zhovt--dnr.sudrf.ru DevTools, 2026-06-08.
# lawbookarticles[] filters to special proceedings (особое производство) only.
# The Windows-1251-encoded value decodes to "Дела особого производства".
# Page parameter appended after list=ON; page 1 is the default (no param needed
# by the server, but we include it explicitly for resumability).
RESULTS_TEMPLATE = os.environ.get(
    "RESULTS_TEMPLATE",
    "{court}/modules.php?name=sud_delo&srv_num=1&name_op=r&delo_id=1540005"
    "&case_type=0&new=0"
    "&G1_PARTS__NAMESS=&g1_case__CASE_NUMBERSS=&g1_case__JUDICIAL_UIDSS="
    "&delo_table=g1_case"
    "&g1_case__ENTRY_DATE1D={date_from}&g1_case__ENTRY_DATE2D={date_to}"
    "&lawbookarticles%5B%5D=%C4%E5%EB%E0+%EE%F1%EE%E1%EE%E3%EE"
    "+%EF%F0%EE%E8%E7%E2%EE%E4%F1%F2%E2%E0+"
    "&G1_CASE__JUDGE=&g1_case__RESULT_DATE1D=&g1_case__RESULT_DATE2D="
    "&G1_CASE__RESULT=&G1_CASE__BUILDING_ID=&G1_CASE__COURT_STRUCT="
    "&G1_EVENT__EVENT_NAME=&G1_EVENT__EVENT_DATEDD="
    "&G1_PARTS__PARTS_TYPE=&G1_PARTS__INN_STRSS=&G1_PARTS__KPP_STRSS="
    "&G1_PARTS__OGRN_STRSS=&G1_PARTS__OGRNIP_STRSS="
    "&G1_RKN_ACCESS_RESTRICTION__RKN_REASON="
    "&g1_rkn_access_restriction__RKN_RESTRICT_URLSS="
    "&g1_requirement__ACCESSION_DATE1D=&g1_requirement__ACCESSION_DATE2D="
    "&G1_REQUIREMENT__CATEGORY=&g1_requirement__ESSENCESS="
    "&g1_requirement__JOIN_END_DATE1D=&g1_requirement__JOIN_END_DATE2D="
    "&G1_REQUIREMENT__PUBLICATION_ID="
    "&G1_DOCUMENT__PUBL_DATE1D=&G1_DOCUMENT__PUBL_DATE2D="
    "&G1_CASE__VALIDITY_DATE1D=&G1_CASE__VALIDITY_DATE2D="
    "&G1_ORDER_INFO__ORDER_DATE1D=&G1_ORDER_INFO__ORDER_DATE2D="
    "&G1_ORDER_INFO__ORDER_NUMSS=&G1_ORDER_INFO__EXTERNALKEYSS="
    "&G1_ORDER_INFO__STATE_ID=&G1_ORDER_INFO__RECIP_ID="
    "&list=ON&page={page}&Submit=%CD%E0%E9%F2%E8",
)

RAW_DIR.mkdir(parents=True, exist_ok=True)
