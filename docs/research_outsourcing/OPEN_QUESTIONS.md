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

### Q5. East SOS filtration / entry-ban dataset — access and format
**Question:** What exactly has East SOS (or another tracker — OHCHR HRMMU,
Media Initiative for Human Rights) published on Russian "filtration"
entry-bans for Ukrainians trying to (re-)enter occupied territory —
specifically the cited figures of ~30,000 denied entry between October 2023
and April 2025 with 20–50-year re-entry bans? We need the underlying
publication(s), not just the headline number.
**Why it matters:** progress_report_2026-06.md §5 item 14 /
`tier3_corroboration_design.md` S7. This is the evidentiary backbone of the
project's "sham process" argument — it shows the law's own "appear in person
within 30 days to keep your property" requirement is *designed* to be
impossible for a large share of displaced owners. It's systemic context (no
per-property join), but it has to be sourced properly, not just cited as a
remembered headline figure.
**What we already know:** The ~30k/20–50-year figures are already written
into `docs/reconceptualization_2026.md:85` as a recalled claim, with no
citation attached — this task exists to find and attach one, or correct the
figures if the recalled version is wrong (see RESEARCH_BRIEF.md §4 — we've
already had one recalled/paraphrased figure turn out to need correction
this session, treat this the same way until verified).
**What "done" looks like:** the actual East SOS (or equivalent) report/page
URL, publication date, exact figures as stated in the source (don't
round-trip our own paraphrase back to us), and methodology notes (how "denied
entry" and "ban length" are defined/counted). Note whether East SOS publishes
structured/tabular data (a CSV/dataset) vs. narrative-only reporting — that
determines whether this can ever become more than a citation.
**Domains likely to host the answer:** East SOS's own site, OHCHR (`ohchr.org`
HRMMU reports), Media Initiative for Human Rights, ZMINA.

---

### Q6. СЗ ГСА ДЕВЕЛОПМЕНТ — land-allocation instrument for 10 ЕИСЖС objects
**Question:** ООО «СЗ ГСА ДЕВЕЛОПМЕНТ» (ИНН 9310009539) appears as the
developer of record on 10 objects in the ЕИСЖС new-build registry, all with
only a generic "г. Мариуполь" address (no street-level address recovered).
What DNR land-grant order, decree, or auction record allocated these sites to
this developer, and does it carry street-level addresses we don't have yet?
**Why it matters:** This developer is currently a dead end in the
demolish→land-grant→rebuild chain — every *other* major Mariupol developer
in the project has a matching `dnr_land_orders` entry; this one doesn't,
which is either a genuine sourcing gap or a sign this developer is using a
different allocation mechanism worth understanding.
**What we already know:** ИНН 9310009539; 10 objects in ЕИСЖС, all
generic-address; zero matches in the project's existing `dnr_land_orders`
captures (Denis Pushilin site archive, DNR scaffolding decrees).
**What "done" looks like:** the specific decree/order/auction record (number,
date, issuing authority) that allocated land to this developer, ideally with
street addresses for the 10 sites. A confirmed "no public allocation record
exists, this developer received land through an undisclosed/non-auction
mechanism" is also a valid and useful answer.
**Domains likely to host the answer:** `denis-pushilin.ru` archives,
`glavadnr.ru`, EGRUL/EGRUL.org for the company's own filings (may disclose
land-use rights), ЕИСЖС's own developer-disclosure documents (project
declarations sometimes name the underlying site-allocation act).

---

### Q7. Перепечай Б.Н. / Дмитриев А.В. overlapping tenure — clarify the anomaly
**Question:** Перепечай Б.Н. and Дмитриев А.В. both hold the identical title
(Начальник Управления ЖКХ, Администрация городского округа Мариуполь) with
overlapping decree-signing date ranges (Перепечай 19.08–17.10.2024; Дмитриев
16.08.2024–14.05.2025). Is this a co-signing arrangement, an undisclosed
врио/acting substitution, a department reorganization (e.g. two parallel
ЖКХ units), or a dating/numbering error in the source decrees themselves?
**Why it matters:** `docs/stakeholder_network.md` flags this as an unresolved
anomaly. Two people holding the identical formal title with overlapping
authority to sign binding municipal decrees is either an administrative
irregularity worth documenting as such, or resolves cleanly into something
mundane (e.g. one official covers two adjacent administrative zones) — we
don't currently know which.
**What we already know:** Titles + date ranges extracted from decree
signature-block OCR (`scripts/195`, 2026-06-28). Краснолуцкая Т.Ю.
(Заместитель начальника, same dept.) has a date range sitting inside
Дмитриев's, consistent with normal deputization — that part is NOT the
anomaly, only the Перепечай/Дмитриев overlap is.
**What "done" looks like:** either (a) an official appointment
order/decree that clarifies the two officials' actual scopes (e.g. each
covers a different city district, or one was deputy-acting for the other
under an unlisted title), with a citable source, or (b) a confirmed "no
public clarifying record found" if genuinely unresolvable from open sources.
**Domains likely to host the answer:** `glavadnr.ru` (Кольцов/Моргун-era
appointment decrees), Mariupol administration's own staff/structure pages,
press coverage of municipal personnel changes.

---

### Q8. Распоряжение №61 — Mariupol municipal lease rulebook
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
