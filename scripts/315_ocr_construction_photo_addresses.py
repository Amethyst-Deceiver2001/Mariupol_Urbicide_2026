#!/usr/bin/env python3
"""Stage 2h: OCR the developer-burned-in address caption from ЕИСЖС
construction-progress photos (captured by scripts/314).

WHY THIS EXISTS
---------------
See scripts/314's docstring for the full chain. Each monthly construction
photo carries a lower-left red-text caption — e.g. "БУЛЬВАР БОГДАНА
ХМЕЛЬНИЦКОГО 12А 25.11.2025" for ЕИСЖС object 66544 — the developer's own
primary-source address disclosure, useful for objects whose ЕИСЖС `address`
field is street-only. This script OCRs every captured photo (tesseract,
rus+eng), extracts a street+house-number candidate, and cross-references it
against:
  (a) the object's own declared ЕИСЖС address
      (data/exports/qgis/eisghs_newbuilds.geojson)
  (b) the nearest demolished property by coordinate — reproducing the
      2026-07-14 ad-hoc spatial join (property.geom vs. objLkLatitude/
      objLkLongitude) as a read-only DB query

SCOPE — CONFIRMED 2026-07-15: the burned-in caption is a СЗ-1 ПОРФИР house
style only. Manual review of other developers' galleries (СУ-2007, ГСА
ДЕВЕЛОПМЕНТ, СОЛНЕЧНАЯ, КОРПОРАЦИЯ СМУ-5, etc.) found no caption at all —
their photos are plain progress shots. This script still OCRs every photo
(cheap, and the raw text is worth keeping on file), but only treats a
Porfir-developed object's OCR output as a possible address disclosure;
every non-Porfir row is marked `not_applicable_developer` regardless of what
OCR happens to read off the image, so crane signage or safety placards can't
masquerade as a false-positive address match. For non-Porfir objects the
nearest-demolished-property spatial match (already in this same CSV) remains
the only available corroborating signal — no caption fallback exists for them.

This does NOT itself add anything to scripts/164's DEMOLITION_NEWBUILD_CROSSWALK.
It only produces the evidence report; adding an entry still requires the same
manual per-pair review this project has used throughout (decree text, dates,
INN — see that file's existing entries and rejection notes).

Purely local/offline — no network calls, safe to run directly.

OUTPUT
------
data/reports/eisghs_construction_photo_addresses.csv
  eisghs_id, photo_sha256, ocr_raw_text, extracted_street, extracted_house,
  photo_date, declared_address, nearest_demolished_building_id,
  nearest_demolished_dist_m, agreement

  agreement is one of:
    agrees_with_spatial_match  — OCR'd house number matches the nearest
                                  demolished building's own house number
    agrees_with_declared       — OCR'd house number matches what the ЕИСЖС
                                  address field already states
    new_info                   — OCR succeeded, spatial match is <30m, but
                                  the house number wasn't already visible in
                                  either source — the strongest new-evidence case
    conflict_or_unmatched       — OCR succeeded but disagrees with, or is too
                                  far from, the nearest demolished property
    unresolved                 — Porfir object, but OCR found no caption in
                                  this particular photo (try another month)
    not_applicable_developer   — non-Porfir object; this technique doesn't
                                  apply, rely on the spatial-match columns only

Run scripts/314_crawl_eisghs_construction_photos.py first (from the VPS) —
this script only reads what's already in the raw store.
"""
from __future__ import annotations

import csv
import json
import logging
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

try:
    import numpy as _np
    import pytesseract
    from PIL import Image
    _OCR = True
except ImportError:
    _OCR = False

try:
    import psycopg2
    from dotenv import load_dotenv
    _PSYCOPG2 = True
except ImportError:
    _PSYCOPG2 = False

try:
    from rapidfuzz import fuzz as _fuzz
    _RAPIDFUZZ = True
except ImportError:
    _RAPIDFUZZ = False

# Below this score (0-100, rapidfuzz partial_ratio) the OCR'd street text
# isn't treated as matching a candidate street name. OCR noise on this
# caption font is real (e.g. "ХМЕЛЬНИЦКОГО" → "ХМЕЛЬЙМЦКОГВ" on a noisier
# frame) so exact/substring comparison was dropped in favor of this.
_STREET_FUZZ_THRESHOLD = 70


# Street-type tokens as they appear in the burned-in captions (uppercase, as
# rendered — matches the address normalizer's vocabulary in normalize/address.py).
_STREET_TYPES = (
    r"(?:УЛИЦА|УЛ|ПРОСПЕКТ|ПР-КТ|ПР-Т|ПРОЕЗД|БУЛЬВАР|Б-Р|"
    r"ПЕРЕУЛОК|ПЕР|ПЛОЩАДЬ|ПЛ)"
)
_DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")

# The caption's own line order (confirmed 2026-07-15 across 20 photos of
# id=66544): [street tokens, sometimes with a БУЛЬВАР/УЛ/... prefix, sometimes
# without] then [house number, its own line] then [DD.MM.YYYY date, its own
# line]. Early-month photos for a given object are noisier (smaller/newer
# concrete pour, more background clutter behind the caption) than later ones
# — this project OCRs every photo per object rather than just one, and lets
# the per-object rollup in main() pick whichever photo actually came out clean.
_HOUSE_TOKEN_RE = re.compile(r"\b(\d{1,4}[А-ЯЁ]?)\b")


def _eisghs_id_from_title(title: str) -> int | None:
    m = re.search(r"\bid=(\d+)", title)
    return int(m.group(1)) if m else None


def ocr_image(path: Path) -> str:
    """OCR the caption region: crop the lower-left corner, then isolate the
    burned-in RED text from the busy photo background via a color mask before
    handing it to tesseract.

    Plain OCR on the raw crop returns nothing (confirmed 2026-07-15) — the
    caption is small red text over a photographic construction-site
    background (rebar, concrete, workers), and tesseract can't separate text
    from texture without the color isolation. Masking red pixels (R
    dominant, R-G and R-B both large) onto a white background and running
    OCR against THAT gets clean results — e.g. id=66544's 2025-08 photo OCRs
    to an exact "БУЛЬВАР БОГДАНА ХМЕЛЬНИЦКОГО / 12А / 25.08.2025".
    """
    img = Image.open(path).convert("RGB")
    w, h = img.size
    crop = img.crop((0, int(h * 0.78), int(w * 0.60), h))
    arr = _np.array(crop)
    r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
    red_mask = (r > 120) & (r - g > 60) & (r - b > 60)
    if red_mask.sum() < 20:
        # No red caption pixels at all in this frame — not worth OCR'ing.
        return ""
    masked = _np.full(arr.shape[:2], 255, dtype=_np.uint8)
    masked[red_mask] = 0
    mask_img = Image.fromarray(masked)
    return pytesseract.image_to_string(mask_img, lang="rus", config="--psm 6")


def extract_address(ocr_text: str) -> tuple[str | None, str | None]:
    """Split OCR text into (street, house) using the caption's line order:
    date is stripped out first (it's the most reliably-OCR'd token and would
    otherwise be mistaken for a house number), then the last remaining
    digit(+letter) token is treated as the house number, everything before
    it as the street name.
    """
    text = _DATE_RE.sub(" ", ocr_text.upper())
    matches = list(_HOUSE_TOKEN_RE.finditer(text))
    if not matches:
        return None, None
    house_m = matches[-1]
    house = house_m.group(1).strip()
    street = re.sub(r"[^А-ЯЁ\s\-]", " ", text[:house_m.start()])
    street = re.sub(r"\s+", " ", street).strip()
    if len(street) < 4:
        return None, None
    return street, house


def _load_declared(gj_path: Path) -> dict[int, dict]:
    declared: dict[int, dict] = {}
    if not gj_path.exists():
        log.warning("%s not found — declared-address cross-check disabled", gj_path)
        return declared
    gj = json.loads(gj_path.read_text(encoding="utf-8"))
    for f in gj["features"]:
        p = f["properties"]
        declared[p["eisghs_id"]] = {
            "address": p.get("address"),
            "dev": p.get("dev_name_short") or p.get("dev"),
            "lon": f["geometry"]["coordinates"][0],
            "lat": f["geometry"]["coordinates"][1],
        }
    return declared


def _is_porfir(dev_name: str | None) -> bool:
    """The burned-in address+date caption was confirmed (2026-07-15, manual
    review of other developers' galleries) to be a СЗ-1 ПОРФИР house style
    only — other developers' construction-progress photos carry no caption
    at all. OCR still runs on every photo (cheap, and worth having the raw
    text on file), but a non-Porfir photo's OCR output is never treated as
    an address disclosure — any Cyrillic-looking noise it picks up (crane
    signage, safety placards) would otherwise read as a false positive."""
    return bool(dev_name) and "ПОРФИР" in dev_name.upper()


def _load_nearest_demolished(declared: dict[int, dict]) -> dict[int, dict]:
    """Nearest demolished property (by seizure_event.stage='demolition') per
    object coordinate — the same query used in the 2026-07-14 ad-hoc analysis."""
    nearest: dict[int, dict] = {}
    if not _PSYCOPG2:
        log.warning("psycopg2/dotenv not available — spatial cross-check disabled")
        return nearest
    load_dotenv()
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        log.warning("DATABASE_URL not set — spatial cross-check disabled")
        return nearest
    try:
        conn = psycopg2.connect(db_url)
    except Exception as e:
        log.warning("DB connection failed (%s) — spatial cross-check disabled", e)
        return nearest
    cur = conn.cursor()
    for eid, d in declared.items():
        cur.execute(
            """
            SELECT p.id, p.building_id,
                   ST_Distance(p.geom::geography,
                               ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography)
            FROM property p
            JOIN seizure_event se
              ON se.property_id = p.id AND se.stage = 'demolition'
            WHERE p.geom IS NOT NULL
            ORDER BY p.geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            LIMIT 1
            """,
            (d["lon"], d["lat"], d["lon"], d["lat"]),
        )
        row = cur.fetchone()
        if row:
            nearest[eid] = {"pid": row[0], "building_id": row[1], "dist_m": row[2]}
    conn.close()
    return nearest


def _street_matches(ocr_street: str, candidate: str) -> bool:
    """Fuzzy-compare the OCR'd street run against a candidate street/building
    string (declared address or building_id). Falls back to substring match
    if rapidfuzz isn't installed — strictly worse, but not a hard dependency."""
    if not ocr_street or not candidate:
        return False
    candidate_clean = re.sub(r"[^А-ЯЁа-яё\s\-]", " ", candidate.upper())
    if _RAPIDFUZZ:
        return _fuzz.partial_ratio(ocr_street, candidate_clean) >= _STREET_FUZZ_THRESHOLD
    return ocr_street[:8] in candidate_clean or candidate_clean[:8] in ocr_street


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                         format="%(asctime)s %(levelname)s %(message)s")
    if not _OCR:
        log.error("pytesseract/PIL not available — run inside .venv312 "
                   "(see memory: OCR tooling setup — tesseract+rus via Homebrew, "
                   "pytesseract in the 'ocr' pyproject extra).")
        return

    con = forensics.open_state()
    rows = con.execute(
        "SELECT sha256, raw_path, title FROM source_document "
        "WHERE source_type='eisghs_construction_photo_image' ORDER BY title"
    ).fetchall()
    if not rows:
        log.error("No eisghs_construction_photo_image records — "
                   "run scripts/314_crawl_eisghs_construction_photos.py first (from the VPS).")
        return
    log.info("Found %d construction-progress photos to OCR", len(rows))

    gj_path = config.PROJECT_ROOT / "data" / "exports" / "qgis" / "eisghs_newbuilds.geojson"
    declared = _load_declared(gj_path)
    nearest = _load_nearest_demolished(declared)

    out_dir = config.PROJECT_ROOT / "data" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "eisghs_construction_photo_addresses.csv"

    n_ocr_hit = 0
    n_new_info = 0
    n_porfir_photos = 0
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "eisghs_id", "photo_sha256", "ocr_raw_text", "extracted_street",
            "extracted_house", "photo_date", "declared_address",
            "nearest_demolished_building_id", "nearest_demolished_dist_m",
            "agreement",
        ])
        for sha, raw_path, title in rows:
            eid = _eisghs_id_from_title(title)
            p = Path(raw_path)
            if not p.exists():
                log.warning("file missing: %s", raw_path)
                continue
            try:
                text = ocr_image(p)
            except Exception as e:
                log.warning("OCR failed for %s (id=%s): %s", p.name, eid, e)
                continue

            near = nearest.get(eid, {}) if eid is not None else {}
            decl = declared.get(eid, {}) if eid is not None else {}

            if _is_porfir(decl.get("dev")):
                n_porfir_photos += 1
                street, house = extract_address(text)
            else:
                # Non-Porfir developers don't burn a caption into their photos
                # (confirmed 2026-07-15) — don't let OCR noise masquerade as
                # an address hit for these.
                street, house = None, None
            date_m = _DATE_RE.search(text)
            photo_date = (f"{date_m.group(3)}-{date_m.group(2)}-{date_m.group(1)}"
                          if date_m else None)

            if not _is_porfir(decl.get("dev")):
                agreement = "not_applicable_developer"
            else:
                agreement = "unresolved"
                if street and house:
                    n_ocr_hit += 1
                    bid = near.get("building_id") or ""
                    decl_addr = decl.get("address") or ""
                    house_matches_spatial = house.upper() in bid.upper()
                    house_matches_declared = house.upper() in decl_addr.upper()
                    street_matches_spatial = _street_matches(street, bid)
                    street_matches_declared = _street_matches(street, decl_addr)

                    if house_matches_spatial and street_matches_spatial:
                        agreement = "agrees_with_spatial_match"
                    elif house_matches_declared and street_matches_declared:
                        agreement = "agrees_with_declared"
                    elif street_matches_spatial and near.get("dist_m") is not None \
                            and near["dist_m"] < 30 and not house_matches_declared:
                        # Street name checks out against the nearest demolished
                        # building and the object's own address field didn't
                        # already carry this house number — the caption is
                        # adding real information, not just confirming what
                        # was already known.
                        agreement = "new_info"
                        n_new_info += 1
                    else:
                        agreement = "conflict_or_unmatched"

            writer.writerow([
                eid, sha, text.strip().replace("\n", " | ")[:300], street, house,
                photo_date, decl.get("address"),
                near.get("building_id"), near.get("dist_m"), agreement,
            ])
            log.info("id=%-6s  extracted=%-30s house=%-6s date=%-10s agreement=%s",
                      eid, street or "-", house or "-", photo_date or "-", agreement)

    log.info("── Summary ─────────────────────────────────────────────")
    log.info("  Photos OCR'd:            %d", len(rows))
    log.info("  Porfir photos (caption technique applies): %d", n_porfir_photos)
    log.info("  Address caption found:   %d / %d Porfir photos", n_ocr_hit, n_porfir_photos)
    log.info("  New-info matches (<30m): %d", n_new_info)
    log.info("  Non-Porfir photos rely on the spatial-match columns only — "
             "not a failure, expected per the 2026-07-15 scope finding.")
    log.info("  Output:                  %s", out_path)
    log.info("Next: review each 'new_info'/'conflict_or_unmatched' row by hand before "
             "adding anything to scripts/164_export_map_layers.py's DEMOLITION_NEWBUILD_CROSSWALK.")


if __name__ == "__main__":
    main()
