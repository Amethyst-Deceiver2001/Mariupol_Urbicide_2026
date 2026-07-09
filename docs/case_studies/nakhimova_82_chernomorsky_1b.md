# Case Study — prosp. Nakhimova 82 → per. Chernomorsky 1B

**The complete demolish→rebuild→resell lifecycle of a single Mariupol building,
documented end-to-end from the Russian occupation's own records.**

A privatized 36-apartment residential building is destroyed in the 2022 siege,
formally demolished by occupation decree, its cleared land handed to a developer
without auction, and a new 51-apartment building raised on the same footprint
under a *new street address and new cadastral number* — then sold, 94% of it, to
the occupier's own population on subsidized mortgages. The displaced owners get
nothing, because on paper "takogo adresa fizicheski ne sushchestvuet" — no such
address physically exists.

This is the project's reference example of the **address-laundering seizure
modality** (`memory/demolition_rebuild_address_laundering.md`). It is the
strongest single exhibit linking *property → seizure act → named beneficiary*
across both downstream endpoints (RD4U restitution + Rome Statute
accountability), because every leg is attested by a captured, hashed,
occupation- or federal-government record.

---

## The two property rows

| | ORIGINAL | REPLACEMENT |
|---|---|---|
| DB property id | **5865** | **6333** |
| building_id | `AVENUE:нахимова\|82` | `LANE:черноморский\|1б` |
| Occupation address | prosp. Nakhimova, 82 | per. Chernomorsky, 1B |
| District | Primorsky | Zhovtnevy / Primorsky border |
| Cadastral | — | **93:37:0010410:173** |
| Geocode | 47.076027, 37.5125162 | 47.0761, 37.5126 |

**Footprint match: ~10 metres apart.** The two geocodes are the same building
site to within GPS noise — the physical-continuity proof that the address change
is conceals.

---

## The five legs of the lifecycle — each with its source artifact

> Every row below is a real record already loaded into the evidence DB, with a
> SHA-256 hash and capture timestamp (Berkeley Protocol chain of custody). These
> are the occupation's / Russian federation's *own* documents — self-incriminating
> admissions, not third-party assertions.

### 1 — INTACT (pre-war)
- **What it was:** a 4-storey multi-apartment residential building (MKZhD,
  residential-class), **36 apartments**, 3 entrances, privately owned/privatized.
- **Source:** Russian federal damage/reconstruction tracker, building record —
  `property_type=жилое`, `building_class=МКЖД`, `floors=4`, `apartments=36`.
- **Artifact:** `Russian_damage_assessment.xlsx` · SHA-256 `0bd1edf7…d9d7c7`
  · captured 2026-06-09.

### 2 — DAMAGED (during the siege)
- **What happened:** **100% destruction.** Burned March 2022 (HRW siege record).
  Flagged Priority Phase II in the reconstruction tracker.
- **Source:** same damage tracker — `destruction_pct=100.0`,
  `priority_phase=II`, named clean-up contractors LLC (OOO) «Monotek Stroi» /
  JSC (AO) «INTEKO», responsible executor public-law company (PPK)
  «Edinyi zakazchik».
- **Artifact:** `Russian_damage_assessment.xlsx` · SHA-256 `0bd1edf7…d9d7c7`.

### 2b — DISPLACEMENT (corroborating the human loss)
- **What it shows:** at least **1 household** from this address appears on the
  occupation's own displaced-persons housing-distribution list — i.e. the
  occupation administration itself records that the residents lost access to
  this property (RD4U category A3.6).
- **Source:** Mariupol occupation housing-distribution list, 27.05.2026.
- **Artifact:** `Raspredelenie_zhil_ya_ot_27.05.2026.xlsx` · SHA-256
  `927c3fcc…ef33`.

### 3 — DEMOLISHED (after)
- **What happened:** razed under **State Defense Committee (GKO) DNR Directive
  No. 56, 29.09.2022**, listed as "g. Mariupol, prosp. Nakhimova, d. 82 (Zdanie
  zhilogo doma)" — the registry's own "residential building" entry.
- **Source:** DNR MinStroy open-data demolition register (snapshot 16.03.2026).
- **Artifact:** `minstroy-dpr.gosuslugi.ru/.../reestr-snosa_16_03_2026.csv` ·
  SHA-256 `d431a530…42ea37` · captured 2026-06-09.
- **DB:** `seizure_event` 54105, stage `demolition`, date **2022-09-29**.

### 3b — TERRITORIAL CONTEXT: the demolition sat inside a formal redevelopment zone
- **What it shows:** Directive No. 289's parcel description — "bounded by
  prosp. Nakhimova and ul. Chernomorskaya" — is not an ad hoc description of a
  single lot. It is the footprint of a named **KRT (compleks development of
  territory) project-planning-territory (PPT) zone**, ~36 hectares, in the
  Primorsky district, authorizing demolition of **9 multi-apartment buildings**
  including this one — confirmed by a Minstroy DNR PPT document
  (`@minstroydnr/3932`, October 2023) signed by **Aleksandr Avdiyenko**, head of
  urban-planning and architecture, Minstroi DNR. The parcel-level land grant to
  Porfir is the per-building act *inside* a zone Minstroy itself designated for
  clearance — the demolition of Nakhimova 82 was planned at the zone level
  before any single-building decree existed, not decided building-by-building.
- **Source:** Minstroy DNR project-planning-territory (PPT) document.
- **Artifact:** `@minstroydnr/3932` (Telegram channel post, geoblocked source,
  in raw store by SHA-256); see `docs/legal_mechanisms_review.md` for the full
  KRT/PPT zone reconciliation against the land-grant register.

### 4 — REBUILT (new building, same spot, new address)
- **What rose:** **«Dom na Nakhimova»** ("the house on Nakhimova") — a
  5-storey, **51-apartment** building (2,324 m² living area), registered at
  the *new* postal address **per. Chernomorsky 1B**, new cadastral
  **93:37:0010410:173**, **commissioned 29.12.2023**.
- **Land grant:** the cleared parcel was leased to the developer **without
  auction** via **Directive No. 289, 07.09.2023** (parcel described as
  "territoriya ogranichena prospektom Nakhimova, ulitsei Chernomorskoi" —
  "the parcel bounded by Nakhimov Avenue and Chernomorskaya Street" — same
  cadastral 93:37:0010410:173).
- **Source:** EISZhS / nash.dom.rf object **54284**, RPD 93-000002.
- **Artifact:** `nash.dom.rf/.../api/object/54284` · SHA-256 `443936eb…57b712`
  · captured 2026-06-09.
- **DB:** `seizure_event` 54173, stage `reallocation`, date **2023-12-29**.

### 5 — SOLD (apartments resold to the occupier's population)
- **What it shows:** **94.3% sold** (`sold_out_perc = 0.9434`) as of the
  2026-06-09 EISZhS snapshot — overwhelmingly to Russian buyers via the
  federal 2% subsidized mortgage program open to any Russian citizen
  (population-transfer financial channel; `memory/demand_side_architecture.md`).
- **Source / artifact:** same EISZhS record 54284 (the registry carries the
  live sold-out percentage).
- **The mortgage decree itself, now captured (2026-07-04):** Russian
  Government Decree **No. 2565 (31.12.2022)** «On approving Rules for
  providing federal-budget subsidies to JSC DOM.RF...» — the primary legal
  instrument behind the 2% rate. §k) confirms verbatim: "the interest rate
  under the loan agreement is no more than 2 percent per annum," minimum 10%
  down payment, for loans "issued to citizens of the Russian Federation for
  the purchase or construction of residential premises in the territories of
  the DNR, LNR, Zaporizhzhia, and Kherson regions" — the decree's own text
  names no residency restriction, confirming any Russian citizen qualifies,
  not just local residents. In force from 1 January 2023.
- **Artifact:** publication.pravo.gov.ru, `eoNumber=0001202301030011` (signed
  PDF, 46pp, Mishustin signature block), OCR'd (`scripts/246`, 2026-07-04).

### Beneficiary (named, in scope for accountability — NOT minimized)
- **LLC, specialized developer (OOO SZ-1) «Porfir»** — INN **9310009271**,
  OGRN **1239300008870**, registered 11.07.2023, director Bogdan Rasskazov
  (Рассказов Богдан Денисович); brand group **GK YugStroiInvest** (Stavropol).
- **DB:** actor 14485, role `beneficiary`, linked to the reallocation event.
- ⚠ Source conflict to resolve before court use: director named as Bogdan
  Rasskazov (EISZhS) vs Vladimir Karpov (Карпов Владимир Николаевич, other
  sources); registered address prosp. Stroiteley 60 vs Chernomorsky 1B —
  verify via EGRUL.
- **Not a single-address developer.** Reconciling the full denis-pushilin.ru
  land-grant archive (`scripts/249`/`250`/`252`, 2026-07-04/05;
  `docs/legal_mechanisms_review.md`) found Porfir holds **9 parcels, ~97,000 m²
  total**, almost all one contiguous land assembly in Zhovtnevyi district
  bounded by prosp. Lenina / ul. Kazantseva / ul. Apatova / prosp. Nakhimova /
  ul. B. Khmelnitskogo / ul. Bakhchivandzhi / ul. Zelinskogo — subdivided into
  named projects at prosp. Stroiteley 74/76/78/80/88 and ul. Zelinskogo
  23/30A/30B, in addition to the Nakhimova 82/Chernomorsky 1B parcel documented
  here. Across the reconciled 101-decree land-grant set, Porfir is **the single
  largest developer-beneficiary** of no-tender Mariupol land. This building is
  one node in a much larger land assembly by the same beneficiary, not an
  isolated grant.

---

## The smoking gun

The Russian state's **own EISZhS registry simultaneously proves both halves of
the laundering**:

- it names the project **«Dom na Nakhimova»** — admitting the building stands
  on the **Nakhimova** site;
- while assigning it the postal address **per. Chernomorsky 1B** — the address
  break that severs the identity chain to destroyed prosp. Nakhimova 82.

And the **cadastral 93:37:0010410:173** appears in *both* the land-allocation
order (Directive No. 289, "bounded by Nakhimov Avenue and Chernomorskaya
Street") and the new building's registration — a single number stitching the
old footprint to the new title.

**A second, independent federal admission.** The DNR land order isn't the only
document that names this building "Nakhimova, 82" — the developer's own **RPD
(project) declaration No. 93-000002, filed with the federal nash.dom.rf /
Minstroi registry on 09.01.2024**, opens with the project title (original
Russian, verbatim from the PDF):

> «Многоквартирный жилой дом со встроенными помещениями по пр-ту Нахимова, 82 в
> г. Мариуполе.»

English: "Multi-apartment residential building with built-in premises at
prosp. Nakhimova, 82, in the city of Mariupol."

This is a *different issuing layer* (federal housing-construction oversight, not
DNR regional land administration) independently calling the Chernomorsky-1B
building "Nakhimova, 82" — extracted via `scripts/19_ocr_rpd_pdf.py`
(`project_title_in_pdf` field, added 2026-06-11) from the already-captured PDF
(SHA-256 `eca27d52…b4ec2`).

A third trace: the building's own marketing-render files, embedded in the
EISZhS object record (`photoRenderDTO[].objRenderPhotoNm`), are named
`Нахимова_82_Top2.jpg`, `Нахимова_82_Corona_Camera0111.jpg`,
`Нахимова_82_2_Top2.jpg`, `Нахимова_82_2_Corona_Camera0093.jpg`,
`Нахимова_82_Top4.jpg` (literal filenames, kept verbatim as the chain-of-custody
artifact name) — the developer's internal asset-naming convention preserves the
old address ("Nakhimova_82") even in files served under the new one.

**The arithmetic of the dispossession:** a 36-apartment privately owned building
→ destroyed → becomes a 51-apartment building, 94% sold to incomers on
subsidized mortgages. The original owners are off the map.

---

## Legal mapping

- **RD4U restitution:** category **A3.6** (loss of access to property in occupied
  territory) is established; the demolition + 100% destruction record also
  supports **A3.1/A3.2** (destruction of/damage to residential property). The
  address change is itself the mechanism of denial the Register exists to
  overcome.
- **Rome Statute:** demolition decree (intent) + no-auction land grant to a named
  SPV (system) + 94%-sold new build to the occupier's population (beneficiary +
  population transfer) maps to **art. 8(2)(b)(viii)** (transfer of the occupier's
  own population into occupied territory) and unlawful **appropriation of
  property** (art. 8(2)(a)(iv)).

---

## Timeline

| Date | Event | Source |
|---|---|---|
| pre-2022 | prosp. Nakhimova 82: 4-storey, 36-apartment privatized MKZhD | damage tracker |
| **Mar 2022** | Destroyed in the siege — 100% destruction | damage tracker / HRW |
| **29 Sep 2022** | Demolished — GKO DNR Directive No. 56 | MinStroy register |
| **07 Sep 2023** | Land leased to OOO SZ-1 «Porfir» w/o auction — Directive No. 289 | DNR land order |
| **29 Dec 2023** | «Dom na Nakhimova» commissioned as Chernomorsky 1B, 51 apts | EISZhS 54284 |
| 2024–2026 | Apartments sold — 94.3% as of Jun 2026 | EISZhS 54284 |
| 27 May 2026 | ≥1 displaced household still listed for lost-access housing | distribution list |

---

## Visual-evidence collection targets

To pair the documentary chain with imagery (for the visualization and the
exhibit). Coordinates are the loaded geocodes.

- **Site coordinates:** `47.0760, 37.5125` (both old and new — same spot).
- **LEG 1 (intact pre-war):**
  - Google Street View / Yandex Panorama historical imagery at the coordinates,
    pre-2022 — capture the original 4-storey building.
  - Pre-war photos: search "prospekt Nakhimova 82 Mariupol" on Yandex Images,
    panoramio archives, and the Wayback Machine for 2gis/Yandex Maps captures.
- **LEG 2 (damaged):**
  - Google Earth Pro historical imagery timeline (2022–2023) at the coordinates
    — show the burned/destroyed shell.
  - Maxar/Planet satellite stills from spring–summer 2022 (widely published for
    Mariupol); UNOSAT damage-assessment overlays.
- **LEG 3 (demolished):**
  - Google Earth historical imagery late 2022 / 2023 — cleared lot / rubble
    removal.
- **LEG 4 (rebuilt):**
  - nash.dom.rf object 54284 — 5 marketing-render images, all dated
    14.09.2023, filenames `Нахимова_82_Top2.jpg`, `Нахимова_82_Corona_Camera0111.jpg`,
    `Нахимова_82_2_Top2.jpg`, `Нахимова_82_2_Corona_Camera0093.jpg`,
    `Нахимова_82_Top4.jpg` (URLs + filenames captured in the object detail JSON
    and SSR page; **the image bytes themselves are not yet downloaded** — see
    "Open items" below). No separate construction-progress photo set exists (the
    object shows "Sdan"/commissioned with renders only).
  - Google Earth / Yandex 2024–2025 imagery — the new building on the footprint.
  - Current Yandex Panorama at Chernomorsky 1B.
- **LEG 5 (sold):**
  - nash.dom.rf / Avito / CIAN listings for per. Chernomorsky 1B — for-sale and
    sold apartment screenshots; 2% mortgage banner.

> Forensic note: any image collected becomes evidence only once captured to the
> raw store with its own SHA-256 + source URL + retrieval timestamp, per
> `CLAUDE.md`. Do not paste screenshots straight into the exhibit — capture
> first, cite the hash.

---

## Provenance (chain of custody)

| Leg | DB ref | Source artifact | SHA-256 | Captured |
|---|---|---|---|---|
| 1+2 | corrob 2855 | Russian_damage_assessment.xlsx | `0bd1edf7…d9d7c7` | 2026-06-09 |
| 2b | corrob 375 | Raspredelenie_zhil_ya_ot_27.05.2026.xlsx | `927c3fcc…ef33` | 2026-06-09 |
| 3 | event 54105 | minstroy reestr-snosa_16_03_2026.csv | `d431a530…42ea37` | 2026-06-09 |
| 4+5 | event 54173 | EISZhS api/object/54284 (detail JSON) | `443936eb…57b712` | 2026-06-09 |
| 4+5 | — | EISZhS katalog-novostroek/obekt/54284 (SSR page) | `57dbae9d…58fe649` | 2026-06-09 |
| 4 (2nd source) | — | RPD declaration No. 93-000002 PDF (project_title_in_pdf) | `eca27d52…b4ec2` | 2026-06-09 |
| 4 (RnV permit) | — | RnV No. 93-37-1-2023 PDF | `ec3cb2a6…5201b0` | 2026-06-09 |

*Reproducible from raw → DB. Occupation registrations/rulings are evidence of the
seizure act, NOT valid title; Ukraine does not recognize them, and neither do we.*

---

## Open items / completeness audit (2026-06-11)

Audited the captured nash.dom.rf data for object 54284 against the live page
(`/servisy/katalog-novostroek/obekt/54284`) for completeness:

- ✅ API detail JSON, SSR page, RPD declaration PDF, RnV permit PDF — all
  captured (table above). The SSR page's own UI confirms "Documenty
  otsutstvuyut" ("no documents on file") for every document category except
  RPD/RnV, so no hidden document tabs are being missed.
- ✅ The 6 per-object sub-resource endpoints (`permits/documentation/
  infrastructure/rpd/report/other`) were probed for all 20 EISZhS Mariupol
  objects during the 2026-06-09 crawl and returned no data for any of them —
  consistent with the SSR "no documents on file" indicators, not a gap.
- ⚠ **Not yet captured:** the 5 marketing-render image files (+ 1 `miniUrl`
  cover) at `api/ext/file/...` URLs — only their URLs/filenames/dates are in
  the captured JSON/HTML (see LEG 4 above). Low priority: the filenames
  themselves are already the evidentiary signal. If wanted, a small
  additive capture step can be added to `eisghs_mariupol.py` for the user to
  run from the VPS.
- ⚠ **RnV permit PDF has no extractable text layer** (scanned image) — OCR
  (tesseract) is not in the current toolchain, so any text on the permit
  beyond the structured `rnvDTO` fields (number/date, both already captured)
  is currently unrecoverable.

---

## Pattern replication: three more confirmed instances (2026-07-05)

Reconciling the full denis-pushilin.ru land-grant archive
(`data/parsed/dnr_land_orders.jsonl`, `scripts/252`/`253`; see
`docs/legal_mechanisms_review.md`) surfaced three more properties where the
same demolish→no-tender-regrant pattern is independently confirmed on the
spine — each carries a recorded `demolition` event AND a subsequent
`reallocation` event to a freshly-invoked developer SPV, the same LEG 1–3
shape documented above for Nakhimova 82:

| Property | DB id | Demolished | Regranted (decree) | Beneficiary |
|---|---|---|---|---|
| просп. Ленина, 89 | 4488 | 2022-12-12 | 2025-11-10 (№399) | СЗ «Главный перекрёсток» |
| просп. Ленина, 87А | 4486 | 2022-12-12 | 2025-11-10 (№398) | СЗ «Главный перекрёсток» (same beneficiary, adjacent parcel — likely one combined development spanning both footprints) |
| просп. Лунина, 25 | 5807 | 2022-08-31 | 2025-07-29 (№258) | СЗ «Садовое КОЛЬЦО «Проспект»» — project «Дом у моря» |

This confirms the modality is a **repeating occupation practice, not a
one-off**: Nakhimova 82 remains the reference exhibit because it alone has
the full five-leg lifecycle (renamed street address, new cadastral number,
marketing renders, sales data) captured end-to-end. These three are
currently attested only at LEG 1–3 depth (demolition record + no-tender
land-grant decree naming the beneficiary) — **not yet verified**:

- Whether any of the three received a *new street address* on the same
  footprint (Nakhimova 82's defining "address-laundering" feature) — the
  land-grant decrees for пр. Ленина 89/87А and пр. Лунина 25 use the
  **original** street address, unlike Nakhimova 82 → Chernomorsky 1B, so
  address-laundering specifically is unconfirmed here; the underlying
  demolish→regrant pattern still holds without it.
- New-build construction/sales status (no ЕИСЖС/nash.dom.rf match attempted
  yet for these three addresses).
- No resale, marketing, or resident-testimony evidence gathered.

**Follow-up:** cross-check пр. Ленина 89/87А and пр. Лунина 25 against
`eisghs_mariupol_objects.jsonl` for a matching new-build object (the same
approach that surfaced Nakhimova 82's nash.dom.rf record); if a match
exists, extend LEG 4–5 documentation the same way this case study does.
