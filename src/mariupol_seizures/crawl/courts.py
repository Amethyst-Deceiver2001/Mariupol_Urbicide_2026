"""Registry of occupation court portals (ГАС «Правосудие»).

SCOPE: Mariupol only. Four district courts currently operate in Mariupol under
the Russian *.dnr.sudrf.ru system after DNR Law 55-РЗ (22 Feb 2024) dissolved
the old DNR court structure and integrated it into the Russian federal
judiciary.

Note on the original three courts from HRW rulings:
  - Pershotravnevy was relocated to Mangush (no longer a Mariupol court).
  - Telmanovsky was abolished by Law 55-РЗ.
  - Primorsky absorbed Ilyichevsky and Ordzhonikidzevsky jurisdictions per a
    2023 RF Supreme Court Presidium decision, but all four portals remain live.

Zhovtnevy court is explicitly confirmed to handle 66-РЗ ownerless-property
(бесхозяйная недвижимость) cases — the primary case type for this project.

HOW TO ENABLE A COURT
---------------------
1. Open the court's portal in a browser via your Russia-routed proxy.
2. Go to "Судебное делопроизводство" → search for ownerless-property cases.
3. Open DevTools → Network → copy the GET URL for the results page.
4. Verify the URL contains modules.php?name=sud_delo.
5. Set enabled=True for that court entry below.
6. Capture a working RESULTS_TEMPLATE from that URL (see config.py).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Court:
    key: str
    name: str
    origin: str   # https://hostname only — no trailing slash
    region: str   # "DNR" | "LNR"
    enabled: bool = False


# Active Mariupol courts on *.dnr.sudrf.ru. Origins confirmed; enable after
# verifying modules.php?name=sud_delo is reachable through your proxy.
COURTS: list[Court] = [
    Court(
        key="primorsky_mariupol",
        name="Приморский районный суд г. Мариуполя",
        origin="https://mar-prim--dnr.sudrf.ru",
        region="DNR",
        enabled=True,   # enabled 2026-06-09
        # Absorbed Ilyichevsky + Ordzhonikidzevsky jurisdictions (2023).
    ),
    Court(
        key="zhovtnevy_mariupol",
        name="Жовтневый районный суд г. Мариуполя",
        origin="https://mar-zhovt--dnr.sudrf.ru",
        region="DNR",
        enabled=True,   # URL + template confirmed 2026-06-08
    ),
    Court(
        key="ilyichevsky_mariupol",
        name="Ильичевский районный суд г. Мариуполя",
        origin="https://mar-ilich--dnr.sudrf.ru",
        region="DNR",
        enabled=True,   # enabled 2026-06-09
    ),
    Court(
        key="ordzhonikidzevsky_mariupol",
        name="Орджоникидзевский районный суд г. Мариуполя",
        origin="https://mar-ordzh--dnr.sudrf.ru",
        region="DNR",
        enabled=True,   # enabled 2026-06-09
    ),
]


def enabled_courts() -> list[Court]:
    return [c for c in COURTS if c.enabled and c.origin]
