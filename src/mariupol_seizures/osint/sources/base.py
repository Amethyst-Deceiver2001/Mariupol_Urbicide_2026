"""Shared result type + small helpers for OSINT source modules."""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class SourceResult:
    source: str
    ok: bool
    summary: str
    findings: list[dict] = field(default_factory=list)
    captured_sha256: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        return {
            "source": self.source,
            "ok": self.ok,
            "summary": self.summary,
            "n_findings": len(self.findings),
            "findings": self.findings,
            "captured_sha256": self.captured_sha256,
        }


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


UA = "mariupol-property-seizures research (see CLAUDE.md); contact via project"


def http_headers() -> dict:
    return {"User-Agent": UA}


# Domains confirmed geoblocked from outside Russia in this project's own
# source catalogue (docs/sources.md) — heuristic, not exhaustive. A URL not
# matching this list is treated as reachable; false negatives (a geoblocked
# domain we haven't seen yet) just mean the dossier doesn't flag it, which
# is the safe direction of error (CLAUDE.md: always hyperlink the source
# regardless — this classification only controls the "geoblocked" badge).
GEOBLOCKED_DOMAIN_SUBSTRINGS = (
    "sudrf.ru", "gosuslugi.ru", "denis-pushilin.ru", "dnronline.su",
    "npa.dnronline.su", "rosreestr.gov.ru", "nalog.ru", "egrul",
    "mos.ru", "government-nnov.ru", "minstroy-dpr", "garant.ru",
    "pravo.gov.ru", "kremlin.ru", "donland.ru", "dnr-online.ru",
    "2kas.sudrf.ru",
)


def is_geoblocked(url: str) -> bool:
    u = (url or "").lower()
    return any(d in u for d in GEOBLOCKED_DOMAIN_SUBSTRINGS)


import re  # noqa: E402

URL_RE = re.compile(r"https?://[^\s\"'<>\)\]]+")


def find_urls(value) -> list[str]:
    """Recursively pull every http(s) URL out of a JSON-ish value (dict/
    list/str), for scanning seizure_event.detail / corroboration.detail
    JSONB blobs whose URL-bearing keys aren't consistently named."""
    out: list[str] = []
    if isinstance(value, str):
        out.extend(URL_RE.findall(value))
    elif isinstance(value, dict):
        for v in value.values():
            out.extend(find_urls(v))
    elif isinstance(value, list):
        for v in value:
            out.extend(find_urls(v))
    return out
