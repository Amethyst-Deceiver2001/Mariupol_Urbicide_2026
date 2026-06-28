# Open Questions — ready-to-assign research tasks

Pulled from `docs/progress_report_2026-06.md`'s gap register, 2026-06-28.
Each is pre-filled per `TASK_TEMPLATE.md` — copy one section, paste it after
`RESEARCH_BRIEF.md`, send to the outsourced researcher LM. Update this file
(strike through/move to "closed") as answers come back; keep it as the single
queue so tasks aren't duplicated across sessions.

---

## Open

### Q1. Original 2% subsidized-mortgage launch decree
**Question:** What is the exact number and signing date of the Russian
federal government resolution that *launched* the 2% subsidized mortgage
program for DNR/LNR/Zaporizhzhia/Kherson residents (signed by Mishustin,
reported in press around early January 2023, following Putin's 15 December
2022 strategic-council directive)?
**Why it matters:** progress_report_2026-06.md §5 item 11. We already have
the confirmed *amendment* — Постановление Правительства РФ от 15.12.2023
№2166, verified on `publication.pravo.gov.ru/document/0001202312150019` — but
not the founding instrument it amends.
**What we already know:** Program covers ДНР/ЛНР/Запорожская/Херсонская
oblasts, 2% rate, ≤6M ₽, ≥10% down payment, Промсвязьбанк as primary
operator (alongside Сбербанк/ВТБ). Multiple press outlets (Vedomosti,
RIA Crimea, RT) confirm a resolution existed by ~3 Jan 2023 but didn't print
its number.
**What "done" looks like:** the resolution's number + date + a
`pravo.gov.ru` or `government.ru` URL to it. A confirmed negative ("genuinely
not separately published, folded into another instrument") is also useful.
**Domains likely to host the answer:** `publication.pravo.gov.ru`,
`government.ru/docs/`, `psbank.ru` (Промсвязьбанк's own program page may cite
the founding resolution by number).

---

### Q2. Постановление №2501 (29.12.2022) — federal/municipal property demarcation
**Question:** Full text (or at least full official title + scope) of
Постановление Правительства РФ от 29.12.2022 №2501, "Об утверждении
особенностей управления и распоряжения отдельными объектами имущества,
расположенными на территориях ДНР, ЛНР, Запорожской и Херсонской области..."
— specifically, under what conditions does it route bezkhoz/"ownerless"
housing into **federal** (not municipal) ownership?
**Why it matters:** Surfaced inside Закон №269-РЗ Статья 3 п.2 as the legal
basis for transferring some seized housing to federal ownership instead of
the municipality — a new, uncaptured branch of the property-transfer chain.
**What we already know:** Cited by number/date/title inside №269-РЗ's own
text (captured `scripts/197`); not yet independently verified or read in
full.
**What "done" looks like:** primary text located on `pravo.gov.ru`, the
specific clause governing housing (not just general property) quoted
verbatim.
**Domains likely to host the answer:** `publication.pravo.gov.ru`.

---

### Q3. Постановление №2255 (22.12.2023) — federal reconstruction subsidy program
**Question:** What does Приложение №4 of the federal programme "Восстановление
и социально-экономическое развитие ДНР, ЛНР, Запорожской и Херсонской
области" (approved by Постановление Правительства РФ от 22.12.2023 №2255)
set as the per-square-meter compensation rate used to calculate housing-loss
payouts?
**Why it matters:** Закон №269-РЗ Статья 7 п.3 explicitly defers the
per-m² compensation rate to this federal program's Приложение №4 — i.e. this
is the actual source of the money figure behind every monetary
compensation case in the project, not just a cross-reference.
**What we already know:** Title/number/date confirmed inside №269-РЗ's own
text (captured `scripts/197`).
**What "done" looks like:** the actual per-m² rate (or rate table/formula),
with a `pravo.gov.ru` citation to Приложение №4 specifically (the parent
resolution alone may run hundreds of pages — find the right annex).
**Domains likely to host the answer:** `publication.pravo.gov.ru`,
`government.ru`.

---

### Q4. Распоряжение №61 — Mariupol municipal lease rulebook
**Question:** Full text of Распоряжение №61 (Mariupol municipal property-lease
rulebook), currently only [CITED] (referenced inside other captured records,
never directly retrieved).
**Why it matters:** progress_report_2026-06.md §5 item 12. PDF is
dead-linked on нпа.днронлайн.
**What we already know:** Dead link confirmed at нпа.днронлайн (no working
mirror found there).
**What "done" looks like:** a working mirror URL (try
`mariupol.gosuslugi.ru`, the горуправление юстиции registry, or press/forum
reposts) OR a confirmed "no public mirror exists" negative.
**Known dead ends:** нпа.днронлайн's own copy is dead-linked — don't re-try
that exact URL, look for a different host.

---

## Closed (answered, for reference — see commit history for full citations)

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
