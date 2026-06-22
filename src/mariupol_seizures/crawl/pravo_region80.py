"""Stage 1g: capture the DNR-level legal framework from the Russian official
legal-publication portal (publication.pravo.gov.ru), block `region80` =
Донецкая Народная Республика.

Claude must NEVER run this — see CLAUDE.md. publication.pravo.gov.ru serves a
Russian-CA TLS certificate and is geoblocked; run it from the Russia-routed VPS
with SSL_VERIFY=false. Capture-before-parse, SHA-256 everything, append-only.

WHY THIS EXISTS
---------------
The Mariupol municipal portal (mariupol.gosuslugi.ru, scripts 05/08) and the
court portals (script 01) give us the *operational* layer of the dispossession:
the building-by-building demolition lists, ownerless designations, and court
transfers. They do NOT give us the *enabling legal framework* — the laws of the
ДНР Народный Совет, the указы/распоряжения of the Глава ДНР, and the
постановления of the Правительство ДНР that authorise each step. Those are
published here, in the federal official-publication register, block region80.

This is the layer the legal-mechanisms review
(`docs/legal_mechanisms_review.md`) is built on: each rung of the pipeline
(ownerless → court transfer → demolition → land grant → resale → housing
allocation) rests on a named, dated, signed normative act, and this is the
canonical, self-authenticating source for those acts (the federal register's own
copy, with the signing authority and publication number).

WHAT THIS CAPTURES
------------------
Two tiers, both forensic:

1. The COMPLETE index of region80 — every publication listing page (JSON via the
   portal's read-only API; HTML fallback). Cheap, and it is the manifest of
   everything the DNR has officially published. source_type=`pravo_region80_index`.

2. The dispossession-relevant SUBSET of documents as signed PDFs — those whose
   title/type matches DISPOSSESSION_LEXICON (снос, бесхозяйн, изъятие, земельн,
   жиль, переселен, компенсац, генплан, …). Downloading every region80 PDF would
   blow the resource envelope (tens of thousands of acts); the full index is kept
   for completeness and the PDFs are fetched selectively. Override with
   --all-pdfs. source_type=`pravo_region80_pdf` + per-doc metadata
   `pravo_region80_meta`.

PORTAL API (read-only; verified 2026-06-11 against public documentation —
publication.pravo.gov.ru/help, data.apicrafter.ru/tables/pravogovru/publications)
-----------------------------------------------------------------------------
Document record fields: EoNumber (publication number, the primary key), Number,
Name, ComplexName, DocumentDate, DocumentTypeName, SignatoryAuthorityName,
HasPdf, JDRegNumber, JDRegDate, ViewUrl.

Endpoints (constants below — confirm with --probe on first run, the portal has
revised key casing across versions and we cannot test from outside Russia):
  list : /api/Documents?block=region80&index={i}&pageSize={n}   -> JSON
  meta : /api/Document?eoNumber={eo}                            -> JSON
  pdf  : /file/pdf?eoNumber={eo}                                -> application/pdf
  html : /documents/block/region80?index={i}                   -> HTML (fallback)
         /document/view/{eo}                                    -> HTML doc page

--probe fetches page 1, captures it, and prints the JSON's top-level keys + the
first record's keys so the operator can confirm the shape before a full run.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import time
from typing import Any, Iterator

import requests
import urllib3
from bs4 import BeautifulSoup

from .. import config, forensics

log = logging.getLogger(__name__)

if not config.SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ORIGIN = "http://publication.pravo.gov.ru"
BLOCK = "region80"  # Донецкая Народная Республика (confirmed 2026-06-11)
PAGE_SIZE = 200

# API/URL templates. Kept as constants so a portal-side rename is a one-line fix.
API_LIST = ORIGIN + "/api/Documents?block={block}&index={index}&pageSize={size}"
API_META = ORIGIN + "/api/Document?eoNumber={eo}"
PDF_URL = ORIGIN + "/file/pdf?eoNumber={eo}"
HTML_LIST = ORIGIN + "/documents/block/{block}?index={index}"

# Candidate JSON keys for the documents array and the publication number, tried
# in order — the portal has used several across API versions.
_DOCS_KEYS = ("documents", "items", "Documents", "Items", "result", "data")
_EO_KEYS = ("eoNumber", "EoNumber", "eo_number", "number", "Number")
_NAME_KEYS = ("name", "Name", "complexName", "ComplexName")
_TYPE_KEYS = ("documentTypeName", "DocumentTypeName", "viewTypeName")
_DATE_KEYS = ("documentDate", "DocumentDate", "publishDateShort", "PublishDateShort")
_HASPDF_KEYS = ("hasPdf", "HasPdf")

# Dispossession lexicon: the legal-mechanism vocabulary spanning every rung of
# the pipeline. A document whose Name/ComplexName/DocumentTypeName matches any of
# these is fetched as a PDF. Substrings are matched case-insensitively against a
# folded (ё->е) lowercase string.
#
# Entries are SINGLE word-stems, never multi-word phrases: Russian inflects and
# separates adjacent words ("генеральн[ого] план[а]"), so a phrase like
# "генеральн план" would never substring-match an inflected title. Stems are
# chosen to cover their whole inflection paradigm. This errs deliberately toward
# OVER-capture — per the project's capture-before-parse rule it is far better to
# pull a few irrelevant PDFs (cheap bandwidth) than to miss an enabling act; the
# parse stage narrows precisely. Tune here if the VPS bandwidth bill warrants.
DISPOSSESSION_LEXICON = (
    # demolition / razing / unfit
    "снос", "снес", "демонтаж", "аварийн", "ветх", "непригодн",
    # ownerless / escheat / appropriation / (de)privatization
    "бесхозяйн", "выморочн", "изъят", "реквизи", "национализ", "конфискац",
    "собственност", "приватизац",
    # land allocation / lease / auction
    "земельн", "землепользован", "аукцион", "торгов", "аренд",
    # housing distribution / service housing / maneuver fund / resettlement
    "жил", "квартир", "маневренн", "служебн", "нуждающ",
    "переселен", "расселен", "найм",
    # compensation
    "компенсац", "возмещени", "выплат",
    # urban-planning / reconstruction authority (top of chain)
    "градостроительн", "генплан", "генеральн", "планировк", "застройк",
    "реконструкц", "восстановлен", "освоени",
    # cadastral / registration / addressing / street renaming (toponymy)
    "кадастр", "инвентаризац", "переименован", "улиц", "наименован",
)

_DIGITS_RE = re.compile(r"\d{6,}")


def _fold(s: str) -> str:
    return (s or "").replace("ё", "е").replace("Ё", "Е").lower()


def is_relevant(*texts: str | None) -> bool:
    blob = _fold(" ".join(t for t in texts if t))
    return any(term in blob for term in DISPOSSESSION_LEXICON)


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": config.USER_AGENT,
        "Accept-Language": "ru,en;q=0.8",
        "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
    })
    if config.PROXY:
        s.proxies.update({"http": config.PROXY, "https": config.PROXY})
    return s


def polite_sleep() -> None:
    lo, hi = config.REQUEST_DELAY
    time.sleep(lo + (hi - lo) * 0.5)


def _get(s: requests.Session, url: str) -> requests.Response | None:
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            return s.get(url, timeout=config.TIMEOUT, verify=config.SSL_VERIFY)
        except requests.RequestException as e:
            wait = min(60, 2 ** attempt)
            log.warning("GET %s failed (%d/%d): %s; wait %ds",
                        url, attempt, config.MAX_RETRIES, e, wait)
            time.sleep(wait)
    log.error("giving up on %s", url)
    return None


def _first(d: dict, keys: tuple[str, ...]) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def _parse_index_json(body: bytes) -> tuple[list[dict], int | None]:
    """Return (records, pages_total) from a listing-page JSON body, defensively."""
    try:
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return [], None
    if isinstance(data, list):
        return data, None
    docs: list = []
    for k in _DOCS_KEYS:
        v = data.get(k) if isinstance(data, dict) else None
        if isinstance(v, list):
            docs = v
            break
    pages = None
    if isinstance(data, dict):
        for k in ("pagesCount", "pagesTotalCount", "PagesCount", "totalPages"):
            if isinstance(data.get(k), int):
                pages = data[k]
                break
    return docs, pages


def _eo_from_record(rec: dict) -> str | None:
    eo = _first(rec, _EO_KEYS)
    return str(eo) if eo else None


def _extract_eonumbers_from_html(body: bytes) -> list[str]:
    """Fallback: pull eoNumbers from an HTML listing page's document links."""
    soup = BeautifulSoup(body, "lxml")
    found: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        m = re.search(r"(?:document/view/|eoNumber=)(\d{6,})", href)
        if m:
            found.append(m.group(1))
    # de-dup preserving order
    seen: set[str] = set()
    return [e for e in found if not (e in seen or seen.add(e))]


def iter_index(s: requests.Session, con, use_html: bool) -> Iterator[dict]:
    """Yield document records page by page, capturing each index page forensically.

    JSON mode yields full records (dict). HTML-fallback mode yields minimal
    records {"_eo": eoNumber} with no metadata (PDF still fetchable by eoNumber).
    """
    index = 1
    pages_total: int | None = None
    while True:
        if use_html:
            url = HTML_LIST.format(block=BLOCK, index=index)
            ctype = "text/html"
        else:
            url = API_LIST.format(block=BLOCK, index=index, size=PAGE_SIZE)
            ctype = "application/json"

        r = _get(s, url)
        polite_sleep()
        if r is None or r.status_code != 200:
            log.warning("index page %d unavailable (HTTP %s) — stopping",
                        index, r.status_code if r else "N/A")
            break

        forensics.capture_source(
            r.content, url=url,
            source_type="pravo_region80_index",
            title=f"pravo.gov.ru region80 (ДНР) — index page {index}",
            description=(
                "Official-publication register listing page for block region80 "
                "(Донецкая Народная Республика). Forensic manifest of DNR "
                "normative acts; the dispossession-relevant subset is captured "
                "as PDFs separately."
            ),
            content_type=r.headers.get("Content-Type", ctype),
            http_status=r.status_code, con=con,
        )

        if use_html:
            eos = _extract_eonumbers_from_html(r.content)
            if not eos:
                log.info("HTML page %d has no document links — end of block", index)
                break
            for eo in eos:
                yield {"_eo": eo}
        else:
            records, pages = _parse_index_json(r.content)
            if pages and pages_total is None:
                pages_total = pages
                log.info("region80 reports %d index pages (pageSize=%d)",
                         pages_total, PAGE_SIZE)
            if not records:
                log.info("JSON page %d empty — end of block", index)
                break
            yield from records

        index += 1
        if pages_total is not None and index > pages_total:
            break
        if index > 100000:  # hard stop, should never hit
            log.error("index runaway guard tripped at page %d", index)
            break


def capture_document(s: requests.Session, con, rec: dict) -> bool:
    """Capture one document's metadata JSON + signed PDF. Returns True if a PDF
    was fetched. Resumable via the done-key on eoNumber."""
    eo = rec.get("_eo") or _eo_from_record(rec)
    if not eo or not _DIGITS_RE.fullmatch(eo):
        log.debug("record without a usable eoNumber: %.80s", str(rec))
        return False

    key = f"pravo_region80::{eo}"
    if forensics.is_done(con, key):
        return False

    name = _first(rec, _NAME_KEYS) or ""
    dtype = _first(rec, _TYPE_KEYS) or ""
    ddate = _first(rec, _DATE_KEYS) or ""

    # metadata JSON (skip in HTML-fallback mode, where we have no record fields)
    if not rec.get("_eo"):
        meta_url = API_META.format(eo=eo)
        mr = _get(s, meta_url)
        polite_sleep()
        if mr is not None and mr.status_code == 200:
            forensics.capture_source(
                mr.content, url=meta_url,
                source_type="pravo_region80_meta",
                title=f"pravo.gov.ru region80 doc {eo} — metadata",
                description=f"{dtype} {name}".strip()[:500] or f"region80 doc {eo}",
                content_type=mr.headers.get("Content-Type", "application/json"),
                http_status=mr.status_code, con=con,
            )

    pdf_url = PDF_URL.format(eo=eo)
    pr = _get(s, pdf_url)
    polite_sleep()
    if pr is None or pr.status_code != 200 or not pr.content:
        log.warning("PDF not fetched for %s (HTTP %s)", eo,
                    pr.status_code if pr else "N/A")
        forensics.mark_done(con, key)  # don't retry a missing PDF forever
        return False

    forensics.capture_source(
        pr.content, url=pdf_url,
        source_type="pravo_region80_pdf",
        title=(f"{dtype} {name}".strip() or f"region80 doc {eo}")[:300],
        description=(
            f"ДНР normative act, official publication №{eo}"
            + (f", {ddate}" if ddate else "")
            + (f" [{dtype}]" if dtype else "")
            + ". Captured from publication.pravo.gov.ru block region80 as a "
            "dispossession-pipeline legal-mechanism source."
        ),
        content_type=pr.headers.get("Content-Type", "application/pdf"),
        http_status=pr.status_code, con=con,
    )
    forensics.mark_done(con, key)
    log.info("captured PDF %s — %.80s", eo, name or dtype)
    return True


def probe(s: requests.Session, con) -> None:
    """Fetch + capture index page 1 and print its shape so the operator can
    confirm the API contract before a full crawl."""
    url = API_LIST.format(block=BLOCK, index=1, size=PAGE_SIZE)
    r = _get(s, url)
    if r is None:
        log.error("probe: no response from %s", url)
        return
    log.info("probe: HTTP %s, Content-Type=%s, %d bytes",
             r.status_code, r.headers.get("Content-Type"), len(r.content))
    forensics.capture_source(
        r.content, url=url, source_type="pravo_region80_index",
        title="pravo.gov.ru region80 — probe (page 1)",
        description="Initial probe of the region80 listing API to confirm shape.",
        content_type=r.headers.get("Content-Type", "application/json"),
        http_status=r.status_code, con=con,
    )
    records, pages = _parse_index_json(r.content)
    print(f"\n--- region80 probe ---\nHTTP {r.status_code}  pages_total={pages}  "
          f"records_on_page={len(records)}")
    try:
        top = json.loads(r.content)
        if isinstance(top, dict):
            print("top-level JSON keys:", list(top.keys()))
    except ValueError:
        print("response is not JSON — use --html mode (HTML fallback parser)")
    if records:
        print("first record keys:", list(records[0].keys()))
        eo = _eo_from_record(records[0])
        print("first record eoNumber:", eo)
        print("first record name:", _first(records[0], _NAME_KEYS))
    print("--- end probe ---\n")


def run(use_html: bool = False, all_pdfs: bool = False,
        probe_only: bool = False) -> None:
    con = forensics.open_state()
    s = make_session()
    seen = pdfs = 0
    try:
        if probe_only:
            probe(s, con)
            return
        for rec in iter_index(s, con, use_html):
            seen += 1
            if all_pdfs or rec.get("_eo") or is_relevant(
                _first(rec, _NAME_KEYS), _first(rec, _TYPE_KEYS),
                rec.get("ComplexName"), rec.get("complexName"),
            ):
                # In HTML mode we can't pre-filter (no metadata) — fetch all eo'd
                # PDFs only if --all-pdfs; otherwise HTML mode just builds the index.
                if rec.get("_eo") and not all_pdfs:
                    continue
                if capture_document(s, con, rec):
                    pdfs += 1
    except KeyboardInterrupt:
        log.warning("interrupted — state saved, safe to rerun (resumes).")

    n_idx = con.execute(
        "SELECT COUNT(*) FROM source_document WHERE source_type='pravo_region80_index'"
    ).fetchone()[0]
    n_pdf = con.execute(
        "SELECT COUNT(*) FROM source_document WHERE source_type='pravo_region80_pdf'"
    ).fetchone()[0]
    log.info("done; saw %d records this run, fetched %d PDFs. "
             "Store totals: %d index pages, %d region80 PDFs.",
             seen, pdfs, n_idx, n_pdf)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Crawl pravo.gov.ru block region80 (ДНР).")
    ap.add_argument("--probe", action="store_true",
                    help="fetch+capture page 1 and print the API shape, then exit")
    ap.add_argument("--html", action="store_true",
                    help="use the HTML listing fallback instead of the JSON API")
    ap.add_argument("--all-pdfs", action="store_true",
                    help="download EVERY document PDF, not just dispossession-relevant "
                         "ones (large — blows the resource envelope; use deliberately)")
    args = ap.parse_args(argv)
    run(use_html=args.html, all_pdfs=args.all_pdfs, probe_only=args.probe)
