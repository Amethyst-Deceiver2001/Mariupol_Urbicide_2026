#!/usr/bin/env python3
"""Register two locally-staged artifacts into the raw store (2026-06-19):

  1. The 1:09-6:42 walkthrough segment of YouTube video pmb7BIl-Atw, cropped
     from the user's already-downloaded full video (no re-download). User:
     "contemporary footage of both destruction and stalled reconstruction
     (area is fenced, but no ongoing construction works visible, consistent
     with the residents' complaints)" -- covers the whole 104/106/108/110
     stretch.
  2. The dnr.red resale listing for пр. Ленина 108 (property_id 4421),
     manually saved as a complete webpage (browser Save As -> zip) by the
     user from /Users/ak/Downloads/Archive.zip, since dnr.red is the same
     anti-bot/geoblocked class as Avito/CIAN (scripts/49/158 policy) --
     Claude never fetches it directly, but capturing an already-locally-saved
     file is a pure local read, no network call. NOTE: the archive contains
     ONLY the dnr.red page (file_122.html, confirmed via its og:url meta
     tag) -- the second target from scripts/158 (dnr.domick.ru) is NOT in
     this archive and is still outstanding.

Capture-before-parse: raw bytes -> data/raw/<sha256>.<ext> + .meta.json,
registered in source_document. No field extraction beyond what's needed for
the description (price/area/floor), no DB writes beyond that.
"""
import logging
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import forensics  # noqa: E402

log = logging.getLogger(__name__)

WALKTHROUGH_VIDEO = "/tmp/pmb7BIl-Atw_walkthrough.mp4"
ARCHIVE_ZIP = "/Users/ak/Downloads/Archive.zip"
DNRRED_OG_URL = (
    "https://dnr.red/mariupol/search/nedvizhimost/prodazha-nedvizhimosti/"
    "prodazha-kvartir/vtorichnyy-rynok/"
    "prodajotsa-3kh-komnatnaja-kvartira-v-centre-goroda-pod-vash-remont-pr-lenina-d108-1506303.html"
)


def find_listing_html(zip_path: str) -> bytes | None:
    """The archive has several HTML files (the listing page plus Omnidesk
    helpdesk-widget iframe stubs); pick the one whose og:url matches the
    dnr.red listing rather than assuming a fixed entry index."""
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".html"):
                continue
            if "__MACOSX" in info.filename:
                continue
            data = z.read(info)
            if DNRRED_OG_URL.encode() in data:
                return data
    return None


def main() -> None:
    con = forensics.open_state()

    # 1) Walkthrough video segment
    video_path = Path(WALKTHROUGH_VIDEO)
    if video_path.exists():
        content = video_path.read_bytes()
        sha = forensics.capture_source(
            content, url="https://www.youtube.com/watch?v=pmb7BIl-Atw",
            source_type="youtube_video_segment",
            title="пр. Ленина/Мира 104-110 walkthrough (1:09-6:42 of "
                  "pmb7BIl-Atw, cropped)",
            description=(
                "User 2026-06-19: 'contemporary footage of both destruction "
                "and stalled reconstruction (area is fenced, but no ongoing "
                "construction works visible, consistent with the residents' "
                "complaints)'. Whole stretch 104/106/108/110. Cropped from "
                "the full video (00:01:09-00:06:42, lossless -c copy) -- the "
                "rest of the original video is outside this case study's "
                "scope. Frames reviewed at 00:01:15/02:15/03:15/04:15 of the "
                "cropped segment: rusty corrugated-metal perimeter fencing "
                "with damaged multi-storey buildings visible behind it; one "
                "frame shows an idle yellow construction hoist/platform "
                "mounted on a facade with no visible workers or active "
                "material staging -- consistent with the halted-work claim "
                "in the CHrEXXI8CK0 resident testimony."
            ),
            content_type="video/mp4", http_status=200, con=con,
        )
        log.info("captured walkthrough video -> sha=%s", sha[:12])
    else:
        log.error("walkthrough video not found at %s", WALKTHROUGH_VIDEO)

    # 2) dnr.red listing page (manually saved, complete webpage zip)
    html = find_listing_html(ARCHIVE_ZIP)
    if html is not None:
        sha2 = forensics.capture_source(
            html, url=DNRRED_OG_URL, source_type="realestate_listing_detail",
            title="dnr.red -- 3-room apartment, пр. Ленина 108",
            description=(
                "Apartment-resale listing for пр. Ленина 108 (property_id "
                "4421), demand-side resale evidence. Manually saved by the "
                "user as a complete webpage (browser Save As -> "
                "Archive.zip) on 2026-06-19, since dnr.red is anti-bot/"
                "geoblocked (same class as Avito/CIAN, scripts/49/158 "
                "policy) -- this capture reads the already-locally-saved "
                "file, no network fetch. Listing text: 3-room apartment, "
                "пр. Ленина д.108, под ваш ремонт (needs renovation), общая "
                "площадь 61.3 m2 (жилая 42.9 m2, кухня 5.3 m2), 4/9 floor, "
                "потолки 2.50 m, балкон 0.8 m2, price 4,500,000 руб (~₽4.5 "
                "млн), listed 2026-06-08. NOTE: this archive contains ONLY "
                "the dnr.red page -- the dnr.domick.ru listing from "
                "scripts/158's second target is still outstanding."
            ),
            content_type="text/html", http_status=200, con=con,
        )
        log.info("captured dnr.red listing -> sha=%s", sha2[:12])
    else:
        log.error("could not find the dnr.red listing HTML in %s", ARCHIVE_ZIP)

    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
