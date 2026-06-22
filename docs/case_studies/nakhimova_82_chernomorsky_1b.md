# Case Study — пр. Нахимова 82 → пер. Черноморский 1Б

**The complete demolish→rebuild→resell lifecycle of a single Mariupol building,
documented end-to-end from the Russian occupation's own records.**

A privatized 36-apartment residential building is destroyed in the 2022 siege,
formally demolished by occupation decree, its cleared land handed to a developer
without auction, and a new 51-apartment building raised on the same footprint
under a *new street address and new cadastral number* — then sold, 94% of it, to
the occupier's own population on subsidized mortgages. The displaced owners get
nothing, because on paper "такого адреса физически не существует" (no such
address physically exists).

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
| Occupation address | проспект Нахимова, 82 | пер. Черноморский, 1Б |
| District | Приморский (Primorsky) | Жовтневый / Primorsky border |
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
- **What it was:** a 4-storey multi-apartment residential building (МКЖД, жилое),
  **36 apartments**, 3 entrances, privately owned/privatized.
- **Source:** Russian federal damage/reconstruction tracker, building record —
  `property_type=жилое`, `building_class=МКЖД`, `floors=4`, `apartments=36`.
- **Artifact:** `Russian_damage_assessment.xlsx` · SHA-256 `0bd1edf7…d9d7c7`
  · captured 2026-06-09.

### 2 — DAMAGED (during the siege)
- **What happened:** **100% destruction.** Burned March 2022 (HRW siege record).
  Flagged Priority Phase II in the reconstruction tracker.
- **Source:** same damage tracker — `destruction_pct=100.0`,
  `priority_phase=II`, named clean-up contractors ООО «Монотек Строй» / АО
  «ИНТЕКО», responsible executor ППК «Единый заказчик».
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
- **What happened:** razed under **Распоряжение ГКО ДНР № 56 от 29.09.2022**,
  listed as "г. Мариуполь, пр-т. Нахимова, д. 82 (Здание жилого дома)".
- **Source:** DNR MinStroy open-data demolition register (snapshot 16.03.2026).
- **Artifact:** `minstroy-dpr.gosuslugi.ru/.../reestr-snosa_16_03_2026.csv` ·
  SHA-256 `d431a530…42ea37` · captured 2026-06-09.
- **DB:** `seizure_event` 54105, stage `demolition`, date **2022-09-29**.

### 4 — REBUILT (new building, same spot, new address)
- **What rose:** **«Дом на Нахимова»** — a 5-storey, **51-apartment** building
  (2,324 m² living area), registered at the *new* postal address **пер.
  Черноморский 1Б**, new cadastral **93:37:0010410:173**, **commissioned
  29.12.2023**.
- **Land grant:** the cleared parcel was leased to the developer **without
  auction** via **Распоряжение №289 от 07.09.2023** (parcel described as
  "территория ограничена проспектом Нахимова, улицей Черноморской" — same
  cadastral 93:37:0010410:173).
- **Source:** ЕИСЖС / наш.дом.рф object **54284**, RPD 93-000002.
- **Artifact:** `наш.дом.рф/.../api/object/54284` · SHA-256 `443936eb…57b712`
  · captured 2026-06-09.
- **DB:** `seizure_event` 54173, stage `reallocation`, date **2023-12-29**.

### 5 — SOLD (apartments resold to the occupier's population)
- **What it shows:** **94.3% sold** (`sold_out_perc = 0.9434`) as of the
  2026-06-09 ЕИСЖС snapshot — overwhelmingly to Russian buyers via the federal
  2% льготная ипотека open to any Russian citizen (population-transfer
  financial channel; `memory/demand_side_architecture.md`).
- **Source / artifact:** same ЕИСЖС record 54284 (the registry carries the
  live sold-out percentage).

### Beneficiary (named, in scope for accountability — NOT minimized)
- **ООО «СЗ-1 «Порфир»»** — ИНН **9310009271**, ОГРН **1239300008870**,
  registered 11.07.2023, руководитель **Рассказов Богдан Денисович**; brand
  group **ГК ЮгСтройИнвест** (Ставрополь).
- **DB:** actor 14485, role `beneficiary`, linked to the reallocation event.
- ⚠ Source conflict to resolve before court use: director named as Рассказов
  Богдан Денисович (ЕИСЖС) vs Карпов Владимир Николаевич (other sources);
  registered address пр-кт Строителей 60 vs Черноморский 1Б — verify via EGRUL.

---

## The smoking gun

The Russian state's **own ЕИСЖС registry simultaneously proves both halves of
the laundering**:

- it names the project **«Дом на Нахимова»** — admitting the building stands on
  the **Нахимова** site;
- while assigning it the postal address **пер. Черноморский 1Б** — the address
  break that severs the identity chain to destroyed пр. Нахимова 82.

And the **cadastral 93:37:0010410:173** appears in *both* the land-allocation
order (decree №289, "ограничена проспектом Нахимова, улицей Черноморской") and
the new building's registration — a single number stitching the old footprint to
the new title.

**A second, independent federal admission.** The DNR land order isn't the only
document that names this building "Нахимова, 82" — the developer's own **RPD
(project) declaration №93-000002, filed with the federal naш.дом.рф / Минстрой
registry on 09.01.2024**, opens with the project title:

> «Многоквартирный жилой дом со встроенными помещениями по пр-ту Нахимова, 82 в
> г. Мариуполе.»

This is a *different issuing layer* (federal housing-construction oversight, not
DNR regional land administration) independently calling the Черноморский-1Б
building "Нахимова, 82" — extracted via `scripts/19_ocr_rpd_pdf.py`
(`project_title_in_pdf` field, added 2026-06-11) from the already-captured PDF
(SHA-256 `eca27d52…b4ec2`).

A third trace: the building's own marketing-render files, embedded in the ЕИСЖС
object record (`photoRenderDTO[].objRenderPhotoNm`), are named
`Нахимова_82_Top2.jpg`, `Нахимова_82_Corona_Camera0111.jpg`,
`Нахимова_82_2_Top2.jpg`, `Нахимова_82_2_Corona_Camera0093.jpg`,
`Нахимова_82_Top4.jpg` — the developer's internal asset-naming convention
preserves the old address even in files served under the new one.

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
| pre-2022 | пр. Нахимова 82: 4-storey, 36-apartment privatized МКЖД | damage tracker |
| **Mar 2022** | Destroyed in the siege — 100% destruction | damage tracker / HRW |
| **29 Sep 2022** | Demolished — Распоряжение ГКО ДНР №56 | MinStroy register |
| **07 Sep 2023** | Land leased to СЗ-1 «Порфир» w/o auction — Распоряжение №289 | DNR land order |
| **29 Dec 2023** | «Дом на Нахимова» commissioned as Черноморский 1Б, 51 apts | ЕИСЖС 54284 |
| 2024–2026 | Apartments sold — 94.3% as of Jun 2026 | ЕИСЖС 54284 |
| 27 May 2026 | ≥1 displaced household still listed for lost-access housing | distribution list |

---

## Visual-evidence collection targets

To pair the documentary chain with imagery (for the visualization and the
exhibit). Coordinates are the loaded geocodes.

- **Site coordinates:** `47.0760, 37.5125` (both old and new — same spot).
- **LEG 1 (intact pre-war):**
  - Google Street View / Yandex Panorama historical imagery at the coordinates,
    pre-2022 — capture the original 4-storey building.
  - Pre-war photos: search "проспект Нахимова 82 Мариуполь" on Yandex Images,
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
  - наш.дом.рф object 54284 — 5 marketing-render images, all dated
    14.09.2023, filenames `Нахимова_82_Top2.jpg`, `Нахимова_82_Corona_Camera0111.jpg`,
    `Нахимова_82_2_Top2.jpg`, `Нахимова_82_2_Corona_Camera0093.jpg`,
    `Нахимова_82_Top4.jpg` (URLs + filenames captured in the object detail JSON
    and SSR page; **the image bytes themselves are not yet downloaded** — see
    "Open items" below). No separate construction-progress photo set exists (the
    object shows "Сдан"/commissioned with renders only).
  - Google Earth / Yandex 2024–2025 imagery — the new building on the footprint.
  - Current Yandex Panorama at Черноморский 1Б.
- **LEG 5 (sold):**
  - наш.дом.рф / Авито / ЦИАН listings for пер. Черноморский 1Б — for-sale and
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
| 4+5 | event 54173 | ЕИСЖС api/object/54284 (detail JSON) | `443936eb…57b712` | 2026-06-09 |
| 4+5 | — | ЕИСЖС каталог-новостроек/объект/54284 (SSR page) | `57dbae9d…58fe649` | 2026-06-09 |
| 4 (2nd source) | — | RPD declaration №93-000002 PDF (project_title_in_pdf) | `eca27d52…b4ec2` | 2026-06-09 |
| 4 (РнВ permit) | — | РнВ №93-37-1-2023 PDF | `ec3cb2a6…5201b0` | 2026-06-09 |

*Reproducible from raw → DB. Occupation registrations/rulings are evidence of the
seizure act, NOT valid title; Ukraine does not recognize them, and neither do we.*

---

## Open items / completeness audit (2026-06-11)

Audited the captured naш.дом.рф data for object 54284 against the live page
(`/сервисы/каталог-новостроек/объект/54284`) for completeness:

- ✅ API detail JSON, SSR page, RPD declaration PDF, РнВ permit PDF — all
  captured (table above). The SSR page's own UI confirms "Документы
  отсутствуют" for every document category except RPD/РнВ, so no hidden
  document tabs are being missed.
- ✅ The 6 per-object sub-resource endpoints (`permits/documentation/
  infrastructure/rpd/report/other`) were probed for all 20 ЕИСЖС Mariupol
  objects during the 2026-06-09 crawl and returned no data for any of them —
  consistent with the SSR "Документы отсутствуют" indicators, not a gap.
- ⚠ **Not yet captured:** the 5 marketing-render image files (+ 1 `miniUrl`
  cover) at `api/ext/file/...` URLs — only their URLs/filenames/dates are in
  the captured JSON/HTML (see LEG 4 above). Low priority: the filenames
  themselves are already the evidentiary signal. If wanted, a small
  additive capture step can be added to `eisghs_mariupol.py` for the user to
  run from the VPS.
- ⚠ **РнВ permit PDF has no extractable text layer** (scanned image) — OCR
  (tesseract) is not in the current toolchain, so any text on the permit
  beyond the structured `rnvDTO` fields (number/date, both already captured)
  is currently unrecoverable.
