# Claude-app visualization prompt — Dispossession legal-mechanisms pipeline

Paste everything between the lines into a new Claude.ai conversation. It is
self-contained (all pipeline data embedded) and asks for a single-file
interactive HTML artifact: a flow diagram of the legal mechanisms of
dispossession, with the worked Нахимова-82 case threaded through it.

Source of truth: `docs/legal_mechanisms_review.md`. Keep this prompt in sync if
that doc changes.

---8<--- COPY FROM HERE ---8<---

Build a single-file, self-contained **interactive HTML artifact** (inline CSS +
vanilla JS, no libraries, no build step — must run from one saved `.html` file).
It visualizes how the Russian occupation of Mariupol legally dispossesses
residents of their property: a **pipeline flow diagram** where each stage shows
the legal instrument that enables it. Tone: sober, forensic, investigative —
dark neutral palette, strong typography, the feel of an NYT Visual
Investigations / Bellingcat explainer, NOT marketing.

## Layout

A left-to-right (wrapping to vertical on narrow screens) **flow of 6 main stages**
A→F, with **2 parallel branches** (G, H) running beneath, and a **framework bar**
spanning the top. Connect stages with arrows. Each stage is a clickable card;
clicking expands a detail panel (or opens a modal) with the full instrument list.

**Top framework bar** (spans the whole width): "ENABLING FRAMEWORK — the authority
to remake the city". Chips inside: ФКЗ №5-ФКЗ (04.10.2022, RF admission); Указ
Главы ДНР №420 (30.07.2022, master-plan); ГКО ДНР №162/205/245 (2022, demolition
procedure); **ФКЗ-4 (15.12.2025) — abolishes the court stage, registry = title**
(mark this one as a red "pivot" chip).

**Main stages (A–F):**
- **A · OWNERLESS** — "Manufacturing 'no owner'". Instrument: ГК РФ ст.225 +
  Mariupol ownerless decrees + 12,948-entry registry. DB stages:
  ownerless_designation, registry_inclusion. RD4U A3.6 · Rome 8(2)(a)(iv).
- **B · COURT TRANSFER** — "Judicial laundering of title". Instrument: ГПК РФ
  гл.33 особое производство (признание права муниципальной собственности на
  бесхозяйную вещь); 2,666 cases. DB: court_petition, court_transfer, appeal.
  RD4U A3.6 · Rome 8(2)(a)(iv). Note: superseded by ФКЗ-4 going forward.
- **C · DEMOLITION** — "Erasing the building". Instrument: ГКО №162 framework +
  Распоряжение ГКО №56 (29.09.2022) + Mariupol «О сносе» decrees + MinStroy
  register (525 Mariupol buildings). DB: demolition. RD4U A3.1/A3.2 · Rome
  8(2)(a)(iv).
- **D · LAND REALLOCATION** — "Cleared land to developers, no auction".
  Instrument: ЗК РФ no-auction КРТ + Распоряжения Главы ДНР №289/125/162-164/etc.
  to застройщик-SPVs. DB: reallocation. Rome: appropriation + named beneficiary.
- **E · REBUILD** — "New building, new address". Instrument: ЕИСЖС/наш.дом.рф
  registration (20 objects). The project-name-vs-address mismatch proves
  same-footprint identity + address break. DB: reallocation (new-build).
- **F · RESALE** — "Title to the occupier's population". Instrument: federal 2%
  subsidized mortgage open to ANY Russian citizen. DB: resale. **Rome 8(2)(b)(viii)
  — transfer of the occupier's own population** (highlight this as the gravest).

**Parallel branch G · HOUSING ALLOCATION** (beneath, feeding from C/D): служебное
жильё to officials/military/police/teachers until 01.01.2028 + маневренный фонд
(decree №493, 05.03.2026) + Mariupol distribution lists (5,822 queued / 1,889
distributed) + 25 m² compensation cap. Rome 8(2)(b)(viii) + disposal.

**Parallel branch H · TOPONYMY / ADDRESS LAUNDERING** (a thin rail running under
the whole flow): ≈75 streets / 113 objects renamed; severs the address so the
destroyed property "no longer exists" — defeats compensation. Mark it as the
connective layer that makes E's address-break possible.

## Three-tier color coding (a legend)
Color each instrument chip by its legal tier:
- **Federal** (ФКЗ, ГК/ГПК/ЗК/ЖК РФ, 2% mortgage) — one color.
- **DNR regional** (Глава ДНР, Народный Совет, Правительство, ГКО ДНР) — second color.
- **Mariupol municipal** (Глава администрации г. Мариуполя) — third color.

## Source-status badges (a second legend)
Every instrument also gets a small status badge:
- **CAPTURED** (we hold the primary text) — solid/green.
- **CITED** (named inside a captured record) — amber.
- **REPORTED** (secondary research only) — grey.
- **CRAWL GAP ▶** (to be retrieved by the region80 crawl) — dashed/red outline.
Add a toggle button: **"Highlight crawl gaps"** that dims everything except the
CRAWL-GAP and REPORTED items, so a viewer sees exactly what evidence is still
missing. (Crawl-gap items: ФКЗ-4 implementing acts, DNR ownerless procedure, DNR
КРТ land procedure, маневренный фонд/служебное жильё DNR acts, street-renaming
decrees, ГКО Распоряжение №56 federal copy.)

## Worked case overlay
Add a toggle: **"Trace a real building"** that highlights the path of пр. Нахимова
82 → пер. Черноморский 1Б through the pipeline, with the dated facts on the
relevant stages:
- C Demolition: Распоряжение ГКО ДНР №56, 29.09.2022 (100% destroyed, burned Mar 2022).
- D Land: Распоряжение №289, 07.09.2023 → ООО СЗ-1 «Порфир» (no auction).
- E Rebuild: «Дом на Нахимова» commissioned 29.12.2023 as Черноморский 1Б, 51 apts,
  cadastral 93:37:0010410:173, ~10 m from the original footprint.
- F Resale: 94.3% sold.
When active, draw the highlighted route A?→C→D→E→F and show these as captioned
callouts. (See the building's own case-study artifact for the full chain.)

## Endpoint summary panel
A compact footer table mapping each stage to RD4U category + Rome Statute article
(use the values given per stage above). Headline it: "Every rung points to a
claim."

## Polish
- Responsive; sensible print/PDF stylesheet (it should export as a clean A3/A4
  briefing page).
- Clicking a stage card expands its instrument list; a persistent legend for
  tiers + source-status; the two toggles ("Highlight crawl gaps", "Trace a real
  building") clearly placed.
- All Cyrillic must render (UTF-8). Keep every act number, date, cadastral, and
  statistic EXACTLY as given — do not invent or round. If you need a fact I did
  not supply, show a visible "[TODO]" rather than guessing.
- Small provenance footer: "Built from occupation/Russian-government records, each
  captured with a SHA-256 hash + UTC timestamp (Berkeley Protocol). These acts are
  evidence of the seizure system, not valid title; Ukraine does not recognize
  them."

---8<--- COPY TO HERE ---8<---
