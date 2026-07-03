#!/usr/bin/env python3
"""Lint exhibits/index.html for headline-stat drift against docs/STATS.md.

Today's coherence review found five *different* "properties on the evidence
spine" figures live across the exhibits at once (11,730 / 11,741 / 11,804),
plus stale legal-grade counts, raw-artifact counts, and a raw-store size --
the exact defect class docs/STATS.md was created to prevent (see its own
header comment). This script makes that class of bug mechanically
detectable instead of relying on another manual read-through.

Two independent checks, run against every docs/exhibits/*.html file and
docs/index.html:

1. Label-anchored drift: every headline-stat markup pattern this project's
   exhibits use (``<span class="n ...">NUMBER</span><span class="l">LABEL
   </span>``, both the EN and RU wording of each label) is extracted; if the
   label identifies a tracked project-total metric (spine count, legal-grade
   count, raw-artifact count, raw-store size, corroboration rows, registry
   entries, court-case counts, grant rates) and the extracted number isn't
   one of the values currently acceptable for that metric -- parsed live
   from docs/STATS.md, never hardcoded here -- it's flagged.
2. Known-stale literal: a short list of numbers already confirmed wrong in
   a past review (2026-07-03) is grepped verbatim across the same files, as
   a safety net for stat mentions that don't use the standard markup (plain
   prose, an evcard heading, etc.) and so would be invisible to check 1.

Pure local file read, no network, no DB. Safe to re-run any time; exits 1 if
any drift is found (0 otherwise), so it can be wired into a pre-commit hook
or CI step later if wanted.

Run:
    python3 scripts/238_lint_stats_drift.py
"""
from __future__ import annotations

import html
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATS_MD = ROOT / "docs" / "STATS.md"
EXHIBITS_DIR = ROOT / "docs" / "exhibits"
INDEX_HTML = ROOT / "docs" / "index.html"

# Numbers already confirmed wrong in the 2026-07-03 coherence review. Append
# to this list whenever a future review finds and fixes another stale
# figure -- it's a cheap permanent regression guard for exactly that number
# reappearing (e.g. from a copy-pasted section, an unmerged branch, a stale
# clone of an exhibit for a new case study).
STALE_LITERALS = [
    "11,730", "11 730", "11730",
    "11,741", "11 741", "11741",
    "1,155", "1 155",
    "1,156", "1 156",
    "353,587", "353 587", "353587",
    "353,600", "353 600", "≈353 600", "≈353,600",
    "211,732", "211732",
    "70 GB", "70 гигабайт",
    "11,521", "11 521",
    "82.2%", "82,2%",
]

# Strip these before scanning so SVG path coordinates, rgba() color lists,
# and embedded base64 image data can't produce false-positive number matches.
_STRIP_BLOCK_RE = re.compile(
    r"<script\b.*?</script>|<style\b.*?</style>|<svg\b.*?</svg>|"
    r"data:image/[a-zA-Z0-9+.;=,/]+",
    re.S | re.I,
)

# The headline-stat markup pattern every exhibit uses: a number span
# (optionally carrying the JS count-up source-of-truth in data-count/data-to)
# immediately followed by a label span. Covers .stat/.bstat/.csstat -- all
# three use the same "n" + "l" inner class names.
_STAT_PAIR_RE = re.compile(
    r'<span class="n[^"]*"(?:\s+data-(?:count|to)="(?P<attr>\d+)")?\s*>'
    r"(?P<text>[^<]*)</span>\s*<span class=\"l\">(?P<label>.*?)</span>",
    re.S,
)

_TAG_RE = re.compile(r"<[^>]+>")
_NUM_RE = re.compile(
    r"^[~≈]?\s*(?P<num>[\d][\d,.\s  ]*?)\s*"
    r"(?P<mult>k|тыс\.?|млн|m|million)?"
    r"(?P<pct>%)?$",
    re.I,
)
_MULT = {"k": 1_000, "тыс": 1_000, "тыс.": 1_000,
         "m": 1_000_000, "million": 1_000_000, "млн": 1_000_000}


def strip_label(label_html: str) -> str:
    text = html.unescape(label_html)
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = _TAG_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def try_parse_number(raw: str) -> float | None:
    """Parse a stat-span's inner text/attr to a plain number, or None if the
    cell is composite ("3 / 3", "45k vs 53k", "5-12 days") -- those aren't
    single project-total figures and are deliberately left unparsed rather
    than guessed at."""
    s = html.unescape(raw).strip()
    s = s.replace("–", "-").replace("—", "-")
    if "-" in s or "/" in s or " vs " in s.lower() or " vs." in s.lower():
        return None
    # Russian decimal-comma percentages ("83,8%") vs. thousands-group commas
    # ("11,804") are ambiguous by punctuation alone -- disambiguate by shape:
    # a single comma, 1-2 digits after it, ending in "%" is a RU decimal.
    if re.match(r"^[\d]{1,3},\d{1,2}%$", s):
        s = s.replace(",", ".")
    m = _NUM_RE.match(s)
    if not m:
        return None
    num_str = re.sub(r"[,\s  ]", "", m.group("num"))
    if not num_str or not num_str.replace(".", "", 1).isdigit():
        return None
    value = float(num_str)
    mult = (m.group("mult") or "").lower().rstrip(".")
    if mult in _MULT:
        value *= _MULT[mult]
    return value


@dataclass
class TrackedStat:
    name: str
    keyword_re: re.Pattern
    acceptable: set[float] = field(default_factory=set)

    def matches_label(self, label: str) -> bool:
        return bool(self.keyword_re.search(label))

    def is_acceptable(self, value: float) -> bool:
        return any(abs(value - a) < 0.05 for a in self.acceptable)


def parse_stats_md(text: str) -> dict[str, float]:
    """Pull every `| Label | **Value** |` markdown-table row into a dict,
    plus the two prose grant-rate lines under 'Occupation court layer'.
    Values keep their raw parsed magnitude (GB size parsed as a bare
    number of gigabytes, percentages as bare floats)."""
    stats: dict[str, float] = {}
    for m in re.finditer(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$", text, re.M):
        label, value = m.group(1).strip(), m.group(2).strip()
        if label.lower() in ("metric", "stage", "---", ""):
            continue
        value = value.strip("*").strip()
        vm = re.match(r"^([\d][\d,\s]*)(G|GB)?$", value)
        if not vm:
            continue
        num = float(vm.group(1).replace(",", "").replace(" ", ""))
        stats[label] = num

    # "Total: 2,694 · decided: 2,684 · granted: 2,248 · **grant rate: 83.8%**"
    # "Mariupol" labels the *paragraph above* the bullet, not the bullet
    # itself -- classify each match by whichever of "Mariupol" / "Rest of
    # DNR" appears most recently before it in the text, not by scanning one
    # line in isolation.
    for gm in re.finditer(
        r"[Tt]otal:?\s*([\d,]+)\s*.{0,10}?decided:?\s*([\d,]+)\s*.{0,10}?"
        r"granted:?\s*([\d,]+)\s*.{0,40}?grant rate:?\s*\*?\*?([\d.]+)%",
        text,
    ):
        total = float(gm.group(1).replace(",", ""))
        decided = float(gm.group(2).replace(",", ""))
        granted = float(gm.group(3).replace(",", ""))
        rate = float(gm.group(4))
        preceding = text[:gm.start()].lower()
        last_mariupol = preceding.rfind("mariupol")
        last_rest = preceding.rfind("rest of dnr")
        if last_mariupol == -1 and last_rest == -1:
            continue
        if last_mariupol > last_rest:
            stats["Mariupol court cases (total)"] = total
            stats["Mariupol court cases (decided)"] = decided
            stats["Mariupol court cases (granted)"] = granted
            stats["Mariupol grant rate %"] = rate
        else:
            stats["Rest-of-DNR court cases (total)"] = total
            stats["Rest-of-DNR court cases (decided)"] = decided
            stats["Rest-of-DNR court cases (granted)"] = granted
            stats["Rest-of-DNR grant rate %"] = rate

    # Combined region-wide grant rate, weighted across both populations --
    # a real, correct figure ("87.1%" in the exhibits) that isn't its own
    # row in STATS.md, only derivable from the two bullets above.
    m_dec, r_dec = stats.get("Mariupol court cases (decided)"), stats.get("Rest-of-DNR court cases (decided)")
    m_gr, r_gr = stats.get("Mariupol court cases (granted)"), stats.get("Rest-of-DNR court cases (granted)")
    if None not in (m_dec, r_dec, m_gr, r_gr) and (m_dec + r_dec):
        stats["Combined grant rate %"] = round(100 * (m_gr + r_gr) / (m_dec + r_dec), 1)
    return stats


def build_tracked_stats(stats: dict[str, float]) -> list[TrackedStat]:
    def s(*labels: str) -> set[float]:
        out = set()
        for lbl in labels:
            if lbl in stats:
                out.add(stats[lbl])
        return out

    court_cases = s(
        "Mariupol court cases (total)", "Rest-of-DNR court cases (total)",
        "Court-island properties (single-source, court only)",
    )
    mariupol_total = stats.get("Mariupol court cases (total)")
    rest_total = stats.get("Rest-of-DNR court cases (total)")
    if mariupol_total is not None and rest_total is not None:
        court_cases.add(mariupol_total + rest_total)  # the combined 8,271-style figure

    return [
        TrackedStat(
            "Properties on spine",
            re.compile(
                r"properties on (the )?(evidence )?spine|объект[а-я]* в базе",
                re.I,
            ),
            s("Properties on spine"),
        ),
        TrackedStat(
            "Legal-grade properties",
            re.compile(
                r"legal.grade|независимыми источниками",
                re.I,
            ),
            s("Legal-grade (≥2 independent source families)"),
        ),
        TrackedStat(
            "Raw artifacts (chain of custody)",
            re.compile(
                r"artifacts?( held| registered| hashed)?( in the raw store| under chain of custody)?|"
                r"артефакт",
                re.I,
            ),
            s("Raw artifact files (excl. `.meta.json` sidecars)"),
        ),
        TrackedStat(
            "Raw store disk size (GB)",
            re.compile(r"\bGB\b|гигабайт", re.I),
            s("Disk size"),
        ),
        TrackedStat(
            "Corroboration rows",
            re.compile(
                r"corroboration rows|2\+ independent sources?|independent source families|"
                r"независимыми источниками",
                re.I,
            ),
            s("Corroboration rows") | s("Legal-grade (≥2 independent source families)"),
        ),
        TrackedStat(
            "Ownerless registry entries",
            re.compile(
                r"ownerless.{0,20}registry entries|запис[еи]й? в реестре",
                re.I,
            ),
            s("registry_inclusion"),
        ),
        TrackedStat(
            "Court cases",
            re.compile(
                r"court cases|occupation court cases|dnr courts?|"
                r"судебных дел|судов «?днр»?",
                re.I,
            ),
            court_cases,
        ),
        TrackedStat(
            "Grant rate %",
            re.compile(r"grant(ed| rate)|удовлетвор", re.I),
            s("Mariupol grant rate %", "Rest-of-DNR grant rate %", "Combined grant rate %"),
        ),
    ]


def label_anchored_findings(path: Path, text: str, tracked: list[TrackedStat]) -> list[str]:
    findings = []
    for m in _STAT_PAIR_RE.finditer(text):
        raw_num = m.group("attr") or m.group("text")
        value = try_parse_number(raw_num)
        if value is None:
            continue
        label = strip_label(m.group("label"))
        if not label:
            continue
        for stat in tracked:
            if not stat.matches_label(label):
                continue
            if not stat.acceptable:
                break  # nothing current to compare against yet -- skip silently
            if not stat.is_acceptable(value):
                shown = m.group("attr") or m.group("text").strip()
                findings.append(
                    f"  [{stat.name}] shows {shown!r} (label: {label!r}) -- "
                    f"current acceptable value(s): {sorted(stat.acceptable)}"
                )
            break
    return findings


def stale_literal_findings(text: str) -> list[str]:
    findings = []
    for literal in STALE_LITERALS:
        if literal in text:
            findings.append(f"  [known-stale literal] {literal!r} found verbatim")
    return findings


def main() -> int:
    if not STATS_MD.exists():
        print(f"ERROR: {STATS_MD} not found", file=sys.stderr)
        return 2
    stats = parse_stats_md(STATS_MD.read_text(encoding="utf-8"))
    if not stats:
        print("ERROR: parsed zero rows out of docs/STATS.md -- format may have "
              "changed; update parse_stats_md() before trusting this lint.",
              file=sys.stderr)
        return 2
    tracked = build_tracked_stats(stats)

    files = sorted(EXHIBITS_DIR.glob("*.html"))
    if INDEX_HTML.exists():
        files.append(INDEX_HTML)

    total_findings = 0
    for path in files:
        raw = path.read_text(encoding="utf-8", errors="ignore")
        clean = _STRIP_BLOCK_RE.sub(" ", raw)
        findings = label_anchored_findings(path, clean, tracked)
        findings += stale_literal_findings(clean)
        if findings:
            total_findings += len(findings)
            rel = path.relative_to(ROOT)
            print(f"\n{rel}")
            for f in findings:
                print(f)

    print(
        f"\n{'=' * 60}\n"
        f"{total_findings} finding(s) across {len(files)} file(s) "
        f"checked against docs/STATS.md."
    )
    if total_findings:
        print("Fix the drift or, if the number is legitimately correct and "
              "this lint just doesn't recognize it, extend build_tracked_stats() "
              "or STALE_LITERALS in scripts/238_lint_stats_drift.py.")
    return 1 if total_findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
