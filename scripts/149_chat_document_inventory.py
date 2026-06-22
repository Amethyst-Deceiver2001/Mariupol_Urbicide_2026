#!/usr/bin/env python3
"""Inventory + text-extract every DOCUMENT file posted in the building chats.

Telegram messages carry not just photos but uploaded files — and across the
28 chats those files include the occupation administration's own primary
sources: dated ownerless-registry snapshots, an explicit "Исключены из
бесхоза" removal list, ГКО постановления, court rulings, planning projects
(ППТ), and resident appeals. This script catalogs and extracts them so they
become searchable / loadable primary evidence.

For each document-type media (pdf / xlsx / docx / octet-stream / txt):
  - recover the real filename + date + chat + the parent message's caption
  - sniff true type (octet-stream files are often mislabeled pdf/xlsx/jpeg)
  - extract text:
        pdf  -> pdftotext -layout
        xlsx -> openpyxl (all sheets, tab-separated)
        docx -> read word/document.xml from the zip (no python-docx dep)
        txt  -> verbatim
    written to data/parsed/chat_docs/<sha>.txt
  - classify by filename + extracted content into a document category, with
    special detection of dated ownerless snapshots (the inputs script 150
    needs for the temporal differential)

Outputs:
  data/parsed/chat_docs/<sha>.txt          — extracted text per document
  data/parsed/chat_document_inventory.jsonl — one row per document
  console summary highlighting ownerless snapshots + decree/ruling numbers

Pure local analysis over the forensic store (no network). Safe to run.

Run:
    PYTHONPATH=src python scripts/149_chat_document_inventory.py
"""
import json
import logging
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import forensics  # noqa: E402

log = logging.getLogger(__name__)

OUT_DIR = ROOT / "data" / "parsed" / "chat_docs"
OUT_INV = ROOT / "data" / "parsed" / "chat_document_inventory.jsonl"

DOC_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/vnd.ms-excel",
    "application/octet-stream",
    "text/plain",
}

# filename / content classifiers (first match wins, order matters)
CLASSIFIERS = [
    ("ownerless_exclusion", r"исключ\w*\s+из\s+бесхоз|искл.{0,6}бесхоз|exclud"),
    ("ownerless_snapshot",  r"бесхоз|besx|бесхозяйн|признаки бесхозяйности"),
    ("owners_list",         r"собственник|sobstvennik|правообладател"),
    ("gko_decree",          r"GKO|ГКО|Post_GKO"),
    ("admin_postanovlenie", r"постановлени|postanovleni|распоряжени"),
    ("court_ruling",        r"решени|reshenie|протокол|determination|опредил"),
    ("planning_ppt",        r"ППТ|планировк|планировочн|релиз_ппт"),
    ("inventory",           r"инвентаризац|инвентар|инвентаризация|мкд_инвент"),
    ("resident_appeal",     r"письмо|заявлени|жалоб|обращени|главе|чиновник|инстанц"),
    ("evacuation_list",     r"эвакуир|эвакуац|переселенц|пересел|гум.{0,5}помощ|живых"),
    ("damage_assessment",   r"unosat|damage|разрушен|перечень объектов|не функционирующ|не_функционирующ"),
    ("utility",             r"лифт|трудов\w* книжк|roskap|receipt|больниц"),
]
CLASSIFIER_RX = [(name, re.compile(rx, re.I)) for name, rx in CLASSIFIERS]

# dated-snapshot date sniffers: filename patterns like 26072023, 27.03.2024,
# 02_09_2024, 08.12.2025, _na_13.01.2025, на 26.08.2024
DATE_IN_NAME = [
    re.compile(r"(\d{2})[._-](\d{2})[._-](\d{4})"),     # 27.03.2024 / 02_09_2024
    re.compile(r"на[_ ]?(\d{2})(\d{2})(\d{4})"),        # на26072023
    re.compile(r"(\d{4})(\d{2})(\d{2})"),               # 20220405
]


def _sniff(blob: bytes) -> str:
    if blob[:5] == b"%PDF-":
        return "pdf"
    if blob[:2] == b"PK":
        return "zip"          # xlsx/docx
    if blob[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if blob[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if blob[:4] in (b"\xd0\xcf\x11\xe0",):
        return "ole"          # legacy doc/xls
    return "unknown"


def _extract_pdf(path: Path) -> str:
    try:
        r = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                           capture_output=True, text=True, timeout=120)
        return r.stdout or ""
    except Exception as e:
        return f"[pdf extract error: {e}]"


def _extract_xlsx(path: Path) -> str:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        out = []
        for ws in wb.worksheets:
            out.append(f"### SHEET: {ws.title}")
            for row in ws.iter_rows(values_only=True):
                cells = ["" if c is None else str(c) for c in row]
                if any(cells):
                    out.append("\t".join(cells))
        return "\n".join(out)
    except Exception as e:
        return f"[xlsx extract error: {e}]"


def _extract_docx(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
        # paragraphs: </w:p> -> newline; strip tags
        xml = re.sub(r"</w:p>", "\n", xml)
        xml = re.sub(r"<[^>]+>", "", xml)
        return re.sub(r"\n{3,}", "\n\n", xml)
    except Exception as e:
        return f"[docx extract error: {e}]"


def _classify(fname: str, text: str) -> str:
    hay = f"{fname}\n{text[:4000]}"
    for name, rx in CLASSIFIER_RX:
        if rx.search(hay):
            return name
    return "other"


def _snapshot_date(fname: str, text: str) -> str | None:
    for rx in DATE_IN_NAME:
        m = rx.search(fname)
        if m:
            g = m.groups()
            if len(g[0]) == 4:        # yyyymmdd
                return f"{g[0]}-{g[1]}-{g[2]}"
            return f"{g[2]}-{g[1]}-{g[0]}"
    # fall back: a date inside the first lines of the document text
    m = re.search(r"на\s+(\d{2})[._/](\d{2})[._/](\d{4})", text[:2000])
    if m:
        g = m.groups()
        return f"{g[2]}-{g[1]}-{g[0]}"
    return None


def main() -> None:
    con = forensics.open_state()
    placeholders = ",".join("?" * len(DOC_CONTENT_TYPES))
    rows = con.execute(
        f"SELECT url, content_type, raw_path, sha256 FROM source_document "
        f"WHERE source_type='telegram_building_chat_media' "
        f"AND content_type IN ({placeholders}) ORDER BY url",
        tuple(DOC_CONTENT_TYPES),
    ).fetchall()
    log.info("found %d document-type media", len(rows))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    inv = []

    for url, ct, raw_path, sha in rows:
        p = ROOT / raw_path if raw_path else None
        if not p or not p.exists():
            continue
        blob = p.read_bytes()
        true_kind = _sniff(blob)

        # recover filename + date + caption from the parent message
        parent_url = url.replace("/media", "")
        pr = con.execute("SELECT raw_path FROM source_document WHERE url=?",
                         (parent_url,)).fetchone()
        fname = ""
        date = ""
        caption = ""
        if pr:
            try:
                obj = json.loads((ROOT / pr[0]).read_bytes())
                date = (obj.get("date") or "")[:10]
                caption = (obj.get("message") or "").strip()[:300]
                media = obj.get("media") or {}
                doc = media.get("document") or {}
                for a in (doc.get("attributes") or []):
                    if a.get("file_name"):
                        fname = a["file_name"]
            except Exception:
                pass

        # extract text by true type
        if true_kind == "pdf" or ct == "application/pdf":
            text = _extract_pdf(p)
        elif true_kind == "zip":
            # distinguish xlsx vs docx by zip contents
            try:
                with zipfile.ZipFile(p) as z:
                    names = z.namelist()
                if any(n.startswith("xl/") for n in names):
                    text = _extract_xlsx(p)
                elif any(n.startswith("word/") for n in names):
                    text = _extract_docx(p)
                else:
                    text = "[zip but neither xlsx nor docx]"
            except Exception as e:
                text = f"[zip error: {e}]"
        elif ct == "text/plain" or true_kind == "unknown" and len(blob) < 200000:
            text = blob.decode("utf-8", "ignore")
        elif true_kind in ("jpeg", "png"):
            text = "[image — OCR not run here; see script 151 media manifest]"
        else:
            text = f"[unextracted: ct={ct} sniff={true_kind}]"

        category = _classify(fname, text)
        snap_date = _snapshot_date(fname, text) if category.startswith("ownerless") else None

        # rough row count for ownerless snapshots
        n_owner_rows = None
        if category.startswith("ownerless"):
            n_owner_rows = len(re.findall(r"бесхозяйн", text))

        txt_path = OUT_DIR / f"{sha[:16]}.txt"
        if not text.startswith("["):
            txt_path.write_text(text, encoding="utf-8")
            txt_rel = str(txt_path.relative_to(ROOT))
        else:
            txt_rel = None

        inv.append({
            "chat": parent_url.split("/")[3],
            "url": url, "date": date, "filename": fname,
            "content_type": ct, "true_kind": true_kind,
            "category": category, "snapshot_date": snap_date,
            "ownerless_marker_rows": n_owner_rows,
            "caption": caption, "sha256": sha,
            "text_path": txt_rel, "text_len": len(text),
        })

    with OUT_INV.open("w", encoding="utf-8") as fh:
        for r in inv:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # ── console summary ─────────────────────────────────────────────────────
    from collections import Counter
    cats = Counter(r["category"] for r in inv)
    print(f"\n{'='*74}")
    print(f"CHAT DOCUMENT INVENTORY — {len(inv)} documents extracted")
    print(f"{'='*74}")
    print("\n── by category ──")
    for cat, n in cats.most_common():
        print(f"  {cat:22s}  {n}")

    print("\n── OWNERLESS SNAPSHOTS / EXCLUSION LISTS (inputs for script 150) ──")
    snaps = [r for r in inv if r["category"].startswith("ownerless")]
    for r in sorted(snaps, key=lambda x: (x["snapshot_date"] or x["date"] or "")):
        print(f"  {r['snapshot_date'] or r['date'] or '????':10s}  "
              f"{r['category']:20s}  rows~{r['ownerless_marker_rows'] or 0:<5}  "
              f"{r['filename'] or '(no name)':40s}  [{r['chat']}]")

    print("\n── DECREES / RULINGS / PLANNING (primary-source candidates) ──")
    for cat in ("gko_decree", "admin_postanovlenie", "court_ruling", "planning_ppt"):
        items = [r for r in inv if r["category"] == cat]
        if not items:
            continue
        print(f"  {cat}:")
        for r in sorted(items, key=lambda x: x["date"]):
            print(f"     {r['date']:10s}  {r['filename'] or '(no name)':45s}  [{r['chat']}]")

    print(f"\n  Inventory → {OUT_INV}")
    print(f"  Extracted text → {OUT_DIR}/")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
