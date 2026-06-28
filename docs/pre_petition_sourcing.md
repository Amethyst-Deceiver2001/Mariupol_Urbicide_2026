# Pre-petition lifecycle sourcing plan

**Status:** open gap, scoped 2026-06-08.
**Problem:** the Zhovtnevy court dataset (827 cases) only yields the *downstream*
lifecycle stages — `court_petition` (1,920 events) and `court_transfer`
(1,439 events). The four **pre-petition** rungs of the lifecycle model in
`CLAUDE.md` / `reconceptualization_2026.md` are empty in the DB:

```
utility_cutoff → notice → inspection → ownerless_designation → [court_petition → court_transfer]
└──────────────────── 0 events captured ───────────────────┘   └──── captured ────┘
```

This document scopes how to corroborate the pre-petition chain. **The headline
finding: it is not one missing source but four rungs with different origins, and
three of the four are recoverable from sources already in the project's planned
universe.**

---

## 1. Each rung's record-of-origin

| Rung | Record of origin | Tractable? | Where it actually lives |
|---|---|---|---|
| `utility_cutoff` | Utility-operator records (Вода Донбасса, Мариупольэнерго) | **No** — no public series | Recited as a *finding* inside the inspection act ("отсутствие потребления ресурсов") |
| `notice` (30-day "come forward") | Published **ownerless lists** | **Yes** | Mariupol admin site / gosuslugi subdomain / Telegram (Tier-1 lists) |
| `inspection` (акт обследования межведомственной комиссии) | Commission inspection act | **Partly** | Recited in the court ruling text; sometimes appended to the admin decree |
| `ownerless_designation` | Admin постановление + **Rosreestr ownerless-registration** | **Partly** | Recited in the court ruling (with date); published as an NPA |

## 2. The procedural lever — ГК РФ ст. 225

A municipality cannot petition the court (особое производство, ГПК РФ гл. 33,
ст. 290–293) until the immovable has been:

1. placed on **Rosreestr ownerless-registration** (учёт бесхозяйного имущества) —
   on application of the local self-government body, and
2. found abandoned by an **inspection act** (акт обследования).

Both are **legal preconditions the petition must plead**, so the court ruling
recites the registration/notice date and the inspection findings (the notorious
"overgrown grass / closed door" grounds; see `reconceptualization_2026.md:49`).

**Consequence:** fetching the ruling-document texts ("ДОКУМЕНТЫ СУДА" PDFs,
currently uncaptured) corroborates **3 of the 4** pre-petition rungs — `notice`,
`inspection`, `ownerless_designation` — *from within the same evidentiary
source*. That same fetch is also what closes the **address gap** (the addresses
are only in those documents, not the case-card HTML). Two of the report's
biggest gaps collapse into one build.

Only `utility_cutoff` genuinely needs an external source, and it is realistically
a **derived signal** read out of the inspection-act text — not a standalone
series to crawl.

## 2a. CONCRETE SOURCE IDENTIFIED (2026-06-08)

Verified live (via WebFetch + WebSearch — these are public muni/ministry sites,
not the geoblocked court portals):

### Primary — Mariupol municipal administration's own published register
**This is the actual upstream of the 805/827 (97%) court petitions filed by
"Администрация городского округа Мариуполь."**

- Landing page: `https://mariupol.gosuslugi.ru/dlya-zhiteley/poleznye-materialy/ownerless/`
  (mirror: `mariupol-r897.gosweb.gosuslugi.ru/dlya-zhiteley/poleznye-materialy/ownerless/`)
- **Four downloadable XLSX registries — one per court district**, an exact join
  key to our existing court data:
  - `/netcat_files/418/7755/Zhovtnevyi_r_n.xlsx`
  - `/netcat_files/418/7755/Primorskii_r_n.xlsx`
  - `/netcat_files/418/7755/Il_ichevskii_r_n.xlsx`
  - `/netcat_files/418/7755/Ordzhonikidzevskii_r_n.xlsx`
  (paths relative to the gosuslugi origin above; snapshot dated 17.03.2026 at
  time of check — these are living documents, re-fetch periodically and keep
  every dated snapshot, since "lists are edited/removed.")
- **101 numbered, dated administrative decrees (постановления)** on the same
  page — both *designations* ("О признании... бесхозяйным и включении в
  реестр", e.g. № 194, 20.02.2026) and *removals* ("О снятии с учета
  недвижимой вещи" / "Об исключении имущества", e.g. № 999, 26.05.2026; № 506,
  05.03.2026). Each has its own detail-page URL
  (`.../postanovleniya-amministratsii-gorodskogo-okruga-mariupol_<ID>.html`),
  a number, a date, and (presumably, pending capture) a signing official —
  i.e. **citable `ownerless_designation` events with named accountable actors**.
- The "removal" decrees are the institutional mirror of the court's
  "left_without_consideration" outcome (100 cases / 12% — owner disputes
  found) — an independent confirmation channel for that finding.
- Press mirrors exist (mrpl.news, 0629.com.ua, freeradio.com.ua routinely
  republish full address lists as journalism) — useful as **resilient
  corroboration** if/when the occupation administration edits or removes
  entries from the live page.

### Secondary — DNR Ministry of Construction (МИЗО ДНР) open-data CSV register
- `https://minstroy-dpr.gosuslugi.ru/otkrytoe-ministerstvo/otkrytye-dannye/nabory-dannyh/`
  → dataset "Бесхозяйное недвижимое имущество", direct CSV downloads, e.g.
  `https://minstroy-dpr.gosuslugi.ru/app/uploads/2024/08/30e389_beshoz-2025-na-2025_08_20.csv`
  (+ versioned snapshots: `..._2025_08_18.csv`, `..._16.05.2025.csv`, etc.)
- **Schema (from `struktura.csv`):** № п/п | РОИВ | Дата запроса МИЗО ДНР |
  № запроса МИЗО ДНР | Основание (cites the designation decree, e.g.
  "Постановление Правительства ДНР от 22.06.2023 № 45-5") | Бесхозяйное
  имущество (description) | Адрес расположения | Примечание.
- **This is a republic-level (not municipal) register, and it's a different,
  smaller stream** — only ~4 Mariupol entries per ~265-row snapshot, all
  large *non-residential* commercial/institutional buildings (a Greek medical
  centre, a filling station, a Renault dealership, etc.), filed by МИЗО ДНР —
  the petitioner that appears in only 9/827 of our court cases. **Not the
  primary upstream of the residential docket**, but a genuine independent,
  structured, dated, legally-grounded register — valuable as (a) a model for
  what the full schema should look like, and (b) a corroboration/cross-check
  source for the small institutional-property subset of cases.
- Geoblocked at the network level for the same reason as the court portals
  (a direct `curl` from a US-based machine fails the TLS handshake entirely;
  WebFetch succeeded only because it routes through Anthropic's own
  infrastructure) — capture from the VPS, same as everything else.

## 3. The independent second source (≥2-source legal-grade rule)

CLAUDE.md requires ≥2 independent sources for legal-grade linkage. The court
ruling supplies the `notice`/`designation` rungs *internally*; the independent
confirmation is the **published ownerless list** — the documented *upstream* of
the court cases (`reconceptualization_2026.md:55-59`):

- **Source:** Mariupol occupation municipal sites (gosuslugi.ru subdomains,
  mrpl.news, district-administration pages) + Telegram channels; published
  "several times per month," Left-Bank batches run to thousands.
- **Unit:** each list entry = a dated `notice` event for one address.
- **The join that matters:** list-`notice` ⋈ court-`petition`/`transfer` on the
  same property (via the toponymic / re-addressing table) = the full chain with
  two independent occupation sources. **Join, don't silo.**

External baselines (Tier 2, framing/corroboration only, not granular events):
OHCHR HRMMU 43rd report (5,557 formally designated "abandoned", Dec 2025);
Andriushchenko / Center for the Study of Occupation (utility-cut signal,
+100–200/week designation rate); Leibniz-IfL VisLab (already scraping + geocoding
the lists — collaborate, don't rebuild).

## 4. CORRECTION (2026-06-08): there is no case-specific document link

Inspecting a captured case card directly (`case_uid 0527015e-...`, decoded from
windows-1251) shows it carries **no case-specific ruling/document URL**. The
only "documents" references are generic site nav:

- `/modules.php?name=docum_sud` — a general court-documents module, not scoped
  to a case (matches what the prior session already flagged)
- `https://ej.sudrf.ru/?fromOa=93RS0006` — a **separate** federal
  "электронное правосудие" portal; never crawled; unknown whether/how it
  exposes full judicial-act texts per case

So "fetch the linked ruling document" is **not a build-ready step** — it's a
**discovery question**: do full-text rulings for особое производство
(named-individual proceedings) get published online *at all*? Russian court
systems often redact or withhold full texts naming private individuals from
public portals. If they're not published anywhere reachable, the
address/inspection/notice data has **no online path through this source** and
must come entirely from the independent streams (§3).

## 5. Recommended order (revised — now with a concrete target)

1. **Build the Tier-1 list crawler against the source in §2a — this is now
   build-ready, not speculative.** Capture (forensically — SHA-256, dated
   sidecars, append-only) the four district XLSX snapshots + decree detail
   pages on a recurring cadence (snapshots change ~weekly per Andriushchenko's
   "+100–200/week"; keep every dated capture as its own row, never overwrite).
   This is independent of the court portal, **doesn't depend on (0)/(1)
   below**, and is the *required* second source for ≥2-source legal-grade
   linkage regardless of what happens with court rulings. **Start here.**
2. **Parse + load:** XLSX rows → `seizure_event(stage='notice')` /
   `ownerless_designation` keyed by district (= direct join to `court_case`
   via the district↔court mapping); decree pages → dated, numbered,
   citable `ownerless_designation`/exclusion events with named signing
   officials → `actor(role='signing_official')`.
3. ~~**Verification**~~ — **(b) SETTLED 2026-06-28, negative.**
   `scripts/196_probe_ej_sudrf_fulltext.py` confirmed `ej.sudrf.ru` is not a
   public full-text search portal — it's an authenticated personal-account
   system ("Дела" = cases *you* are a party to, gated behind `need_auth=1`),
   structurally incapable of exposing rulings to a non-party. Combined with
   the docket-card finding above (§4), **both routes to closing the address
   gap on the 2,657+ court islands are now closed** — there is no public
   path to per-case full texts through any sudrf.ru-family source. (a)
   `docum_sud` case/judge/date filtering remains unchecked but is moot for
   the address gap specifically, since it's the same generic-module problem
   §4 already diagnosed, not a per-case lookup.
4. **`utility_cutoff` has no public source** — (3)(b)'s negative result
   closes this off too; not pursuing further through the court portals.
5. **Schema touch:** record which source series each `seizure_event` came from
   (court ruling vs. published list vs. decree vs. Rosreestr) so the
   ≥2-source count is auditable per property.

## 5. What NOT to claim

Until rungs are actually captured, the report must not imply the pre-petition
chain is documented — it is currently inferred from the procedure, not evidenced
per-property. State pre-petition rungs as **"required by ГК РФ ст. 225, not yet
captured"** rather than asserting them as recorded events.
