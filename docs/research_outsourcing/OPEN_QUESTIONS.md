# Open Questions — ready-to-assign research tasks

Pulled from `docs/progress_report_2026-06.md`'s gap register, 2026-06-28.
Each is pre-filled per `TASK_TEMPLATE.md` — copy one section, paste it after
`RESEARCH_BRIEF.md`, send to the outsourced researcher LM. Update this file
(strike through/move to "closed") as answers come back; keep it as the single
queue so tasks aren't duplicated across sessions.

**Status note (2026-06-28):** the first outsourced batch came back as
`mariupol_urbicide_research_aggregation.md` (Rev. 2). Processed this session:
Q1/Q2/Q5/Q7/Q8 resolved → moved to Closed; Q3 and Q6 only *partially*
resolved → kept Open below with the new leads folded in. Capture of the
Russian primary instruments the report identified is staged in
`scripts/207` (user-run, geoblocked); the HRW/East SOS sources for Q5 were
captured directly in `scripts/206`.

---

## Open

### Q6. СЗ ГСА ДЕВЕЛОПМЕНТ — land-allocation instrument for 10 ЕИСЖС objects
**Question:** What DNR land-grant order allocated the Mariupol sites to
ООО «СЗ ГСА ДЕВЕЛОПМЕНТ» (ИНН 9310009539), and does it carry street-level
addresses?
**Why it matters:** This developer is the one major Mariupol developer with
no matching `dnr_land_orders` entry — either a sourcing gap or a different
allocation mechanism.
**Status — PARTIALLY RESOLVED, primary doc still missing:** The first
research batch confirmed the entity (ОГРН 1239300009530, reg. 20.07.2023,
addresses пр. Строителей 166 / ул. Энгельса 26/2; project declarations
№93-000052/053/054, Aug 2025) and surfaced a **Telegram lead**: a «Русский
Мариуполь» post says **Распоряжение Главы ДНР №297** granted СЗ
«ГСА-Девелопмент» a **12,253 m²** plot at a housing-cooperative address (full
street truncated). No capture-grade, officially-hosted land-grant document
naming this developer was found on glavadnr.ru / denis-pushilin.ru /
gisnpa-dnr.ru. The open task is to pin **Распоряжение №297** to a primary
source (number now known — search by it) and recover the site address(es).
**What "done" looks like:** Распоряжение №297's primary text (or another
official land-grant act) with the developer named and street-level site
addresses; or a confirmed "no public allocation record exists."
**Domains likely to host the answer:** `glavadnr.ru` (search Распоряжение
№297 specifically), `denis-pushilin.ru` archives, `gisnpa-dnr.ru`,
t.me/s/russkiy_mariupol (the post itself, via `?embed=1` / before-cursor
paging — the search snippet was not directly retrievable).

---

## Closed (answered, for reference — see commit history for full citations)

- ~~Q3. Постановление №2255 (22.12.2023) — per-m² rate~~ — **READ THE PRIMARY
  TEXT 2026-06-29** (`scripts/208` captured the signed PDF; OCR'd to
  `data/parsed/decree_2255_ocr.txt`, local-only) and **CORRECTED the first
  research batch's deduced figure** — same press/secondary-paraphrase trap as
  the 25 m² cap. Приложение №4, п.14 (the original, as-enacted 22.12.2023
  formula, no amendment markers in the captured text) gives:
  **Ру = 35,000 ₽/m²** for lost housing (NOT 51,500 ₽/m² — that number was
  deduced from a *later* amendment draft, not the originally-enacted rate);
  **Рп ≤ 7,000 ₽/m²** (capped) for repair of damaged housing — a new figure,
  not previously known; **Ри = 50,000 ₽/person** (partial) / **100,000
  ₽/person** (total) loss of essential property — these *did* match the
  deduction. Compensable area is itself capped: 33 m² (single
  person)/42 m² (family of 2)/+18 m² per additional member, never exceeding
  the lost unit's actual area. See `docs/progress_report_2026-06.md` §5
  item 10-adjacent note for the full citation.
- ~~Q1. Original 2% subsidized-mortgage launch decree~~ — **Постановление
  Правительства РФ от 31.12.2022 № 2565** (ДОМ.РФ subsidy rules; founding
  instrument of the 2% program for DNR/LNR/Zaporizhzhia/Kherson, later
  amended by №1123/08.07.2023 and №2166/15.12.2023). pravo.gov.ru
  publication `0001202301030011` (pub. 03.01.2023, matches press timing).
  Capture staged in `scripts/207` (user-run). Closes the launch-decree
  sub-gap left open by `scripts/197`.
- ~~Q2. Постановление №2501 (29.12.2022) — property demarcation~~ —
  identified + scope explained: federal/municipal demarcation framework for
  the occupied regions; housing routes to federal ownership via **Приложение
  №2 item 9** ("Жилищный фонд...") — the assignable-by-Росимущество class
  (Arts 6¹/7/19), in force to 01.01.2027. pravo.gov.ru `0001202212300029`.
  Capture staged in `scripts/207`; read the annex + articles after capture.
- ~~Q5. East SOS / filtration entry-ban dataset~~ — **CORRECTED an
  attribution error** in the project's own docs: the 30,000-denied-entry /
  20–50-yr-ban figure is **Russian authorities' own reporting** (a
  self-incrimination figure), quoted by HRW — NOT an East SOS dataset; East
  SOS is the source of the separate **1-in-4** filtration ratio. Source:
  HRW, "Ukraine: Russia Illegally Seizing Property in Occupied Areas"
  (26 May 2026) — captured `scripts/206`; it independently describes this
  project's exact seizure lifecycle, reports reviewing ~8,000 such court
  cases, and cites the UN's >38,000 "potentially abandoned" properties
  figure. East SOS's Oct-2023 appeal is narrative context only (no dataset).
  `reconceptualization_2026.md:85` fixed accordingly.
- ~~Q7. Перепечай Б.Н. / Дмитриев А.В. overlapping tenure~~ — resolved as an
  **OCR title-normalization artifact, not a real overlap**: the two hold
  *distinct* offices — Дмитриев А.В. = Начальник управления ЖКХ (head of
  UZhKH, ИНН 9310011880, since 08.01.2024); Перепечай Б.Н. = заместитель
  главы / сити-менеджера city administration with the ЖКХ portfolio (signed
  e.g. постановление №135). Hierarchical, concurrent — collapsing both
  signature-block phrasings to one generic title produced the apparent
  same-title overlap. `stakeholder_network.md` anomaly explained.
- ~~Q8. Распоряжение №61 — Mariupol municipal lease rulebook~~ — working HTML
  mirror found (full text of both the Временный порядок передачи в аренду and
  the Временная методика расчёта арендной платы), reg. №5351 (14.11.2022),
  on the npa.dnronline.su article route (the PDF route was the dead link).
  Capture staged in `scripts/207` (user-run). Resolves the §5 item 12 dead
  link.
- ~~25 m² compensation cap source~~ — Закон ДНР №269-РЗ (03.04.2026), full
  text captured + read; corrects a press mischaracterization (it caps the
  replacement unit's *excess* over the lost unit's area, not total
  compensation). See `docs/progress_report_2026-06.md` §5 item 10.
- ~~Служебное-жилье deadline for seized housing~~ — confirmed 1 January 2028,
  Закон №269-РЗ Статья 4 п.2.
- ~~ej.sudrf.ru full-text discovery~~ — settled negative, authenticated
  personal-account system, no public full-text search. §5 item 9.
- ~~9 absorbed-jurisdiction towns' bezkhoz cases~~ — settled negative,
  full-population scan, zero real hits. §5 item 0.
