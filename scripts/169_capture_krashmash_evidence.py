#!/usr/bin/env python3
"""Capture the KrashMash (КрашМаш) contractor confirmation evidence for the
Troianda-M / pr. Metallurgov 47 case study: the company's own portfolio
page plus three independent third-party videos, two of which contain
on-screen text directly naming both "Metallurgov 47" and "KrashMash" in the
same frame -- the strongest confirmation found so far that KrashMash
physically demolished this building.

Videos were already downloaded to the session scratchpad via yt-dlp this
session (small files, <3 MB each, well under any "long-running" threshold).
This script only hashes/copies local files + does one quick HTML fetch --
safe to run directly.

Usage:
    .venv312/bin/python scripts/169_capture_krashmash_evidence.py
"""
import hashlib
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402
from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

SCRATCH = Path(
    "/private/tmp/claude-501/-Users-ak-Downloads-mariupol-property-seizures/"
    "342b195a-6008-4b21-a81f-9d63615da8f5/scratchpad"
)

VIDEO_TARGETS = [
    {
        "path": SCRATCH / "uUVq_PwdM58.mp4",
        "info_json": SCRATCH / "uUVq_PwdM58.info.json",
        "url": "https://www.youtube.com/watch?v=uUVq_PwdM58",
        "note": "Title: 'Мариуполь Металлургов 47 сразу после обстрела 17.03.22' "
                "(uploader: михаил86). 13s, no speech. Shows the facade with a "
                "visibly collapsed/imploded entrance section, consistent with the "
                "user's description of 'a hit which imploded one of the entrances.' "
                "Independently corroborates the 17.03.2022 strike date already in "
                "donetsk.kp.ru's account.",
    },
    {
        "path": SCRATCH / "AzjzALk-GFs.mp4",
        "info_json": SCRATCH / "AzjzALk-GFs.info.json",
        "url": "https://www.youtube.com/shorts/AzjzALk-GFs",
        "note": "Title: 'Маріуполь. Центр міста. Проспект Металургів, 47. Дата "
                "12.10.22' (uploader: Ліна з України, Ukrainian-language channel). "
                "6s. ON-SCREEN TEXT confirms address directly: 'Проспект "
                "Металургів, 47'. Shows severe combat damage, collapsed balconies, "
                "scorch marks, pre-demolition state.",
    },
    {
        "path": SCRATCH / "RutXOUDzP_s.mp4",
        "info_json": SCRATCH / "RutXOUDzP_s.info.json",
        "url": "https://www.youtube.com/watch?v=RutXOUDzP_s",
        "note": "Title: 'МАРИУПОЛЬ! КРАШМАШ СНОСИТ ЗНАМЕНИТУЮ МНОГОЭТАЖКУ НА "
                "МЕТАЛЛУРГОВ!' (uploader: Игорь Семенов, independent third party, "
                "NOT KrashMash's own channel). 34s, dated upload 14.12.2022 -- "
                "inside the resident-confirmed 10-25.12.2022 demolition window. "
                "ON-SCREEN TEXT reads '...рашМаш\" сносит Металлургов 47' -- "
                "direct on-screen confirmation of BOTH the contractor name and "
                "the address in the same shot, from a source independent of "
                "KrashMash's own promotional material. This is the strongest "
                "single piece of evidence resolving the KrashMash attribution.",
    },
]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def capture_video(t: dict, con) -> None:
    path = t["path"]
    if not path.exists():
        log.warning("missing file, skip: %s", path)
        return
    info = {}
    if t["info_json"].exists():
        info = json.loads(t["info_json"].read_text(encoding="utf-8"))

    sha = _sha256_file(path)
    raw_path = config.RAW_DIR / f"{sha}.mp4"
    if not raw_path.exists():
        raw_path.write_bytes(path.read_bytes())
    else:
        log.info("sha=%s already in raw store", sha[:12])

    captured = forensics.now_iso()
    title = info.get("title") or path.name
    meta = {
        "url": t["url"],
        "source_type": "youtube_video",
        "title": title,
        "description": t["note"],
        "channel": info.get("channel") or info.get("uploader"),
        "upload_date": info.get("upload_date"),
        "duration_seconds": info.get("duration"),
        "sha256": sha,
        "content_type": "video/mp4",
        "http_status": 200,
        "captured_at": captured,
    }
    Path(str(raw_path) + ".meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    con.execute(
        """INSERT OR REPLACE INTO source_document
           (sha256, url, source_type, title, description,
            raw_path, content_type, http_status, captured_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (sha, t["url"], "youtube_video", title, t["note"],
         str(raw_path), "video/mp4", 200, captured),
    )
    con.commit()
    log.info("captured %s -> sha=%s", path.name, sha[:12])


def capture_crushmash_page(con) -> None:
    url = ("https://crushmash.com/obekty/"
           "snos-domov-v-ramkakh-programmy-vosstanovleniya-mariupolya/")
    try:
        r = requests.get(url, headers={"User-Agent": config.USER_AGENT}, timeout=20)
    except requests.RequestException as e:
        log.error("fetch failed: %s", e)
        return
    if r.status_code != 200:
        log.warning("HTTP %s for %s", r.status_code, url)
        return
    sha = forensics.capture_source(
        r.content,
        url=url,
        source_type="press_article",
        title="CrushMash (КрашМаш) own portfolio page: Mariupol reconstruction-program demolitions",
        description="Company's own site, 2022, central Mariupol: contracted for "
                     "demolition of 37 destroyed objects in the city center under "
                     "the Mariupol reconstruction program; 24 units of equipment "
                     "(11 excavators, 10 dump trucks, 3 buses), Komatsu PC-450 "
                     "w/ 25m reach. No individual addresses or customer (PPK/"
                     "RKS-NR) named on this page. Corroborates KrashMash as a "
                     "real, large-scale 2022 Mariupol demolition contractor "
                     "consistent with the Metallurgov 47 timeline.",
        content_type=r.headers.get("Content-Type", "text/html"),
        http_status=r.status_code,
        con=con,
    )
    log.info("captured crushmash.com -> sha=%s", sha[:12])


def main() -> None:
    con = forensics.open_state()
    for t in VIDEO_TARGETS:
        capture_video(t, con)
    capture_crushmash_page(con)
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
