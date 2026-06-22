"""Tests for the forensic capture + custody guarantees."""
import sqlite3

from mariupol_seizures import forensics


def _mem_state():
    """In-memory state DB with both fetch_log and source_document tables."""
    con = sqlite3.connect(":memory:")
    con.executescript(
        """
        CREATE TABLE fetch_log (
            url TEXT, court TEXT, kind TEXT, sha256 TEXT,
            raw_path TEXT, http_status INT, captured_at TEXT,
            PRIMARY KEY (url, captured_at)
        );
        CREATE TABLE source_document (
            sha256 TEXT PRIMARY KEY, url TEXT NOT NULL,
            source_type TEXT, title TEXT, description TEXT,
            raw_path TEXT, content_type TEXT, http_status INT, captured_at TEXT
        );
        """
    )
    return con


def test_sha256_is_stable():
    assert forensics.sha256_bytes(b"abc") == forensics.sha256_bytes(b"abc")
    assert forensics.sha256_bytes(b"abc") != forensics.sha256_bytes(b"abd")


def test_capture_writes_raw_and_sidecar(tmp_path, monkeypatch):
    monkeypatch.setattr(forensics.config, "RAW_DIR", tmp_path)
    con = _mem_state()
    sha = forensics.capture(b"<html>x</html>", url="https://c/x", court="c",
                            kind="case_card", http_status=200, con=con)
    raw = tmp_path / f"{sha}.html"
    assert raw.exists()
    assert (tmp_path / f"{sha}.html.meta.json").exists()
    assert raw.read_bytes() == b"<html>x</html>"


def test_verify_store_detects_tampering(tmp_path, monkeypatch):
    monkeypatch.setattr(forensics.config, "RAW_DIR", tmp_path)
    con = _mem_state()
    sha = forensics.capture(b"original", url="https://c/y", court="c",
                            kind="results", http_status=200, con=con)
    assert forensics.verify_store(con) == []          # intact
    (tmp_path / f"{sha}.html").write_bytes(b"tampered")
    assert forensics.verify_store(con) == ["https://c/y"]


def test_capture_source_writes_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(forensics.config, "RAW_DIR", tmp_path)
    con = _mem_state()
    content = b"%PDF-1.4 fake decree"
    sha = forensics.capture_source(
        content,
        url="https://example.gov/decree.pdf",
        source_type="decree",
        title="Test Decree",
        description="A test PDF",
        content_type="application/pdf",
        http_status=200,
        con=con,
    )
    assert (tmp_path / f"{sha}.pdf").exists()
    assert (tmp_path / f"{sha}.pdf.meta.json").exists()
    assert (tmp_path / f"{sha}.pdf").read_bytes() == content


def test_capture_source_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(forensics.config, "RAW_DIR", tmp_path)
    con = _mem_state()
    content = b"<html>source</html>"
    sha1 = forensics.capture_source(
        content, url="https://x.test/a", source_type="news_article",
        title="T", description="D", content_type="text/html",
        http_status=200, con=con,
    )
    sha2 = forensics.capture_source(
        content, url="https://x.test/a", source_type="news_article",
        title="T", description="D", content_type="text/html",
        http_status=200, con=con,
    )
    assert sha1 == sha2
    assert len(list(tmp_path.glob(f"{sha1}*"))) == 2   # .html + .html.meta.json


def test_list_sources_returns_catalogue(tmp_path, monkeypatch):
    monkeypatch.setattr(forensics.config, "RAW_DIR", tmp_path)
    con = _mem_state()
    forensics.capture_source(
        b"decree bytes", url="https://a.gov/d.pdf", source_type="decree",
        title="Decree A", description="desc", content_type="application/pdf",
        http_status=200, con=con,
    )
    forensics.capture_source(
        b"<html>news</html>", url="https://b.news/article", source_type="news_article",
        title="Article B", description="desc2", content_type="text/html",
        http_status=200, con=con,
    )
    rows = forensics.list_sources(con)
    assert len(rows) == 2
    types = {r["source_type"] for r in rows}
    assert types == {"decree", "news_article"}
