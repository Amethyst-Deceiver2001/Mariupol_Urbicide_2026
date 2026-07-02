"""Forensic capture + chain of custody. Capture before parse; hash everything."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import config

# MIME type → file extension for captured source documents.
_MIME_EXT: dict[str, str] = {
    "application/pdf": ".pdf",
    "text/html": ".html",
    "application/xhtml+xml": ".html",
    "text/plain": ".txt",
    "text/csv": ".csv",
    "application/json": ".json",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "application/zip": ".zip",
    "application/x-zip-compressed": ".zip",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


def now_iso() -> str:
    """ISO-8601 UTC timestamp for capture records."""
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def open_state(db_path: Path | None = None) -> sqlite3.Connection:
    """State DB: dedupe, resumability, and a fetch log mirroring source_document."""
    con = sqlite3.connect(db_path or config.STATE_DB)
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS fetch_log (
            url TEXT, court TEXT, kind TEXT, sha256 TEXT, raw_path TEXT,
            http_status INT, captured_at TEXT,
            PRIMARY KEY (url, captured_at)
        );
        CREATE TABLE IF NOT EXISTS cases (
            case_uid TEXT PRIMARY KEY, court TEXT, case_number TEXT,
            category TEXT, card_url TEXT, relevant INT, discovered_at TEXT
        );
        CREATE TABLE IF NOT EXISTS done (key TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS source_document (
            sha256      TEXT PRIMARY KEY,
            url         TEXT NOT NULL,
            source_type TEXT,
            title       TEXT,
            description TEXT,
            raw_path    TEXT,
            content_type TEXT,
            http_status  INT,
            captured_at  TEXT,
            derived_from TEXT,          -- SHA-256 of the source artifact, if derived
            transform    TEXT           -- tool + args that produced a derived artifact
        );
        """
    )
    # Idempotent migration for DBs created before the derived-artifact columns.
    cols = {r[1] for r in con.execute("PRAGMA table_info(source_document)")}
    if "derived_from" not in cols:
        con.execute("ALTER TABLE source_document ADD COLUMN derived_from TEXT")
    if "transform" not in cols:
        con.execute("ALTER TABLE source_document ADD COLUMN transform TEXT")
    con.commit()
    return con


def capture(content: bytes, *, url: str, court: str, kind: str,
            http_status: int, con: sqlite3.Connection) -> str:
    """Persist a raw body immutably + write a chain-of-custody sidecar. Returns sha."""
    sha = sha256_bytes(content)
    captured = now_iso()
    raw_path = config.RAW_DIR / f"{sha}.html"
    if not raw_path.exists():                       # append-only / immutable
        raw_path.write_bytes(content)
    meta = {
        "url": url, "court": court, "kind": kind, "sha256": sha,
        "http_status": http_status, "captured_at": captured,
    }
    Path(str(raw_path) + ".meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    con.execute(
        "INSERT OR REPLACE INTO fetch_log VALUES (?,?,?,?,?,?,?)",
        (url, court, kind, sha, str(raw_path), http_status, captured),
    )
    con.commit()
    return sha


def mark_done(con: sqlite3.Connection, key: str) -> None:
    con.execute("INSERT OR IGNORE INTO done(key) VALUES (?)", (key,))
    con.commit()


def is_done(con: sqlite3.Connection, key: str) -> bool:
    return con.execute("SELECT 1 FROM done WHERE key=?", (key,)).fetchone() is not None


def verify_store(con: sqlite3.Connection) -> list[str]:
    """Re-hash every raw artifact against the log. Returns list of mismatches."""
    bad = []
    for url, sha, raw_path in con.execute(
        "SELECT url, sha256, raw_path FROM fetch_log"
    ):
        p = Path(raw_path)
        if not p.exists() or sha256_bytes(p.read_bytes()) != sha:
            bad.append(url)
    return bad


def capture_source(
    content: bytes,
    *,
    url: str,
    source_type: str,
    title: str,
    description: str,
    content_type: str,
    http_status: int,
    con: sqlite3.Connection,
) -> str:
    """Persist a reference source document immutably and log it to source_document.

    Unlike capture() (which is for court HTML), this handles arbitrary MIME types
    and uses source_type/title/description instead of court/kind.  The raw file
    extension is derived from content_type so PDFs are stored as .pdf, etc.

    Idempotent: if the SHA already exists in the store the bytes are not
    re-written (append-only rule), but the metadata row is updated.

    Returns the sha256 hex digest.
    """
    sha = sha256_bytes(content)
    captured = now_iso()
    mime_base = content_type.split(";", 1)[0].strip().lower()
    ext = _MIME_EXT.get(mime_base, ".bin")
    raw_path = config.RAW_DIR / f"{sha}{ext}"
    if not raw_path.exists():
        raw_path.write_bytes(content)
    meta = {
        "url": url,
        "source_type": source_type,
        "title": title,
        "description": description,
        "sha256": sha,
        "content_type": content_type,
        "http_status": http_status,
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
        (sha, url, source_type, title, description,
         str(raw_path), content_type, http_status, captured),
    )
    con.commit()
    return sha


def capture_derived(
    content: bytes,
    *,
    derived_from: str,
    transform: str,
    source_type: str,
    title: str,
    description: str,
    content_type: str,
    con: sqlite3.Connection,
) -> str:
    """Persist a DERIVED artifact (e.g. OCR output) with explicit lineage.

    Berkeley Protocol: a transformation must log inputs, outputs, hashes, and
    timestamps, and must never mutate the immutable raw source. This writes the
    derived bytes under their own SHA-256, records `derived_from` (the parent
    SHA) and `transform` (tool + args), and writes a sidecar that names the
    parent so the chain is reproducible from raw → derived → parsed.

    Returns the derived artifact's sha256.
    """
    sha = sha256_bytes(content)
    captured = now_iso()
    mime_base = content_type.split(";", 1)[0].strip().lower()
    ext = _MIME_EXT.get(mime_base, ".bin")
    raw_path = config.RAW_DIR / f"{sha}{ext}"
    if not raw_path.exists():
        raw_path.write_bytes(content)
    meta = {
        "url": f"derived:{transform}:{derived_from}",
        "source_type": source_type,
        "title": title,
        "description": description,
        "sha256": sha,
        "derived_from": derived_from,
        "transform": transform,
        "content_type": content_type,
        "captured_at": captured,
    }
    Path(str(raw_path) + ".meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    con.execute(
        """INSERT OR REPLACE INTO source_document
           (sha256, url, source_type, title, description,
            raw_path, content_type, http_status, captured_at,
            derived_from, transform)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (sha, f"derived:{transform}:{derived_from}", source_type, title,
         description, str(raw_path), content_type, None, captured,
         derived_from, transform),
    )
    con.commit()
    return sha


def list_sources(con: sqlite3.Connection) -> list[dict]:
    """Return all captured source documents as a list of dicts, newest first."""
    rows = con.execute(
        """SELECT sha256, url, source_type, title, description,
                  raw_path, content_type, http_status, captured_at
           FROM source_document
           ORDER BY captured_at DESC"""
    ).fetchall()
    keys = ["sha256", "url", "source_type", "title", "description",
            "raw_path", "content_type", "http_status", "captured_at"]
    return [dict(zip(keys, r)) for r in rows]
