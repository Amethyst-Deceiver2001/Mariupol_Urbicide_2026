#!/usr/bin/env python3
"""Assemble a designer-ready visual evidence package for the пр. Ленина
104/106/108/110 restoration-without-restitution case study.

Pulls already-captured (SHA-256-hashed, forensically chained) media and
documents out of the raw store and into a clean, stage-organized folder a
designer can work from directly -- real image/video bytes with sensible
filenames, not just hashes/URLs.

Sources combined:
  - script 151's classified media_lifecycle_manifest.jsonl entries for the
    @Lenina106_Mariupol chat (resident_presence/demolition/construction/
    new_build -- "siege_damage" is excluded wholesale, see
    memory/lifecycle_classifier_unreliable_siege_damage.md; "demolition"
    excludes the single known negation false-positive, see
    memory/negation_blind_classifier_caveat.md)
  - ALL chat media (classified or not) whose parent message text mentions
    "104", "108", or "110" specifically, so house-number-specific photos
    aren't lost just because they didn't trip a lifecycle keyword
  - the two key documents already in chat_document_inventory.jsonl: the
    residents' joint letter to Putin/Минстрой/прокурор/мэр, and the scanned
    court ruling
  - a one-page README per building summarizing the decree + registry +
    corroboration facts so the designer has the citation text alongside
    the imagery

Pure local copy from data/raw/ -- no network, no DB writes. Safe to run.

Output:
  data/exports/designer_package/lenina_104_106_108_110/
    104/ 106/ 108/ 110/ shared/
    manifest.csv
    README.md
"""
import csv
import json
import logging
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402

log = logging.getLogger(__name__)

OUT_DIR = ROOT / "data" / "exports" / "designer_package" / "lenina_104_106_108_110"
MEDIA_MANIFEST = ROOT / "data" / "parsed" / "media_lifecycle_manifest.jsonl"
DOC_INVENTORY = ROOT / "data" / "parsed" / "chat_document_inventory.jsonl"
CHAT_SLUG = "Lenina106_Mariupol"

# known classifier false positives (see memory/negation_blind_classifier_caveat.md
# and memory/lifecycle_classifier_unreliable_siege_damage.md). msg 37 is the
# "не сносили" negation false-positive (demolition). Manual review (2026-06-19)
# additionally found every "siege_damage"-stage hit for this chat (msgs 58, 97,
# 98, 100) was wrong -- repair-work footage or unrelated video, none of it
# wartime destruction -- so that stage is excluded wholesale rather than
# spot-excluded by id; do not re-enable without per-file manual verification.
# msgs 97/98 are fully dropped (not just destaged): their caption is a generic
# "inspected several buildings in Жовтневый district" photo-op, not imagery of
# any one building, despite the digit regex matching all four house numbers
# somewhere in the (truncated-in-manifest) text -- without this they'd still
# get pulled into 104/108/110 via gather_house_specific_media() even with
# siege_damage excluded above. msg 100's video was confirmed unrelated to this
# building chain entirely. msg 58 stays (it's genuinely about house 106, see
# its house_specific caption "Ленина 106"), just no longer tagged siege_damage.
#
# Second manual-review pass (2026-06-19) found the "construction" stage is
# ALSO mixed: msg 148 is a satirical video about shoddy construction in
# general (no building-specific content -- the classifier has no way to
# detect "this is a joke", flagged here as a known hard case rather than a
# fixable bug), and msgs 949/950/951 are off-topic Telegram-app-settings
# screenshots that happened to land in the construction bucket. All four
# dropped entirely; the *non*-flagged construction items (2023-10-05,
# 2023-10-18) were specifically reviewed and kept.
#
# Third manual-review pass (2026-06-19) found MORE wrong items, including in
# already-"reviewed" construction (msg 87 turned out to be the SAME kind of
# unrelated satirical video as msg 148, despite its caption text appearing to
# reference the residents' letter -- captions are not reliable proxies for
# actual video content, always watch the file): msg 42 is a missing-person
# search post, not a building photo; msgs 269/1155/1157 are off-topic resident
# chatter (one's generic DNR-wide news about water-barrel freezing, reused
# near-verbatim for both 1155 and 1157); msgs 1113-1116 show real repair work
# but the building can't be confirmed as 106 specifically -- a perpendicular
# building visible in the background could place it at 104 or 110 instead, so
# all four are dropped for unconfirmed building attribution rather than kept
# as "106" on a guess. After three passes the only stage classifier label
# left with ANY confirmed-correct content for this chat is the bare presence
# of a caption keyword -- always verify before trusting any of it.
#
# Fourth manual-review pass (2026-06-19) found two more "resident_presence"
# items unrelated to the building itself: msg 733 is another missing-person
# search post (same pattern as msg 42); msg 838 is a contact sheet for the
# pre-war Комитет самоорганизации населения (КСН) residents' association --
# real artifact, just not building-condition evidence for this case study.
# Confirmed GOOD in this pass (kept, no action needed): msg 195 (repair video,
# independently cross-confirmed via https://t.me/BLMariupol/3481) and msg 298
# (door notice announcing repair start, posted to the chat 2024-04-27).
#
# CORRECTION (2026-06-19, after a 5th pass): msg 269 was wrongly excluded in
# the third pass on the strength of a caption that turned out to belong to a
# DIFFERENT, adjacent message -- script 151's manifest mis-associated the
# caption text. The real caption (data/raw/<sha>.jpg.meta.json) is "На каждой
# двери" ("on every door"), and the photo itself, manually re-verified, IS the
# Распоряжение №619 door notice -- exactly what it should be. Lesson on top of
# the existing lesson: even the *caption-association*, not just caption
# accuracy, can be wrong; always check the raw .meta.json, not the manifest's
# excerpt. msg 269 is excluded from the classified/regex pipeline here
# (where it would still surface mislabeled as "resident_presence" under the
# wrong caption) and added to MANUAL_INCLUDES instead, with the correct
# caption and stage -- one copy, correctly labeled, not a mislabeled duplicate.
EXCLUDE_MSG_IDS = {37, 42, 87, 97, 98, 100, 148, 269, 733, 838, 949, 950, 951,
                   1113, 1114, 1115, 1116, 1155, 1157}
EXCLUDE_STAGES = {"siege_damage"}
# content is legitimate (repair-quality footage genuinely about house 106)
# but the classifier also duplicated it into resident_presence, which is the
# wrong bucket for "repair quality" content -- keep only the house_specific
# copy produced by gather_house_specific_media().
EXCLUDE_FROM_CLASSIFIED = {195}

# High-value artifacts identified and manually verified by direct file
# inspection (not caption, not stage label) -- bypass all classifier/regex
# logic and copy by exact (sha256, url) regardless of stage/caption state.
# msg 986 is "unclassified" with no caption at all (a resident's handwritten
# complaint to the occupation prosecutor re: stalled ФКРМО repairs, posted
# 2025-06-02); msg 269 is the Распоряжение №619 door notice (2024-03-27, see
# correction note above).
MANUAL_INCLUDES = [
    {"msg_id": 986, "url": "https://t.me/Lenina106_Mariupol/986/media",
     "sha256": "74b97bb3bd17453278e576e10f837e9c97bbcbe441e97ff080862a18997bde05",
     "date": "2025-06-02", "stem": "2025-06-02_prosecutor_complaint_fkrmo",
     "caption": "Handwritten complaint to Мариуполь prosecutor (Гнездилов Д.В.) "
                 "re: ФКРМО repeatedly delaying then abandoning repair works "
                 "at пр. Ленина 106 since August 2024"},
    {"msg_id": 269, "url": "https://t.me/Lenina106_Mariupol/269/media",
     "sha256": "1ca8ed3de0ed51f104912668c3e75468d828b82b63b50846a93506d361627e05",
     "date": "2024-03-27", "stem": "2024-03-27_decree619_door_notice",
     "caption": "На каждой двери -- Уведомление citing Распоряжение №619 "
                 "(12.10.2023): residents must submit title documents to "
                 "МУП АГМ «Мариупольжилкомплекс» by 01.03.24"},
]

# YouTube videos captured via scripts/157 (2026-06-19), individually watched
# frame-by-frame and verified before inclusion -- NOT trusted on title alone.
# One candidate (shorts/S0HfD_lkeEk, sha 27aea723...) was EXCLUDED despite a
# title mentioning house numbers 104/106: its title says "Победы, 104 и 106"
# (просп. Победы / Victory Avenue), a DIFFERENT street from Ленина/Мира that
# coincidentally shares house numbers -- a title-trust failure mode distinct
# from the Telegram caption bugs documented elsewhere, see
# memory/lifecycle_classifier_unreliable_siege_damage.md. Real siege damage,
# wrong building -- not included anywhere in this package.
YOUTUBE_INCLUDES = [
    {"building": "104", "folder": "verified_siege_damage", "url": "https://www.youtube.com/watch?v=0ryoGHihIaY",
     "sha256": "3215e47c68eca7810b7a395765ed0255be2e22cc888942c2b8157feee604d8f5",
     "date": "2022-03-04", "stem": "2022-03-04_siege_damage_groundfloor",
     "caption": "Ground-floor commercial storefront (dental clinic signage), blast-"
                 "shattered windows and frame, пр. Миру/Ленина 104. Title: "
                 "'2022.03.04 - пр. Миру, буд. 104'. Channel: Near You."},
    {"building": "104", "folder": "verified_siege_damage", "url": "https://www.youtube.com/shorts/5fuqt-M5S6I",
     "sha256": "b1313dae503ed4af7729871d8356ab609e85b30ae488f11043e1a8ab69fc9822",
     "date": "2022-05", "stem": "2022-05_siege_damage_facade",
     "caption": "Full facade, multiple floors with fire-scorched/blown-out windows "
                 "and balconies. Title: 'Мариуполь. Проспект Мира, 104. Май 22г.'"},
    {"building": "106", "folder": "verified_siege_damage", "url": "https://www.youtube.com/watch?v=oPTXL9Gluq0",
     "sha256": "b32d154454c3d55b8e5f6960d8d71be771a5d857474acfcc2d432f0109506a2c",
     "date": "2022-06-25", "stem": "2022-06-25_siege_damage_former_atb",
     "caption": "Destroyed ground-floor former 'АТБ' supermarket space, ATM/blast "
                 "debris visible. Title: 'Мариуполь. Мира, 106, бывший АТБ. "
                 "25 июня 22г.' (@MARIUPOLNOW watermark)."},
    {"building": "106", "folder": "verified_siege_damage", "url": "https://www.youtube.com/watch?v=QBS9qOT-_RM",
     "sha256": "c7ffa6b0a7baa14d6d8dd92fe78c37cc50920db21effe9d74f41d15e1ba8d18c",
     "date": "2022-05", "stem": "2022-05_siege_damage_balconies",
     "caption": "Burnt-out upper-floor balconies/apartments. Title: 'Мариуполь. "
                 "Пр-т Мира, 106. Май 22г.'"},
    {"building": "108", "folder": "demolition", "url": "https://youtube.com/shorts/Bzq5QnarNAo",
     "sha256": "ea5353981a2cfd625abdceebeffc02df4bf3d5f6ad8515021353e2472bb3ccab",
     "date": None, "stem": "demolition_one_entrance_partial",
     "caption": "Long-reach excavator actively demolishing ONE entrance/section "
                 "of the building -- the rest of the tower (visible to the right, "
                 "intact windows/balconies) is standing. REVISES the case study: "
                 "108 was not left entirely undemolished -- a partial demolition "
                 "did occur even as the remainder underwent the registry-"
                 "stripping/restoration track documented elsewhere. Title: "
                 "'Мариуполь. Пр-т Мира, 108, снос дома'."},
    {"building": "shared", "manifest_buildings": "104,106,108,110",
     "folder": "verified_siege_damage",
     "url": "https://www.youtube.com/watch?v=iDKIvw-2q_c",
     "sha256": "2b3b4e85f98dc37d3ded9be6c033acdfca6daeb0d0a66e60a7153e699cf7f2bd",
     "date": "2023-02-22", "stem": "2023-02-22_siege_damage_104_110_stretch",
     "caption": "Contemporaneous (snow on ground) siege-destruction footage of "
                 "the whole 104-110 stretch -- burnt facades, blown-out "
                 "balconies/windows, one collapsed/sheared tower corner. "
                 "Title: 'Mariupol Lenina(Mira) 104-110. And they want to "
                 "restore it' (channel: Mariupol After). The 'restore it' "
                 "framing is the uploader's own editorializing, not shown "
                 "in-frame -- do not cite this video for restoration status, "
                 "only for the dated destruction it actually depicts."},
    {"building": "shared", "manifest_buildings": "104,106,108,110",
     "folder": "resident_testimony",
     "url": "https://www.youtube.com/watch?v=CHrEXXI8CK0",
     "sha256": "a8e0e253f2b25265f4f23c097d8347108f725f2d246a3da9ff41b7110ecf4934",
     "date": None, "stem": "resident_testimony_to_camera",
     "caption": "Residents of пр. Ленина 104/106/108/110 address the camera "
                 "directly, naming the same contractor/agency chain already "
                 "in stakeholder_network/this case study (ППК «Единый "
                 "заказчик», ФКР Московской области, РКС-НР, департамент "
                 "капстроительства г. Мариуполя, администрация МО ГО "
                 "Мариуполь). Claims: facade work done but interiors in "
                 "'complete ruin', restoration work HALTED with no "
                 "explanation, repeated new subcontractors who do nothing, "
                 "ground-floor commercial units ALREADY let to a bank/flower "
                 "shop/pelmennaya while residents can't access their own "
                 "apartments, apartment square footage/wall layout altered "
                 "during works ('квадратура изменилась'), residents in their "
                 "4th year without housing, signatures collected and formal "
                 "complaints sent to Следственный комитет РФ, "
                 "Администрация президента РФ, Прокуратура РФ, прокуратура "
                 "Мариуполя, администрация ГО Мариуполь, департамент "
                 "строительного управления. First on-camera resident "
                 "testimony video for this building group (existing "
                 "testimony was text-only or door-notice photos)."},
    {"building": "shared", "manifest_buildings": "104,106,108,110",
     "folder": "stalled_reconstruction",
     "url": "https://www.youtube.com/watch?v=pmb7BIl-Atw",
     "sha256": "8867e667f405e722aa2e7fe6a18bf639ef355a942dde7e9c38bad019e5e9b117",
     "date": None, "stem": "walkthrough_104_106_108_110_stalled_reconstruction",
     "caption": "Walkthrough of the whole 104/106/108/110 stretch (cropped "
                 "to 1:09-6:42 of the original video -- the rest is out of "
                 "scope). User 2026-06-19: 'contemporary footage of both "
                 "destruction and stalled reconstruction (area is fenced, "
                 "but no ongoing construction works visible, consistent "
                 "with the residents' complaints)'. Rusty corrugated-metal "
                 "perimeter fencing around damaged buildings; one frame "
                 "shows an idle yellow construction hoist/platform mounted "
                 "on a facade with no visible workers or material staging -- "
                 "directly corroborates the halted-work claim in the "
                 "CHrEXXI8CK0 resident testimony above."},
]

# Non-chat, non-YouTube artifacts (Pastvu, real-estate resale channels) --
# same bypass-the-classifier discipline, captured by scripts/159 (2026-06-19).
# Lesson from that capture run: the t.me ?embed=1 widget's HTML is NOT
# byte-stable across requests (each fetch gets a fresh sha, likely a
# per-request token in the page) -- always use the LATEST sha for a given
# logical post, since older shas may carry a stale/uncorrected description
# even though the bytes are still validly captured and immutable.
EXTERNAL_INCLUDES = [
    {"building": "110", "folder": "prewar_baseline", "kind": "image",
     "sha256": "10d33e2830c7b730e15c0e5519feae1a08ce489abafd2270f11c122a313dc821",
     "date": "1979", "stem": "1979_prewar_baseline_pastvu",
     "caption": "Pastvu p/1167758 -- 9-storey Soviet apartment block, "
                 "geotagged ~25m from property 4423 (пр. Ленина 110). "
                 "Confirmed by the user (2026-06-19) as 110. First "
                 "prewar-baseline imagery in the package for any of the "
                 "four buildings, ~43 years before the siege."},
    {"building": "106", "folder": "resale_listings", "kind": "document",
     "sha256": "2537366da4c56cf8c0622170bc82e9805fc7d0613cf7acb8a6751558bef8c45c",
     "date": "2024-01-24", "stem": "2024-01-24_resale_listing_106_partial_capture",
     "caption": "t.me/Mariupol_house/84850 (forwarded from 'Мир "
                 "мариупольской недвижимости', Сергей). Widget capture is "
                 "metadata-only (channel/date/link) -- the album itself is "
                 "'Service message / media not supported'. Listing content "
                 "per the user's screenshot (2026-06-19): 2-room apt with "
                 "'переход' (extra room), 4/9 floor, 47.8/26.3/6.3 m², "
                 "пр. Ленина 106, full contractor renovation, внесена в "
                 "Росреестр, 5 млн ₽ торг, +7(949)70-69-167. First direct "
                 "demand-side resale evidence for 106."},
    {"building": "110", "folder": "resale_listings", "kind": "document",
     "sha256": "5a9171bd2faab3f682e2689f77403fe593397a98e214a7701bde3796b700aaa0",
     "date": "2025-12-29", "stem": "2025-12-29_resale_listing_110_partial_capture",
     "caption": "t.me/Mariupol_house/676643 (channel 'Недвижимость - "
                 "Мариуполь'). Widget capture is metadata-only -- same "
                 "'media not supported' limitation. CORRECTED (2026-06-19): "
                 "this case study's earlier memory note had guessed this "
                 "listing was for 108 by inference, before the content was "
                 "seen; the user has now confirmed via screenshot it is "
                 "пр. Ленина 110 -- 3-room, 63.4 m², floor 7/9, 'под "
                 "ремонт', new wiring/water/gas/floor screed, поставлена в "
                 "Росреестр (один собственник), price reduced to 3 млн руб, "
                 "+79495584140."},
    {"building": "108", "folder": "resale_listings", "kind": "document",
     "sha256": "53a2850be31878ac1ebfb1daed164f77be0fbf285f06b223170b764d550f628b",
     "date": "2026-06-08", "stem": "2026-06-08_resale_listing_108_dnrred",
     "caption": "dnr.red listing, пр. Ленина 108 (property_id 4421) -- 3-room "
                 "apartment, под ваш ремонт (needs renovation), общая "
                 "площадь 61.3 m2 (жилая 42.9 m2, кухня 5.3 m2), 4/9 floor, "
                 "потолки 2.50 m, балкон 0.8 m2, 4,500,000 руб. Manually "
                 "saved by the user (browser Save As, complete webpage) "
                 "since dnr.red is anti-bot/geoblocked -- same class as "
                 "Avito/CIAN (scripts/49/158 policy). The companion "
                 "dnr.domick.ru listing (scripts/158's other target) is "
                 "still outstanding -- not in this capture."},
]

# Same hand-verification discipline as YOUTUBE_INCLUDES, but only ONE frame of
# the source video is on-topic for this case study -- the rest documents an
# ADJACENT, unrelated building, so the frame is extracted directly via ffmpeg
# rather than copying the whole video in. The full video stays in data/raw/
# (sha256 below) as a lead for a future case study, not re-copied here.
#
# JHN1KrWgliE ("Мариуполь. Город-призрак!? пр-т Ленина,108.", Korzhov Vlog,
# 2023-08-23) walks the vlogger from a "corner of дом 110" past Зелинского 33
# into 108's courtyard. Per the user's transcript review (2026-06-19): at
# 2:49 he says "я нахожусь на углу дома номер 110", but at 3:09 ("кран
# работает у дома номер 110") the crane he's pointing at is visibly turned
# toward Зелинского 33's own under-construction tower, not 110 -- confirmed
# by his very next line at 3:21, "зашел во двор Зелинского 33, дом частично
# начали восстанавливать". That whole corner/crane segment (~2:45-3:30) is
# Зелинского 33, a different street entirely, and is NOT used here. Later,
# at 4:35, he explicitly names "дом номер 108" and says from the courtyard
# "отсюда видно что дом восстанавливают, ближе я не смогу подойти" -- a
# genuinely address-explicit, dated (2023-08-23), if distant/back-side, view
# of 108 with restoration activity stated as visible. That single frame is
# the only usable artifact from this video for this case study.
YOUTUBE_FRAME_INCLUDES = [
    {"building": "108", "folder": "verified_restoration",
     "video_sha256": "4cb9fe0fc71265a82509a15d18d02dd0f66e70fd2a89a003b8188acc4f961173",
     "timestamp": "00:04:46", "date": "2023-08-23",
     "stem": "2023-08-23_108_distant_restoration_view",
     "caption": "Distant/back-side view of 108 from an adjacent overgrown "
                 "courtyard, fenced/inaccessible up close. Vlogger on-camera: "
                 "'Итак друзья дом номер 108... отсюда видно что дом "
                 "восстанавливают, ближе я не смогу подойти, везде кусты "
                 "заросли и заборы'. Source: Korzhov Vlog, 'Мариуполь. "
                 "Город-призрак!? пр-т Ленина,108.', 2023-08-23 "
                 "(sha 4cb9fe0f...). NOTE: the same video's earlier "
                 "crane/construction segment (~2:45-3:30) is Зелинского 33, "
                 "a different building/street, and is deliberately excluded "
                 "-- see comment above."},
]

# fzN0pI8alEY ("contemporary courtyard siege-damage footage, 104 and 106",
# user 2026-06-19) -- whole video not copied in (it also pans across
# unrelated stretches between the cited segments); these are the user-cited,
# individually frame-reviewed timestamps. video_sha256 captured locally via
# scripts/160_capture_local_youtube_downloads.py (already downloaded to /tmp
# for manual review before this script existed -- no re-download).
_FZN0PI8ALEY_SHA = "867ab4986642487e053f85c23840486a40c4834c644bbe5e4cc089c398749ae7"
YOUTUBE_FRAME_INCLUDES += [
    {"building": "104", "folder": "verified_siege_damage",
     "video_sha256": _FZN0PI8ALEY_SHA,
     "timestamp": "00:00:12", "date": None,
     "stem": "courtyard_siege_damage_a",
     "caption": "Courtyard-side view, 104: burnt/blown-out balconies, "
                 "blast-torn brick, hanging A/C units. User-cited segment "
                 "0:10-0:20. Second independent siege-destruction source for "
                 "104 (after iDKIvw-2q_c's street-facade shots), first from "
                 "the rear/courtyard side."},
    {"building": "104", "folder": "verified_siege_damage",
     "video_sha256": _FZN0PI8ALEY_SHA,
     "timestamp": "00:00:46", "date": None,
     "stem": "courtyard_siege_damage_b",
     "caption": "Courtyard-side view, 104: close-range burnt facade, "
                 "sheared balcony rail, bicycle hanging from wrecked "
                 "balcony. User-cited segment 0:43-1:02."},
    {"building": "104", "folder": "verified_siege_damage",
     "video_sha256": _FZN0PI8ALEY_SHA,
     "timestamp": "00:01:00", "date": None,
     "stem": "courtyard_siege_damage_c",
     "caption": "Courtyard-side view, 104: wider-angle multi-floor damage, "
                 "tall tower section with blown-out windows. User-cited "
                 "segment 0:43-1:02."},
    {"building": "104", "folder": "resident_presence",
     "video_sha256": _FZN0PI8ALEY_SHA,
     "timestamp": "00:03:39", "date": None,
     "stem": "makeshift_brick_kitchen",
     "caption": "Makeshift brick outdoor hearth by a building doorway -- "
                 "residents still living/cooking on-site amid the ruins. "
                 "User-cited timestamp 3:39."},
    {"building": "106", "folder": "verified_siege_damage",
     "video_sha256": _FZN0PI8ALEY_SHA,
     "timestamp": "00:04:15", "date": None,
     "stem": "courtyard_view_106",
     "caption": "Street/courtyard-level view, 106: shuttered storefront and "
                 "entrance in foreground, damaged upper-floor balconies "
                 "visible in the background through trees. Visibly less "
                 "severe than the 104 shots above, consistent with 106's "
                 "documented restored-not-razed status. User-cited segment "
                 "4:02-4:21."},
]

BUILDING_NUMS = ["104", "106", "108", "110"]
HOUSE_RX = {n: re.compile(rf"(?<!\d){n}(?!\d)") for n in BUILDING_NUMS}

PROPERTY_IDS = {"104": 4417, "106": 4419, "108": 4421, "110": 4423}


def _slug_of(url: str) -> str:
    return url.split("/")[3]


def _msg_id_of(url: str) -> int | None:
    try:
        return int(url.rstrip("/").split("/")[-1])
    except (ValueError, IndexError):
        return None


def _sniff_ext(path: Path) -> str | None:
    """Magic-byte fallback for files whose capture-time content_type didn't
    map to a real extension (Telegram video downloads in particular land as
    .bin) -- a designer needs a real playable filename, not a hash+.bin."""
    head = path.open("rb").read(16)
    if head[4:8] == b"ftyp":
        return ".mp4"
    if head[:4] == b"\x1aE\xdf\xa3":
        return ".webm"
    if head[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if head[:4] == b"%PDF":
        return ".pdf"
    return None


def _copy_media(sha: str, raw_path: str, dest_dir: Path, fname_stem: str) -> str | None:
    src = Path(raw_path)
    if not src.exists():
        log.warning("missing raw file for sha=%s (%s)", sha[:12], raw_path)
        return None
    ext = src.suffix
    if not ext or ext == ".bin":
        ext = _sniff_ext(src) or ext or ".bin"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{fname_stem}{ext}"
    n = 1
    while dest.exists():
        dest = dest_dir / f"{fname_stem}_{n}{ext}"
        n += 1
    shutil.copy2(src, dest)
    return str(dest.relative_to(OUT_DIR))


def gather_classified_media():
    """media_lifecycle_manifest rows for the chat, stage != unclassified."""
    out = []
    if not MEDIA_MANIFEST.exists():
        log.warning("missing %s -- run script 151 first", MEDIA_MANIFEST)
        return out
    for line in MEDIA_MANIFEST.open(encoding="utf-8"):
        d = json.loads(line)
        if d["chat"] != CHAT_SLUG or d["stage"] in ("unclassified", *EXCLUDE_STAGES):
            continue
        for it in d["items"]:
            if it.get("kind") not in ("image", "video"):
                continue  # documents (PDF/xlsx) are handled separately by gather_docs()
            mid = _msg_id_of(it["url"].replace("/media", ""))
            if mid in EXCLUDE_MSG_IDS or mid in EXCLUDE_FROM_CLASSIFIED:
                continue
            out.append({**it, "stage": d["stage"]})
    return out


def gather_manual_includes(con):
    """Bypass the classifier/regex pipeline entirely for MANUAL_INCLUDES --
    these were verified by directly opening the raw file, not by trusting
    any caption or stage label."""
    out = []
    for item in MANUAL_INCLUDES:
        row = con.execute(
            "SELECT raw_path FROM source_document WHERE sha256=?", (item["sha256"],)
        ).fetchone()
        if not row or not row[0]:
            log.warning("manual include sha=%s not found in raw store", item["sha256"][:12])
            continue
        out.append({**item, "raw_path": row[0]})
    return out


def gather_youtube_includes(con):
    """Same bypass mechanism as gather_manual_includes(), for YOUTUBE_INCLUDES
    -- each was watched frame-by-frame and verified, not trusted on title or
    metadata alone (see the Победы/Pobedy exclusion note above YOUTUBE_INCLUDES)."""
    out = []
    for item in YOUTUBE_INCLUDES:
        row = con.execute(
            "SELECT raw_path FROM source_document WHERE sha256=?", (item["sha256"],)
        ).fetchone()
        if not row or not row[0]:
            log.warning("youtube include sha=%s not found in raw store", item["sha256"][:12])
            continue
        out.append({**item, "raw_path": row[0]})
    return out


def gather_external_includes(con):
    """Same bypass mechanism as gather_manual_includes(), for EXTERNAL_INCLUDES
    (Pastvu, resale-channel captures) -- non-chat, non-YouTube sources."""
    out = []
    for item in EXTERNAL_INCLUDES:
        row = con.execute(
            "SELECT raw_path FROM source_document WHERE sha256=?", (item["sha256"],)
        ).fetchone()
        if not row or not row[0]:
            log.warning("external include sha=%s not found in raw store", item["sha256"][:12])
            continue
        out.append({**item, "raw_path": row[0]})
    return out


def gather_youtube_frame_includes(con):
    """Same bypass mechanism as gather_youtube_includes(), but resolves the
    raw_path of the SOURCE VIDEO so a single frame can be extracted from it
    -- the video itself is not copied into the package (see
    YOUTUBE_FRAME_INCLUDES comment for why)."""
    out = []
    for item in YOUTUBE_FRAME_INCLUDES:
        row = con.execute(
            "SELECT raw_path FROM source_document WHERE sha256=?",
            (item["video_sha256"],),
        ).fetchone()
        if not row or not row[0]:
            log.warning("youtube frame include video sha=%s not found in raw store",
                        item["video_sha256"][:12])
            continue
        out.append({**item, "raw_path": row[0]})
    return out


def gather_house_specific_media(con):
    """ALL chat media (any stage, even unclassified) whose parent caption
    mentions a specific house number -- catches building-specific photos the
    lifecycle classifier didn't tag at all."""
    msg_rows = con.execute(
        "SELECT url, raw_path FROM source_document "
        "WHERE source_type='telegram_building_chat_msg' AND url LIKE ?",
        (f"https://t.me/{CHAT_SLUG}/%",),
    ).fetchall()
    captions = {}
    for url, raw_path in msg_rows:
        if not raw_path:
            continue
        p = ROOT / Path(raw_path) if not Path(raw_path).is_absolute() else Path(raw_path)
        if not p.exists():
            continue
        try:
            obj = json.loads(p.read_bytes())
        except Exception:
            continue
        mid = obj.get("id")
        if mid is None:
            continue
        captions[mid] = {"text": (obj.get("message") or "").strip(),
                          "date": (obj.get("date") or "")[:10]}

    media_rows = con.execute(
        "SELECT url, sha256, raw_path, content_type FROM source_document "
        "WHERE source_type='telegram_building_chat_media' AND url LIKE ?",
        (f"https://t.me/{CHAT_SLUG}/%",),
    ).fetchall()

    out = defaultdict(list)  # house_num -> list of media dicts
    for url, sha, raw_path, ct in media_rows:
        if not (ct or "").startswith(("image/", "video/")):
            continue  # documents (PDF/xlsx) are handled separately by gather_docs()
        parent_url = url.replace("/media", "")
        mid = _msg_id_of(parent_url)
        if mid in EXCLUDE_MSG_IDS or mid not in captions:
            continue
        text = captions[mid]["text"]
        for num, rx in HOUSE_RX.items():
            if rx.search(text):
                out[num].append({
                    "url": url, "sha256": sha, "raw_path": raw_path,
                    "date": captions[mid]["date"], "caption_excerpt": text[:200],
                    "kind": "video" if "video" in (ct or "") else "image",
                })
    return out


# named explicitly because they're cited in the case study's provenance
# table but captured from a DIFFERENT chat than @Lenina106_Mariupol (the
# official-info channel), so the chat-scoped court_ruling filter misses them.
NAMED_DOCS = {"Письмо в инстанции.pdf", "Reshenie_I_3_3_ot_13.02.2026.pdf"}


def gather_docs():
    seen_sha, out = set(), []
    if not DOC_INVENTORY.exists():
        return out
    for line in DOC_INVENTORY.open(encoding="utf-8"):
        d = json.loads(line)
        is_match = ((d["chat"] == CHAT_SLUG and d["category"] == "court_ruling")
                    or d.get("filename") in NAMED_DOCS)
        if is_match and d["sha256"] not in seen_sha:
            seen_sha.add(d["sha256"])
            out.append(d)
    return out


def building_brief(num: str, cur) -> str:
    pid = PROPERTY_IDS[num]
    cur.execute("SELECT occupation_address, prewar_address, rd4u_category, "
                "ST_X(geom), ST_Y(geom) FROM property WHERE id=%s", (pid,))
    addr, prewar, rd4u, lon, lat = cur.fetchone()
    cur.execute("SELECT stage, event_date, detail FROM seizure_event "
                "WHERE property_id=%s AND stage='demolition'", (pid,))
    demo = cur.fetchone()
    cur.execute("SELECT count(*) FROM seizure_event WHERE property_id=%s "
                "AND stage='registry_inclusion'", (pid,))
    n_reg = cur.fetchone()[0]
    cur.execute("SELECT kind, count(*) FROM corroboration WHERE property_id=%s "
                "GROUP BY kind", (pid,))
    corro = cur.fetchall()

    lines = [f"# {addr} (property_id={pid})", "",
             f"- Prewar address: {prewar or '(none on file)'}",
             f"- RD4U category: {rd4u}",
             f"- Coordinates: {lat}, {lon}" if lat else "- Coordinates: not geocoded",
             f"- Demolition decree: {demo[2].get('order_reference_raw') if demo else '(none)'}"
             f" ({demo[1] if demo else ''})",
             f"- Registry_inclusion events on spine: {n_reg}",
             f"- Corroboration rows: {dict(corro)}",
             ""]
    return "\n".join(lines)


def main() -> None:
    con = forensics.open_state()
    import psycopg2
    pcon = psycopg2.connect(config.DATABASE_URL)
    cur = pcon.cursor()

    # _copy_media never overwrites (it appends _1/_2/... on collision), so a
    # stale OUT_DIR from a prior run accumulates duplicate copies forever --
    # always start from a clean directory so each run's output is the sole,
    # canonical copy.
    shutil.rmtree(OUT_DIR, ignore_errors=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_rows = []

    # 1) classified media -> all attributed to 106 (the only chat) unless a
    #    house-specific caption says otherwise (layer 2 below adds those)
    classified = gather_classified_media()
    for it in classified:
        dest_dir = OUT_DIR / "106" / it["stage"]
        stem = f"{it['date']}_{it['stage']}"
        rel = _copy_media(it["sha256"], _raw_path_for_sha(con, it["sha256"]), dest_dir, stem)
        if rel:
            manifest_rows.append({
                "file": rel, "buildings": "106", "stage": it["stage"],
                "date": it["date"], "kind": it["kind"], "sha256": it["sha256"],
                "caption": (it.get("caption_excerpt") or "").replace("\n", " "),
                "source_url": it["url"],
            })

    # 2) house-number-specific media (any building, any stage)
    by_house = gather_house_specific_media(con)
    for num, items in by_house.items():
        dest_dir = OUT_DIR / num / "house_specific"
        for it in items:
            stem = f"{it['date']}_{num}_mention"
            rel = _copy_media(it["sha256"], it["raw_path"], dest_dir, stem)
            if rel:
                manifest_rows.append({
                    "file": rel, "buildings": num, "stage": "house_specific_mention",
                    "date": it["date"], "kind": it["kind"], "sha256": it["sha256"],
                    "caption": it["caption_excerpt"].replace("\n", " "),
                    "source_url": it["url"],
                })

    # 2b) manually-verified high-value artifacts (bypass classifier entirely)
    key_dir = OUT_DIR / "106" / "key_artifacts"
    for it in gather_manual_includes(con):
        rel = _copy_media(it["sha256"], it["raw_path"], key_dir, it["stem"])
        if rel:
            manifest_rows.append({
                "file": rel, "buildings": "106", "stage": "key_artifact",
                "date": it["date"], "kind": "image", "sha256": it["sha256"],
                "caption": it["caption"], "source_url": it["url"],
            })

    # 2c) verified YouTube videos (siege damage + the 108 partial demolition)
    for it in gather_youtube_includes(con):
        dest_dir = OUT_DIR / it["building"] / it["folder"]
        rel = _copy_media(it["sha256"], it["raw_path"], dest_dir, it["stem"])
        if rel:
            manifest_rows.append({
                "file": rel, "buildings": it.get("manifest_buildings", it["building"]),
                "stage": it["folder"],
                "date": it["date"], "kind": "video", "sha256": it["sha256"],
                "caption": it["caption"], "source_url": it["url"],
            })

    # 2d) external artifacts (Pastvu prewar baseline, resale-channel captures)
    for it in gather_external_includes(con):
        dest_dir = OUT_DIR / it["building"] / it["folder"]
        rel = _copy_media(it["sha256"], it["raw_path"], dest_dir, it["stem"])
        if rel:
            manifest_rows.append({
                "file": rel, "buildings": it["building"], "stage": it["folder"],
                "date": it["date"], "kind": it["kind"], "sha256": it["sha256"],
                "caption": it["caption"], "source_url": "",
            })

    # 2e) single-frame extracts from YouTube videos where only PART of the
    # video is on-topic (the rest documents an adjacent, different building
    # -- the full video is NOT copied in, see YOUTUBE_FRAME_INCLUDES comment)
    for it in gather_youtube_frame_includes(con):
        dest_dir = OUT_DIR / it["building"] / it["folder"]
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{it['stem']}.jpg"
        result = subprocess.run(
            ["ffmpeg", "-y", "-ss", it["timestamp"], "-i", it["raw_path"],
             "-frames:v", "1", str(dest)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            log.error("ffmpeg frame extract failed for %s:\n%s",
                       it["stem"], result.stderr[-1000:])
            continue
        manifest_rows.append({
            "file": str(dest.relative_to(OUT_DIR)), "buildings": it["building"],
            "stage": it["folder"], "date": it["date"], "kind": "image_from_video",
            "sha256": it["video_sha256"], "caption": it["caption"], "source_url": "",
        })

    # 3) key documents
    docs_dir = OUT_DIR / "shared" / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)
    for d in gather_docs():
        raw_path = _raw_path_for_sha(con, d["sha256"])
        if not raw_path:
            continue
        rel = _copy_media(d["sha256"], raw_path, docs_dir,
                           Path(d["filename"]).stem if d.get("filename") else d["category"])
        if rel:
            manifest_rows.append({
                "file": rel, "buildings": "104,106,108,110", "stage": "document",
                "date": d.get("date"), "kind": "document", "sha256": d["sha256"],
                "caption": d.get("filename"), "source_url": "",
            })
            # Every piece of cited evidence needs a VISUAL representation, not
            # just a reference -- a multi-page PDF in a designer package is
            # not browsable at a glance, so render its first page as a JPEG
            # alongside it (poppler's pdftoppm, already a system dependency
            # per memory/ocr_tooling_setup).
            if rel.lower().endswith(".pdf"):
                full_path = OUT_DIR / rel
                thumb_stem = str(docs_dir / (Path(rel).stem + "_p1"))
                result = subprocess.run(
                    ["pdftoppm", "-jpeg", "-f", "1", "-l", "1", "-r", "150",
                     str(full_path), thumb_stem],
                    capture_output=True, text=True,
                )
                if result.returncode != 0:
                    log.error("pdftoppm failed for %s:\n%s", rel, result.stderr[-500:])
                else:
                    produced = sorted(docs_dir.glob(Path(thumb_stem).name + "*.jpg"))
                    if produced:
                        thumb_rel = str(produced[0].relative_to(OUT_DIR))
                        manifest_rows.append({
                            "file": thumb_rel, "buildings": "104,106,108,110",
                            "stage": "document_thumbnail", "date": d.get("date"),
                            "kind": "image_from_pdf", "sha256": d["sha256"],
                            "caption": f"First-page thumbnail of {d.get('filename')} "
                                       f"-- see the PDF itself for full content.",
                            "source_url": "",
                        })

    # 4) per-building briefs
    for num in BUILDING_NUMS:
        (OUT_DIR / num).mkdir(parents=True, exist_ok=True)
        brief = building_brief(num, cur)
        (OUT_DIR / num / "BRIEF.md").write_text(brief, encoding="utf-8")

    # 5) manifest + top-level README
    with (OUT_DIR / "manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["file", "buildings", "stage", "date",
                                            "kind", "sha256", "caption", "source_url"])
        w.writeheader()
        for r in sorted(manifest_rows, key=lambda x: (x["buildings"], x["date"] or "")):
            w.writerow(r)

    readme = f"""# Visual evidence package — пр. Ленина 104, 106, 108, 110

Case study: docs/case_studies/lenina_104_106_108_110_restoration_without_restitution.md

Four contiguous buildings, one joint residents' letter to Putin / Минстрой РФ
/ Минстрой ДНР / прокурор / мэр, one demolition decree (Распоряжение ГКО ДНР
№56, 29.09.2022) naming all four, one federal contractor (ООО «РКС-НР» /
ППК «Единый заказчик»). `106/key_artifacts/` holds manually-verified
high-value items (the №619 door notice, the prosecutor complaint) that
bypass the classifier entirely; `106/construction/` and `106/house_specific/`
hold classifier-derived media that HAS been individually verified (see
correction history below). `104/verified_siege_damage/` and
`106/verified_siege_damage/` hold hand-watched YouTube footage of actual
2022 siege/shelling damage (the package's first confirmed wartime-destruction
imagery); `108/demolition/` holds footage of a PARTIAL demolition (one
entrance/section, not the whole tower — see the case study);
`108/verified_restoration/` holds a single ffmpeg-extracted frame (the rest
of its source video documents an unrelated adjacent building, see below).
`110/prewar_baseline/` holds a 1979 Pastvu photo (the package's first
prewar imagery for any of the four); `106/resale_listings/` and
`110/resale_listings/` hold metadata-only captures (channel/date/link;
listing text/photos are user-supplied, the Telegram widget can't render
these multi-photo album posts) of demand-side resale evidence.
shared/documents/ has the letter PDF and the scanned court ruling;
shared/verified_siege_damage/ holds a Feb-2023 video covering the whole
104-110 stretch.

**Correction history (2026-06-19, FIVE rounds of manual review)** — this
package started at 32 auto-classified files and is down to {len(manifest_rows)}
after every single item was opened and checked by hand. Full detail in
`memory/lifecycle_classifier_unreliable_siege_damage.md` and the case
study's provenance notes; summary:
1. The entire `siege_damage` stage (4 files) was wrong — repair-work footage
   or unrelated video, none of it wartime destruction. 32→26.
2. `construction` was also mixed — a satirical video + 3 off-topic
   app-settings screenshots had landed in that stage. 26→21.
3. More wrong items, including in stages already "cleared": a second
   satirical video despite an on-topic-looking caption, a missing-person
   post misfiled as a building photo, off-topic resident chatter, and
   repair footage whose building couldn't be confirmed as 106 specifically.
   21→12.
4. Two more off-topic `resident_presence` items (another missing-person
   post, a residents'-association contact sheet). 12→10.
5. **A caption-*association* bug, not just a caption-accuracy bug**: msg 269
   had been excluded as off-topic chatter based on a caption that turned
   out to belong to a different, adjacent message — the manifest mis-linked
   it. Its real caption ("На каждой двери") and the photo itself, re-verified
   directly, are exactly the Распоряжение №619 door notice. Restored via
   `MANUAL_INCLUDES`, alongside a handwritten prosecutor complaint (msg 986)
   that the classifier had left "unclassified" with no caption at all.
   **Lesson: never trust a stage label OR a caption OR even the caption's
   association with a given file — open the actual raw bytes.**
6. **New source added (2026-06-19): 7 YouTube videos.** Each watched
   frame-by-frame before inclusion — one (title-mentions-104/106) was
   EXCLUDED despite matching house numbers because its title says
   "просп. Победы" (Victory Avenue), a different street from Ленина/Мира
   entirely — real siege damage, wrong building. Of the rest: 2 confirm
   genuine 2022 siege/shelling damage at 104, 2 at 106 (the package's first
   confirmed wartime-destruction imagery for either), and 1 shows an
   excavator demolishing ONE entrance/section of 108 while the rest of the
   tower stands — see the case study for what this means for 108's framing.
7. **2 more YouTube videos added (2026-06-19)**: a Feb-2023 video
   ("Lenina(Mira) 104-110. And they want to restore it") is genuine,
   address-consistent siege-destruction footage of the whole stretch —
   `shared/verified_siege_damage/`. A second video ("пр-т Ленина,108", Aug
   2023) needed transcript review to resolve: the vlogger names a crane at
   "дом 110" but the crane is visibly turned toward Зелинского 33, a
   DIFFERENT building, confirmed by his own next line ("зашел во двор
   Зелинского 33"); that segment is excluded and the full video is kept in
   data/raw/ only as a lead for a possible future Зелинского 33 case study.
   The same video's distant courtyard view of 108 itself ("дом
   восстанавливают, ближе не смогу подойти") IS on-topic — only that single
   frame is extracted (via ffmpeg, not the whole video) into
   `108/verified_restoration/`.
8. **Non-chat external sources added (2026-06-19)**: a 1979 Pastvu photo
   and two real-estate resale-channel posts. The Pastvu geotag placed it
   ~25m from property 4423 — the user confirmed it as 110 directly. One
   resale post (676643) had been guessed as 108 in an earlier memory note
   purely by inference, before its content was ever seen; the user's
   screenshot now confirms it's actually 110, not 108 — corrected here.
   Also noted: the t.me ?embed=1 widget's HTML is not byte-stable across
   fetches (each request gets a fresh sha), so a re-fetch to fix a
   description creates a new row rather than updating the old one — always
   use the latest captured sha for a given logical post.

- {len(manifest_rows)} files exported
- manifest.csv — file, buildings, stage, date, kind, sha256, caption, source_url
- Every file's SHA-256 in the manifest matches the forensic store — cite the
  hash, not just the filename, in any published exhibit.
- Occupation records are evidence of the seizure act, not valid title.
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")

    pcon.close()
    print(f"\n{'='*64}")
    print(f"VISUAL EVIDENCE PACKAGE — {len(manifest_rows)} files")
    print(f"  → {OUT_DIR}")
    print(f"{'='*64}\n")


def _raw_path_for_sha(con, sha: str) -> str | None:
    row = con.execute("SELECT raw_path FROM source_document WHERE sha256=?", (sha,)).fetchone()
    return row[0] if row else None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
