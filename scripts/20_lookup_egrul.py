#!/usr/bin/env python3
"""Stage 2g: resolve + forensically capture company records for land-order beneficiaries.

Two-phase tool built around the egrul.org mirror of the Russian EGRUL registry.

  Why not egrul.nalog.ru?  The live FNS portal drops the TLS handshake from any
  non-Russian IP (geo-block at the network layer), so it is unreachable here.

  Why egrul.org (itsoft mirror)?  It is globally reachable, requires no auth,
  serves clean structured JSON by INN/OGRN, AND it covers occupied-territory
  (DNR / region 93) companies — verified against a known region-93 SPV.

  The catch: egrul.org's NAME-search form is gated behind Yandex SmartCaptcha,
  so name -> INN discovery cannot be automated.  But INN -> full-record lookup
  (/{INN}.json) is captcha-free.  Hence two phases:

  PHASE 1 (worklist).  Run with no INN map present.  Reads dnr_land_orders.jsonl,
    lists every beneficiary still missing an INN, and writes a template at
    data/parsed/egrul_manual_inns.json plus prints a browser search URL per name.
    The user opens each URL, solves the one captcha, reads off the INN, and pastes
    it into the template.  (Reference-layer metadata; human-in-the-loop is fine.)

  PHASE 2 (capture + verify).  Re-run after filling the template.  For each
    provided INN it fetches https://egrul.org/{INN}.json, captures the raw body
    immutably (SHA-256 + .meta.json sidecar via forensics.capture_source, logged
    to source_document for chain of custody), parses the registry record
    (full/short name, ОГРН, reg date, ОПФ, status, address, director), and writes
    one row per company to data/parsed/egrul_inn_lookups.jsonl.

  After phase 2: copy each confirmed INN into MANUAL_INN_OVERRIDES at the bottom
  of scripts/11_parse_dnr_land_orders.py, then re-run scripts 11 + 18.

Transport: prefers brew curl (OpenSSL) over macOS system curl (LibreSSL 2.8.x,
which fails modern TLS handshakes).  egrul.org needs no VPN.
"""
from __future__ import annotations

import json
import logging
import subprocess
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config  # noqa: E402
from mariupol_seizures import forensics  # noqa: E402

log = logging.getLogger(__name__)

EGRUL_BASE = "https://egrul.org"
SEARCH_URL_TMPL = "https://egrul.org/s/?region={region}&name={name}"
DNR_REGION = "93"


def _find_curl() -> str:
    for candidate in (
        "/opt/homebrew/opt/curl/bin/curl",   # Apple Silicon brew (OpenSSL)
        "/usr/local/opt/curl/bin/curl",       # Intel brew (OpenSSL)
        "curl",
    ):
        try:
            if subprocess.run([candidate, "--version"],
                              capture_output=True).returncode == 0:
                return candidate
        except OSError:
            continue
    return "curl"


_CURL_BIN = _find_curl()


def _curl_get(url: str, proxy: str | None = None) -> bytes | None:
    """GET raw bytes via curl. Returns body bytes or None on failure."""
    cmd = [_CURL_BIN, "-s", "--max-time", str(config.TIMEOUT),
           "-H", f"User-Agent: {config.USER_AGENT}",
           "-H", "Accept: application/json, */*"]
    if proxy:
        cmd += ["--proxy", proxy]
    cmd.append(url)
    try:
        res = subprocess.run(cmd, capture_output=True, timeout=config.TIMEOUT + 10)
        if res.returncode != 0:
            log.warning("curl GET rc=%d for %s: %s", res.returncode, url,
                        res.stderr.decode("utf-8", "replace")[:200])
            return None
        return res.stdout
    except (subprocess.TimeoutExpired, OSError) as e:
        log.warning("curl GET error for %s: %s", url, e)
        return None


# --- EGRUL JSON parsing ------------------------------------------------------

def _attrs(node: object) -> dict:
    """Return the @attributes dict of an egrul.org JSON node, or {}."""
    if isinstance(node, dict):
        a = node.get("@attributes")
        if isinstance(a, dict):
            return a
    return {}


def _build_address(addr_node: dict) -> str | None:
    """Assemble a readable address line from a СвАдресЮЛ FIAS sub-node.

    Prefers the modern FIAS sub-node (СвАдрЮЛФИАС); falls back to СвМНЮЛ.
    Each component carries its type + name/number in @attributes.
    """
    if not isinstance(addr_node, dict):
        return None
    fias = addr_node.get("СвАдрЮЛФИАС") or addr_node.get("СвМНЮЛ") or {}
    if not isinstance(fias, dict):
        return None
    parts: list[str] = []
    region = fias.get("НаимРегион")
    if region:
        parts.append(str(region).title())
    # City / settlement, street, building, premises — each {Тип/Вид, Наим/Номер}.
    for key, label_keys, val_keys in (
        ("НаселенПункт", ("Вид",), ("Наим",)),
        ("ЭлУлДорСети", ("Тип",), ("Наим",)),
        ("Здание", ("Тип",), ("Номер",)),
        ("ПомещЗдания", ("Тип",), ("Номер",)),
    ):
        node = fias.get(key)
        a = _attrs(node) if isinstance(node, dict) else {}
        if not a:
            continue
        label = next((a[k] for k in label_keys if a.get(k)), "")
        val = next((a[k] for k in val_keys if a.get(k)), "")
        seg = " ".join(s for s in (str(label).strip(), str(val).strip()) if s)
        if seg:
            parts.append(seg)
    return ", ".join(parts) or None


def _parse_egrul_json(payload: dict) -> dict:
    """Extract the fields we care about from an egrul.org /{INN}.json record.

    Defensive: the schema mirrors the FNS XML; nodes are absent for some
    companies, so every access is guarded.  The raw JSON is captured verbatim
    regardless, so this parse can be re-run/extended without re-fetching.
    """
    ul = payload.get("СвЮЛ") if isinstance(payload, dict) else None
    if not isinstance(ul, dict):
        # Individual entrepreneur record uses СвИП; out of scope for SPVs but
        # surface enough to flag it.
        ip = payload.get("СвИП") if isinstance(payload, dict) else None
        if isinstance(ip, dict):
            a = _attrs(ip)
            return {
                "record_type": "ИП",
                "inn": a.get("ИННФЛ"),
                "ogrn": a.get("ОГРНИП"),
                "ogrn_date": a.get("ДатаОГРНИП"),
                "full_name": None, "short_name": None, "opf": "ИП",
                "status": None, "address": None, "director": None,
            }
        return {"record_type": "unknown"}

    head = _attrs(ul)
    name_node = ul.get("СвНаимЮЛ") or {}
    full_name = _attrs(name_node).get("НаимЮЛПолн")
    short_name = _attrs((name_node or {}).get("СвНаимЮЛСокр") or {}).get("НаимСокр")

    # Status: a termination/liquidation node means the company is gone.
    status = "active"
    if isinstance(ul.get("СвПрекрЮЛ"), dict):
        status = "terminated"
    elif isinstance(ul.get("СвСтатус"), dict):
        st = _attrs(ul["СвСтатус"]).get("НаимСтатусЮЛ")
        if st:
            status = st

    # Address: СвАдресЮЛ wraps a structured FIAS sub-node (СвАдрЮЛФИАС, or the
    # older СвМНЮЛ).  Assemble a readable line from its components.
    address = _build_address(ul.get("СвАдресЮЛ") or ul.get("СвАдрЮЛ") or {})

    # Director (СведДолжнФЛ → ФИО).
    director = None
    dn = ul.get("СведДолжнФЛ")
    cand = dn[0] if isinstance(dn, list) and dn else dn
    if isinstance(cand, dict):
        fio = cand.get("СвФЛ") or {}
        fa = _attrs(fio)
        parts = [fa.get("Фамилия"), fa.get("Имя"), fa.get("Отчество")]
        director = " ".join(p for p in parts if p) or None

    return {
        "record_type": "ЮЛ",
        "inn": head.get("ИНН"),
        "kpp": head.get("КПП"),
        "ogrn": head.get("ОГРН"),
        "ogrn_date": head.get("ДатаОГРН"),
        "issued_date": head.get("ДатаВып"),
        "opf": head.get("ПолнНаимОПФ"),
        "full_name": full_name,
        "short_name": short_name,
        "status": status,
        "address": address,
        "director": director,
    }


# --- worklist ---------------------------------------------------------------

def _collect_unresolved(land_orders_path: Path) -> dict[str, list[str]]:
    rows = [json.loads(l) for l in
            land_orders_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    unresolved: dict[str, list[str]] = {}
    for r in rows:
        if r.get("beneficiary_inn"):
            continue
        name = r.get("beneficiary_name")
        if not name or len(name) < 4:
            continue
        if len(name) > 120 or "Программа" in name or "ДОМ.РФ" in name:
            continue
        dec = r.get("decree_number") or "?"
        unresolved.setdefault(name, []).append(dec)
    return unresolved


def _search_url(name: str) -> str:
    # egrul.org search wants the name WITHOUT legal-form prefix.
    import re
    q = re.sub(r"^(?:Специализированный\s+застройщик[-\s]*\d*\s*|СЗ\s+|ООО\s+|АО\s+)",
               "", name, flags=re.I)
    q = re.sub(r"[«»\"']", "", q).strip()
    return SEARCH_URL_TMPL.format(region=DNR_REGION,
                                  name=urllib.parse.quote(q))


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(message)s")
    log.info("Using curl: %s", _CURL_BIN)

    parsed_dir = config.PROJECT_ROOT / "data" / "parsed"
    land_orders_path = parsed_dir / "dnr_land_orders.jsonl"
    map_path = parsed_dir / "egrul_manual_inns.json"
    out_path = parsed_dir / "egrul_inn_lookups.jsonl"

    if not land_orders_path.exists():
        log.error("dnr_land_orders.jsonl not found — run scripts/11 first")
        sys.exit(1)

    unresolved = _collect_unresolved(land_orders_path)
    log.info("Unresolved beneficiaries: %d", len(unresolved))

    # Load or scaffold the manual INN map.
    inn_map: dict[str, str] = {}
    if map_path.exists():
        try:
            doc = json.loads(map_path.read_text(encoding="utf-8"))
            inn_map = {k: str(v).strip() for k, v in (doc.get("inns") or {}).items()
                       if str(v).strip()}
        except (ValueError, AttributeError) as e:
            log.error("Could not parse %s: %s", map_path.name, e)
            sys.exit(1)

    if not map_path.exists():
        # PHASE 1: scaffold the template + print browser search URLs.
        template = {
            "_instructions": (
                "Open each search URL below in a browser (no VPN needed), solve "
                "the captcha, read the company's ИНН, and paste it as the value. "
                "Then re-run: python3 scripts/20_lookup_egrul.py"
            ),
            "_search_urls": {name: _search_url(name) for name in sorted(unresolved)},
            "inns": {name: "" for name in sorted(unresolved)},
        }
        map_path.write_text(json.dumps(template, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        log.info("PHASE 1 — wrote template: %s", map_path)
        log.info("Open these in a browser, solve the captcha, fill in the INN:")
        for name in sorted(unresolved):
            log.info("  %-55s %s", name, _search_url(name))
        log.info("Then re-run this script to capture + verify each record.")
        return

    if not inn_map:
        log.info("PHASE 1 (template exists but no INNs filled yet).")
        log.info("Fill ИНН values in %s, then re-run. Search URLs:", map_path.name)
        for name in sorted(unresolved):
            log.info("  %-55s %s", name, _search_url(name))
        return

    # PHASE 2: capture + verify each provided INN.
    log.info("PHASE 2 — capturing %d INN record(s) from egrul.org", len(inn_map))
    proxy = config.PROXY or None
    con = forensics.open_state()
    results: list[dict] = []

    for name, inn in inn_map.items():
        if not inn.isdigit():
            log.warning("  %s: ИНН %r is not numeric — skipping", name, inn)
            continue
        url = f"{EGRUL_BASE}/{inn}.json"
        log.info("Fetching %s  (%s)", url, name)
        body = _curl_get(url, proxy=proxy)
        if body is None:
            results.append({"beneficiary_name": name, "inn_queried": inn,
                            "source": "error", "error": "fetch_failed"})
            continue

        # Forensic capture BEFORE parse (SHA-256 + sidecar + source_document log).
        sha = forensics.capture_source(
            body, url=url, source_type="egrul_registry",
            title=f"EGRUL record INN {inn}",
            description=f"egrul.org JSON for land-order beneficiary {name!r}",
            content_type="application/json", http_status=200, con=con,
        )

        try:
            payload = json.loads(body)
        except ValueError:
            log.warning("  non-JSON body for INN %s (sha %s)", inn, sha[:12])
            results.append({"beneficiary_name": name, "inn_queried": inn,
                            "source_sha256": sha, "source": "non_json"})
            continue

        parsed = _parse_egrul_json(payload)
        # Sanity: does the returned record's INN match what we queried?
        inn_match = (parsed.get("inn") == inn)
        rec = {
            "beneficiary_name": name,
            "inn_queried": inn,
            "decree_numbers": unresolved.get(name, []),
            **parsed,
            "inn_match": inn_match,
            "source_url": url,
            "source_sha256": sha,
            "captured_at": forensics.now_iso(),
            "source": "egrul_org",
        }
        results.append(rec)
        log.info("  → %s  ОГРН=%s  %r  status=%s  inn_match=%s",
                 parsed.get("inn"), parsed.get("ogrn"),
                 parsed.get("short_name") or parsed.get("full_name"),
                 parsed.get("status"), inn_match)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for rec in results:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    ok = sum(1 for r in results if r.get("source") == "egrul_org" and r.get("inn_match"))
    log.info("Done — %d / %d records captured + INN-verified → %s",
             ok, len(results), out_path)

    # Surface any names still without an INN in the map.
    still_missing = [n for n in sorted(unresolved) if n not in inn_map]
    if still_missing:
        log.info("Still needing manual INN lookup (%d):", len(still_missing))
        for n in still_missing:
            log.info("  %-55s %s", n, _search_url(n))

    if ok:
        log.info("Next: copy verified INNs into MANUAL_INN_OVERRIDES in")
        log.info("  scripts/11_parse_dnr_land_orders.py, then re-run scripts 11 + 18.")


if __name__ == "__main__":
    main()
