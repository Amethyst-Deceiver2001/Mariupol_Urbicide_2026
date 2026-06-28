"""Registry of occupation court portals (ГАС «Правосудие»).

SCOPE: was Mariupol-only (4 district courts); expanded 2026-06-27 to ALL 39
original-jurisdiction (district/city/inter-district) civil courts in DNR
region 93, per the project's pivot to full-population SC DNR appellate
coverage (`docs/dnr_bezkhoz_appellate_outcomes_2026-06.md`) — appeals can
only be enumerated against a complete first-instance base, and the rest-of-
DNR comparison group for the Mariupol citizenship-doctrine finding
(`docs/dnr_bezkhoz_citizenship_doctrine_2026-06.md`) needs first-instance
saturation outside Mariupol too, not just whatever appeals happened to reach
the Supreme Court.

Source for the court list + domains: the public court directory at
xn--d1aiaa2aleeao4h.xn--p1ai (суды.рф), region "Донецкая Народная
Республика", "Региональные суды" listing, 41 entries fetched 2026-06-27.
Excluded from COURTS below:
  - Верховный суд ДНР (Supreme Court) — separate module, `dnr_supreme_court.py`.
  - Донецкий гарнизонный военный суд (Military Garrison Court) — military
    jurisdiction, does not hear civil бесхозяйная-недвижимость cases.
That leaves 39 civil courts (35 newly added here + the 4 pre-existing
Mariupol entries, origins unchanged).

DOMAIN-FORM CAVEAT: the directory lists each court's site as
`<subdomain>.dnr.sudrf.ru` (single dot). The 4 Mariupol courts below were
independently confirmed working at `<subdomain>--dnr.sudrf.ru` (double dash)
— that is the live GAS «Правосудие» convention for this portal generation, not
a typo. All 35 new entries apply that same `--dnr.sudrf.ru` transform to the
directory's single-dot domain, by inference from the 4 known-good entries —
**not yet individually re-verified against each portal**. Two entries had no
explicit "Официальный сайт" field on the directory page at all (only a
`<slug>.dnr@sudrf.ru` contact email, from which the domain was inferred):
Дружковский (`druzhkovskiy`) and Угледарский (`ugledarskiy`) — flagged below.
A wrong/dead origin just produces request failures the crawler logs and skips
(`court_crawler.crawl_court` continues to the next court on exception) — no
destructive effect, but expect a few of these 35 to need a one-line domain
fix after the first run.

Note on the original three Mariupol courts from HRW rulings (unchanged):
  - Pershotravnevy was relocated to Mangush (`mng--dnr.sudrf.ru` below) — no
    longer a Mariupol court, but still a DNR civil court, now added.
  - Telmanovsky: this project's earlier note said it was "abolished by Law
    55-РЗ", but the directory still lists an active site (`tlm--dnr.sudrf.ru`)
    with current judge entries (2026) — added, flagged for reconciliation;
    either the abolition note was wrong or the portal persists for legacy
    case lookup after a 2024 merger.
  - Primorsky absorbed Ilyichevsky and Ordzhonikidzevsky jurisdictions per a
    2023 RF Supreme Court Presidium decision, but all four portals remain live.

Zhovtnevy court is explicitly confirmed to handle 66-РЗ ownerless-property
(бесхозяйная недвижимость) cases — the primary case type for this project.
`court_crawler.crawl_court` already filters every court's results to the
ownerless/municipal-property frame via the `RELEVANT` regex — adding courts
here does not require a different case-type filter per court, only the
{court} origin substitution into the shared `config.RESULTS_TEMPLATE`.

HOW TO ENABLE/FIX A COURT
--------------------------
1. Open the court's portal in a browser via your Russia-routed proxy.
2. Go to "Судебное делопроизводство" → search for ownerless-property cases.
3. Open DevTools → Network → copy the GET URL for the results page.
4. Verify the URL contains modules.php?name=sud_delo.
5. Set enabled=True for that court entry below (already True for all 39).
6. If the origin is wrong, the existing `config.RESULTS_TEMPLATE` should still
   work once the domain is corrected — it parameterizes only {court}.
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


# All 39 original-jurisdiction civil courts in DNR (region 93). Origins for the
# 4 Mariupol courts are independently confirmed; the other 35 apply the
# `--dnr.sudrf.ru` transform inferred from those 4 (see module docstring) and
# should be treated as provisional until the first crawl run confirms each.
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
    Court(
        key="avdeevsky",
        name="Авдеевский городской суд",
        origin="https://avd--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="aleksandrovsky",
        name="Александровский районный суд",
        origin="https://aleksandrovskiy--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="amvrosievsky",
        name="Амвросиевский районный суд",
        origin="https://amv--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="artemovsky",
        name="Артемовский городской суд",
        origin="https://art--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="budennovsky_donetsk",
        name="Буденновский межрайонный суд г. Донецка",
        origin="https://bud--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="velikonovoselkovsky",
        name="Великоновоселковский районный суд",
        origin="https://velikonovoselovskiy--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="volnovakhsky",
        name="Волновахский районный суд",
        origin="https://vln--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="volodarsky",
        name="Володарский районный суд",
        origin="https://vld--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="voroshilovsky_donetsk",
        name="Ворошиловский межрайонный суд г. Донецка",
        origin="https://vr--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="gorlovsky",
        name="Горловский городской суд",
        origin="https://cg-gorl--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="gornyatsky_makeevka",
        name="Горняцкий районный суд г. Макеевки",
        origin="https://gorn--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="debaltsevsky",
        name="Дебальцевский городской суд",
        origin="https://deb--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="dzerzhinsky",
        name="Дзержинский городской суд",
        origin="https://dzerzhinskiy--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="dimitrovsky",
        name="Димитровский городской суд",
        origin="https://dimitrovskiy--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="dobropolsky",
        name="Добропольский городской суд",
        origin="https://dobropolskiy--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="dokuchaevsky",
        name="Докучаевский городской суд",
        origin="https://dok--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="druzhkovsky",
        name="Дружковский городской суд",
        origin="https://druzhkovskiy--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
        # UNVERIFIED: directory page showed only a contact e-mail
        # (druzhkovskiy.dnr@sudrf.ru), no explicit "Официальный сайт" field;
        # domain inferred by the same --dnr.sudrf.ru transform. Re-verify first.
    ),
    Court(
        key="enakievsky",
        name="Енакиевский межрайонный суд",
        origin="https://enak--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="kirovsky_donetsk",
        name="Кировский межрайонный суд г. Донецка",
        origin="https://kir--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="konstantinovsky",
        name="Константиновский городской суд",
        origin="https://konstantinovskiy--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="kramatorsky",
        name="Краматорский городской суд",
        origin="https://kram--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="krasnoarmeysky",
        name="Красноармейский городской суд",
        origin="https://krasn--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="krasnolimansky",
        name="Краснолиманский городской суд",
        origin="https://krasnolimanskiy--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="marinsky",
        name="Марьинский районный суд",
        origin="https://marin--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="novoazovsky",
        name="Новоазовский районный суд",
        origin="https://nva--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="novogrodovsky",
        name="Новогродовский городской суд",
        origin="https://novogrodovskiy--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="pershotravnevy_mangush",
        name="Першотравневый районный суд (Мангуш)",
        origin="https://mng--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
        # Relocated from Mariupol to Mangush; "mng" domain code confirms.
    ),
    Court(
        key="selidovsky",
        name="Селидовский городской суд",
        origin="https://selidovskiy--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="slavyansky",
        name="Славянский городской суд",
        origin="https://slav--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="starobeshevsky",
        name="Старобешевский районный суд",
        origin="https://star--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="telmanovsky",
        name="Тельмановский районный суд",
        origin="https://tlm--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
        # Directory shows this portal as active (2026 judge entries) despite
        # this project's earlier note that Law 55-РЗ abolished the court —
        # reconcile if a crawl run returns nothing or 404s consistently.
    ),
    Court(
        key="ugledarsky",
        name="Угледарский городской суд",
        origin="https://ugledarskiy--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
        # UNVERIFIED: directory page showed only a contact e-mail
        # (ugledarskiy.dnr@sudrf.ru), no explicit "Официальный сайт" field;
        # domain inferred by the same --dnr.sudrf.ru transform. Re-verify first.
    ),
    Court(
        key="khartsyzsky",
        name="Харцызский межрайонный суд",
        origin="https://harc--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="centralno_gorodskoy_makeevka",
        name="Центрально-Городской районный суд г. Макеевки",
        origin="https://centralno-gorodskoy--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
    Court(
        key="yasinovatsky",
        name="Ясиноватский городской суд",
        origin="https://yasin--dnr.sudrf.ru",
        region="DNR",
        enabled=True,
    ),
]


def enabled_courts() -> list[Court]:
    return [c for c in COURTS if c.enabled and c.origin]
