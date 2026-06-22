#!/usr/bin/env python3
"""Capture a Telegram post + photo showing physical eviction enforcement
at просп. Ленина, 133 (property id 4442 on the spine).

t.me/ssaniaworld/3348 (23 Oct 2025, 19.3K views, channel "Министерство
Счастья Сании Денисовой. Движение - СИЛА ДОБРА"):

  - Post text: апартменты 2, 19, 20, 33 in the building had court rulings
    in 2024 (ownerless designation); now (Oct 2025) residents with
    registration (прописка) and powers of attorney are being told to
    vacate. Apartment 19 is already a registry_inclusion seizure_event for
    property 4442 (id 37362, address_raw "...Ленина (Мира), 133, 19").
  - Attached photo: two official "ОПЕЧАТАНО" (sealed) notices, both
    naming "пр. Ленина д. 133 кв. 19", issued by Управление имущественных
    и земельных отношений (Dept. of Property & Land Relations), citing RF
    Criminal Code arts. 139/168, with handwritten vacate deadlines
    22.10.2025 and 25.10.2025. This is the first dated photographic
    artifact in the project showing the on-the-ground enforcement step
    that follows a registry_inclusion / ownerless_designation record.
  - The same post text separately describes "Черноморская, 10" undergoing
    active inventory/inspection (инвентаризация) -- the pre-petition
    stage. No exact "Черноморская, 10" exists on the spine (closest:
    Черноморская 1 / 22/10) -- flagged as a new lead, not auto-merged.

Public Telegram channel -- the `?embed=1` widget and the cdn4.telesco.pe
photo URL are both static, unauthenticated, non-geoblocked (same precedent
as scripts 52/54-59; Claude runs this directly, no VPS needed).

Output: data/raw/<sha256>.{html,jpg} + .meta.json per artifact (forensics
capture_source(), logged to data/state.sqlite's source_document table), plus
a manifest at data/parsed/lenina133_apt19_sealing_manifest.json.

Idempotent: re-running re-fetches but capture_source() only writes new bytes
if the SHA-256 changed; the manifest is rewritten each run.
"""
import json
import logging
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger("fetch_lenina133_sealing_notice")

MANIFEST_PATH = config.DATA_DIR / "parsed" / "lenina133_apt19_sealing_manifest.json"
REQUEST_PAUSE_S = 1.0

POST_URL = "https://t.me/ssaniaworld/3348?embed=1"
POST_CANONICAL_URL = "https://t.me/ssaniaworld/3348"
PHOTO_URL_RE = re.compile(r"background-image:url\('([^']+)'\)")


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"generated_at": None, "artifacts": []}


def save_manifest(manifest: dict) -> None:
    from datetime import datetime, timezone

    manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def fetch(url: str) -> tuple[bytes, str, int]:
    """Return (content, content_type, http_status). Retries transient errors."""
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": config.USER_AGENT},
                timeout=config.TIMEOUT,
                allow_redirects=True,
            )
            resp.raise_for_status()
            return resp.content, resp.headers.get("Content-Type", "text/html"), resp.status_code
        except requests.exceptions.RequestException as exc:
            if attempt == config.MAX_RETRIES - 1:
                raise
            log.warning("transient error fetching %s (attempt %d/%d): %s -- retrying",
                         url, attempt + 1, config.MAX_RETRIES, exc)
            time.sleep(2.0 * (attempt + 1))


def capture(state, content, content_type, http_status, *, url, source_type, title, description):
    sha = forensics.capture_source(
        content,
        url=url,
        source_type=source_type,
        title=title,
        description=description,
        content_type=content_type,
        http_status=http_status,
        con=state,
    )
    ext = forensics._MIME_EXT.get(content_type.split(";")[0].strip(), ".bin")
    raw_path = str((config.RAW_DIR / f"{sha}{ext}").relative_to(config.PROJECT_ROOT))
    log.info("  captured -> %s (sha256=%s, %d bytes)", raw_path, sha, len(content))
    return {
        "url": url,
        "title": title,
        "sha256": sha,
        "raw_path": raw_path,
        "content_length": len(content),
        "http_status": http_status,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")

    state = forensics.open_state()
    manifest = load_manifest()
    artifacts = []

    log.info("Fetching %s", POST_URL)
    html_content, html_content_type, html_status = fetch(POST_URL)
    artifacts.append(capture(
        state, html_content, html_content_type, html_status,
        url=POST_CANONICAL_URL,
        source_type="telegram_post",
        title="ssaniaworld channel, post 3348 (23 Oct 2025) -- "
              "eviction enforcement at проспект Ленина, 133, кв. 19 "
              "+ inventory/inspection underway at Черноморская, 10",
        description=(
            "Telegram post by 'Министерство Счастья Сании Денисовой. "
            "Движение - СИЛА ДОБРА' (19.3K views), titled 'Проспект Ленина, "
            "133: людей выкидывают из своих квартир на улицу'. Reports that "
            "court rulings (ownerless designation) for apartments 2, 19, 20, "
            "33 in this building were issued in 2024, and that residents "
            "with registration (прописка) and powers of attorney are now "
            "(Oct 2025) being told to vacate, including a 73-year-old "
            "resident at apt 19 whose apartment was physically sealed "
            "('опечатана') -- see attached photo. Apartment 19 is already a "
            "registry_inclusion seizure_event for property 4442 (id 37362, "
            "address_raw '...Ленина (Мира), 133, 19'). Separately quotes a "
            "subscriber report that Черноморская, 10 is currently undergoing "
            "door-to-door inventory/inspection ('инвентаризация') for "
            "ownerless designation -- no exact 'Черноморская, 10' is on the "
            "spine (closest: Черноморская 1 / 22/10), flagged as a new lead."
        ),
    ))
    time.sleep(REQUEST_PAUSE_S)

    html_text = html_content.decode("utf-8", errors="replace")
    m = PHOTO_URL_RE.search(html_text)
    if not m:
        raise RuntimeError("could not find attached photo URL in post HTML")
    photo_url = m.group(1)

    log.info("Fetching %s", photo_url)
    photo_content, photo_content_type, photo_status = fetch(photo_url)
    artifacts.append(capture(
        state, photo_content, photo_content_type, photo_status,
        url=photo_url,
        source_type="telegram_photo",
        title="Photo attached to ssaniaworld/3348 -- two 'ОПЕЧАТАНО' "
              "(sealed) notices, пр. Ленина д. 133 кв. 19",
        description=(
            "Two official seal notices stacked in one photo, both reading "
            "'Объект является муниципальной собственностью городского "
            "округа Мариуполь ... пр. Ленина д. 133 кв. 19 ... ВХОД СТРОГО "
            "ВОСПРЕЩЁН! ОПЕЧАТАНО Без представителя собственника в лице "
            "Управления имущественных и земельных отношений не вскрывать. "
            "Повреждение запорных устройств, дверей, окон, инженерных "
            "систем объекта, а также несанкционированное проникновение "
            "повлекут ответственность, в том числе статьями 139, 168 "
            "Уголовного кодекса Российской Федерации. Телефон для связи с "
            "представителем собственника: +7 (949) 814-63-64'. Top notice "
            "handwritten 'Освободить до 25.10.2025'; bottom notice "
            "handwritten 'Освободить до 22.10.2025'. First dated "
            "photographic artifact in the project of the physical "
            "enforcement step (sealing + vacate deadline) that follows a "
            "registry_inclusion / ownerless_designation record -- here for "
            "property 4442 (просп. Ленина (Мира), 133), apt 19, already "
            "present as seizure_event id 37362."
        ),
    ))

    manifest["artifacts"] = artifacts
    save_manifest(manifest)
    state.close()
    log.info("Done -> %s", MANIFEST_PATH)


if __name__ == "__main__":
    main()
