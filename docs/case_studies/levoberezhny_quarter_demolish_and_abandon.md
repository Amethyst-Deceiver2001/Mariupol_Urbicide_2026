# Case Study — Levoberezhny quarter: demolished, never rebuilt

**Accession:** MUP-CS-012 · Modality TBD (see [REGISTRY.md](REGISTRY.md)) ·
working research log — not yet an exhibit.

## Overview

A city block on the left bank (Левобережный район), bounded by
ул. Азовстальская (north) / бульвар 50 лет Октября (called "Меотиды" on this
stretch — dual street-name alias confirmed 2026-07-21 via cadastral map;
east side) / бульвар Комсомольский (called "Морской" colloquially — confirmed
by geocoding both names onto the same coordinate range; south side) /
ул. Ломизова (west side).
Identified 2026-07-21 as a demolish-and-abandon candidate: user-confirmed
via satellite image pairs (pre-war populated block vs. current fully razed
and undeveloped) and cadastral map cross-check.

**Boundary method corrected 2026-07-23** (`scripts/417`): the roster is now
built from the actual OSM street-centerline intersections of the four
boundary streets (a real quadrilateral, not a padded bounding box) — built
after a user-supplied cadastral parcel map showed the block's true extent
and prompted a re-check. This **excludes** several buildings a looser
bounding-box pass (`scripts/416`, retired) had let in: the Меотиды/50 лет
Октября run from ~24 upward and Комсомольский 40/1–44 turn out to sit on
the far side of Азовстальская / east of Меотиды, in adjacent blocks along
the same long streets — including **Комсомольский 42**, which had been
this case study's flagship double-dispossession example (кв.13, Петрова
Наталья) but does not sit inside the confirmed polygon and needs
re-examination as an *adjacent*, not *this*, block's finding before
further use. **Correction, 2026-07-23**: this section previously claimed
zero non-residential structures fall inside the polygon (single Overpass
sweep, OSM coverage). That is now known to be wrong — user-supplied video
stills plus a Visicom cross-check confirm at least two small non-
residential structures genuinely inside the block, attached to/behind
Комсомольский 16: a ground-floor commercial strip (grocery store plus
several other small shops, e.g. "Балаковские колбасы" sausage-shop
signage visible) at "18", and a smaller single-storey non-residential
outbuilding at "18а" directly behind it. **A separate, later correction
also found a genuine civic building**: Ломизова 7, previously assumed
residential and included in the 52-building roster, is actually Детский
сад №91 (Kindergarten №91) — see the school/kindergarten discussion below
for the full finding. OSM's own coverage evidently missed all of these,
which is why the original Overpass sweep came back empty. The broader
claim (this quarter being purely Soviet worker housing, no *major* civic
buildings) still holds; "zero non-residential structures at all" does
not, and the roster's residential building count should be read as an
upper bound, not an exact count.

Formal demolition order: **Распоряжение ГКО ДНР №54 от 29.09.2022**. This
citation was previously unsourced (no captured decree text, no URL) —
**resolved 2026-07-22** via the already-loaded MinStroy demolition register
(`data/parsed/minstroy_demolition_register.jsonl`, csv sha256
`d431a53003e51456c4052a805e1cc6c42e9417b315314df7e4b23ca40742ea37`), which
lists every address the order covers: full odd-numbered ул. Ломизова 3–19,
even-numbered бульвар 50 лет Октября 4–22, бульвар Комсомольский 2–38/2,
and odd-numbered ул. Азовстальская 7–33 (54 addresses total, all within
the confirmed polygon). A handful of addresses inside the polygon
(Азовстальская 24, 50 лет Октября 11/26/28) have no demolition-register
row under any decree — register coverage is visibly incomplete elsewhere
too (it also omits 50 лет Октября 9, independently chat-confirmed
demolished), so this is a genuine open gap, not evidence against those
buildings' inclusion.

Currently the **most casualty-dense single quarter documented in this
project**: 52 buildings inside the confirmed polygon carry a loaded
`civilian_casualty` corroboration record (101 confirmed dead + 63 listed
missing/без вести, from the mariupoldestruction.com TSV cross-reference —
`scripts/407-409`), plus first-hand resident-chat testimony (below) that
both corroborates and extends that tally. (These totals dropped from an
earlier, looser bounding-box count once Комсомольский 42 and the other
out-of-polygon buildings above were excluded — see the boundary-method
note above.)

**Confirmed: zero new-build overlap.** Checked via the project's dedicated
`developer_new_build_perimeter_candidate`/`same_block`/`same_address`
matching AND a raw ≤300m geometric proximity check against all 81 geocoded
ЕИСЖС newbuild objects — zero rows touch any of the 52 quarter properties.
This is the one documented quarter that breaks the demolish→rebuild→resell
pattern (M1/M3) seen elsewhere in this project (Lenina 104-110, Metallurgov
47/83) — here it's demolish-and-abandon, not demolish-and-launder.

## Primary-source cross-checks already run

- **AGO compensation "lost dwelling" list**: 44 of 52 buildings on the
  occupier's own compensation-housing distribution roster (Пост. №175 /
  Решение №61-1 / Закон №141-РЗ), 580 apartment-level claims total. Heaviest:
  Ломизова 15 (26 apartments), Ломизова 5 (21), 50 лет Октября 12 (21).
- **Double-dispossession cross-match** (apartment independently on both the
  compensation list and tied to a named casualty at the same address):
  50 лет Октября (Меотиды) 8 кв.65 (Соколова Елена, Фоменко Игорь
  Алексеевич, Фоменко Тамара Ивановна, all missing — likely one family) is
  confirmed inside the polygon. A second previously-cited example,
  Комсомольский (Морской) 42 кв.13 (Петрова Наталья, missing), turned out
  2026-07-23 to sit **outside** the confirmed block boundary (see the
  boundary-method note above) — still a real finding, just for an adjacent
  block, and not usable as this case study's example until re-verified
  there.
  One false-positive caught and discarded (Коваленко Валентина Ивановна —
  apartment number came from a *different* address field than the street
  match; cross-field contamination in the automated extraction, not a real
  match).
- **Master grave-site list** (project's independent 3-source citywide
  reconciliation, `scripts/300-308`, built 2026-07-20 from
  mariupoldestruction.com + full mariupolRIP channel scan + memorial.ua):
  13 quarter properties present, zero names not already in the TSV extract
  — confirms completeness for this quarter, not a source of new leads.

## Resident-chat testimony (mined 2026-07-21)

Two of the project's already deep-mined 28-building Telegram corpus chats
sit directly inside this quarter, plus one bordering address:

- **@Azovstalskaya31** (pid 6249/6259 area, ул. Азовстальская 31) — 1,774
  messages
- **Komsomolskiy20 chat**, `t.me/invite_ZPLyCLn2RItmNWMy` (pid 10714,
  бульвар Комсомольский/Морской 20 — the single heaviest-casualty building
  in the loaded tally, 11 dead + 3 missing) — 1,353 messages
- **Meotidy 15/20 chat**, `t.me/invite_QaRRTdUZFw0OTU6` — 592 messages
  (borderline-quarter address, just outside the confirmed geocoded box —
  not yet resolved as in/out)

### New/partial casualty leads from Komsomolskiy20 (not yet in the loaded tally)

Direct MChS body-recovery report from a resident, with building-level
counts matching the loaded tally:

> «Сейчас разговаривала с мчс, сказали достали тела с 28 и 20 дома, в 26
> еще не добрались до подвалов» — [t.me/invite_ZPLyCLn2RItmNWMy/3327](https://t.me/invite_ZPLyCLn2RItmNWMy/3327) (2022-03-27)

> «20 сегодня разобрали, достали 6 тел, трое остались так же возле дома» —
> [t.me/invite_ZPLyCLn2RItmNWMy/3350](https://t.me/invite_ZPLyCLn2RItmNWMy/3350)

4 named/partial victims named in the basement of building 20, not yet loaded:

| Name | Detail | Source |
|---|---|---|
| Олег | кв. 3 | [t.me/invite_ZPLyCLn2RItmNWMy/3591](https://t.me/invite_ZPLyCLn2RItmNWMy/3591) |
| Оксана | кв. 27 | same |
| Николай | кв. 27 | same |
| Аня | 9 years old, daughter of "Яна" (possibly, unconfirmed, Вакуленко Яна — already loaded at a different address, Меотиды 8) | same |

Missing-persons posts, not yet in the tally:

| Name | Detail | Source |
|---|---|---|
| Хилобок Валентина Васильевна (1952) | Морской 20 кв.29 — confirmed *not* among the basement dead per a resident reply | [t.me/invite_ZPLyCLn2RItmNWMy/3590](https://t.me/invite_ZPLyCLn2RItmNWMy/3590) |
| Бородулина Вероника Владимировна (1996) + mother Бородулина Екатерина Евгеньевна (1970) | Морской бульвар 20 | [t.me/invite_ZPLyCLn2RItmNWMy/525](https://t.me/invite_ZPLyCLn2RItmNWMy/525) |
| Unnamed woman | Морской бульвар 10 — body lay 40 days before being wrapped in a carpet, no further disposition known | [t.me/invite_ZPLyCLn2RItmNWMy/4841](https://t.me/invite_ZPLyCLn2RItmNWMy/4841) |
| "Artem" + brother + grandmother (Устинова Раиса's family) | Displaced into this building's shared basement from a burned building on Воинов-Освободителей; died under the rubble here — not original residents of this quarter | [t.me/invite_ZPLyCLn2RItmNWMy/713](https://t.me/invite_ZPLyCLn2RItmNWMy/713), [/716](https://t.me/invite_ZPLyCLn2RItmNWMy/716) |

### Demolition timeline (precisely dated, Azovstalskaya31 chat)

- 2022-05-12: "дом восстановлению не подлежит" (building declared unrestorable) — [t.me/Azovstalskaya31/3031](https://t.me/Azovstalskaya31/3031)
- 2022-05-27: first demolition rumors circulate — [.../3277](https://t.me/Azovstalskaya31/3277); resident confirms *"Наши дома от Ломизова до [Морского] готовят под снос"* (our buildings from Lomizova to [Morskoy] are being prepped for demolition) — [.../3280](https://t.me/Azovstalskaya31/3280)
- 2022-06-22: only structurally dangerous buildings cleared first, others "will stand for now" — [.../3606](https://t.me/Azovstalskaya31/3606)
- 2022-10-24: Минстрой ДНР publishes the formal demolition list; Азовстальская 33 demolition begins same day, "снос района до аллейки уже начат" (demolition of the district up to the tree-lined path has begun)
- 2022-10-28: Азовстальская 31 fenced off, demolished within days — *"Дом простоял 56 лет"* (built ~1966)
- 2022-10-29: demolition proceeding corner-first, toward the stadium
- 2022-12-21: "20а уже снесли" (Комсомольский 20а already demolished) — [t.me/invite_ZPLyCLn2RItmNWMy/4844](https://t.me/invite_ZPLyCLn2RItmNWMy/4844)

Compensation entitlement mentioned by residents: **100,000 RUB "имущество"
(property/belongings) payment** for households in demolished buildings —
[t.me/invite_ZPLyCLn2RItmNWMy/4779-adjacent thread] (28.10.2022).

### Broken-promise thread

> «Мы надеемся и ждём когда на месте нашего любимого дома начнется стройка
> для всех нас» (We hope and wait for construction to begin on our beloved
> home's site, for all of us) — Komsomolskiy20 chat, 2023-04-10.

### Open question — NOT resolved, needs map review before use

> «Дом 40,42,44, активно ведут обсуждение, по их информации. 24 год
> начнётся стройка» (Houses 40/42/44 — active discussion, construction
> expected to start in '24) — Komsomolskiy20 chat, 2023-11-26,
> [t.me/invite_ZPLyCLn2RItmNWMy/5742](https://t.me/invite_ZPLyCLn2RItmNWMy/5742).

No surrounding context specifies which street. **Resolved 2026-07-23**:
whether this is 50 лет Октября 40/42/44 or Комсомольский 40/1–44, both
turn out to sit outside the confirmed block polygon (see the
boundary-method note in the Overview) — an adjacent block along the same
long streets, not this quarter. No tension with the "genuinely
undeveloped" finding after all.

## Meotidy 15/20 — boundary question resolved: NOT in the quarter

Mined the chat's `demolition`/`sealing` flags. Directly confirmed the
building **survived** while its immediate neighbors were razed:

> «Мне тоже больно на такие кадры смотреть, но немного утешаю себя тем,
> что наш дом хотя бы не снесли, как рядом, например» (Painful to see
> those images too, but small comfort that our building at least wasn't
> demolished, unlike the ones next door) — [t.me/invite_QaRRTdUZFw0OTU6/1454](https://t.me/invite_QaRRTdUZFw0OTU6/1454) (2024-02-03)

Confirms the earlier geocoded "just outside the box" exclusion was
correct, not a false negative — and adds a useful detail for the case
study: demolition in this district wasn't uniform block-clearance: some
buildings were spared, seemingly unevenly, right at the quarter's edge.
Also confirms demolition of a "50 лет Октября 13" directly from residents:
*"Сносят 13 дом по бульвару"* (2023-07-08) — note this is a real
demolition, but the geocoded 50 лет Октября 13 sits **outside** the
confirmed polygon (see boundary-method note above), so this testimony
corroborates the adjacent block, not this quarter's own tally.

This chat is otherwise a general city-wide bezkhoz/Rosreestr registry
discussion (residents checking whether their own building appears on the
municipal ownerless-property list, а `@mrplChekHomeBot` status-check bot,
the 27.12.2023 and 26.08.2024 municipal perechen announcements, the
22.03.2024 Закон ДНР on municipal-ownership recognition) — valuable
general legal-mechanism context, but not quarter-specific evidence since
the building itself sits just outside the razed block.

## Administration's own confirmation of non-redevelopment (Azovstalskaya31, `official_notice`)

The strongest evidence yet for "genuinely abandoned" — not just visual
inference from satellite imagery, but a **direct administrative response**:

> «Ответ от администрации на вопрос о сроках строительства новых домов на
> месте снесённого 2го участка. На 2023 год - не предусмотрено» (Response
> from the administration on the timeline for new construction on the site
> of the demolished "2nd plot." Not planned for 2023.) —
> [t.me/Azovstalskaya31/12112](https://t.me/Azovstalskaya31/12112) (2023-06-22)

"2й участок" (2nd plot) is not yet matched to a specific official planning
designation — worth chasing if a plot/participok numbering scheme for this
demolition zone turns up elsewhere in the corpus.

**Independent corroboration found 2026-07-22** — Wikimapia object 43255636,
"Снесённая часть 2-го участка" (Demolished part of the 2nd plot),
[wikimapia.org/#lang=en&lat=47.100162&lon=37.631221&z=16&m=w&show=/43255636/](https://wikimapia.org/#lang=en&lat=47.100162&lon=37.631221&z=16&m=w&show=/43255636/ru/%D0%A1%D0%BD%D0%B5%D1%81%D1%91%D0%BD%D0%BD%D0%B0%D1%8F-%D1%87%D0%B0%D1%81%D1%82%D1%8C-2-%D0%B3%D0%BE-%D1%83%D1%87%D0%B0%D1%81%D1%82%D0%BA%D0%B0)
(47°6'1"N 37°37'50"E, inside the quarter). Object description:

> «В 2022 году эта часть 2-го участка была разрушена. В 2023 году была
> полностью снесена, сейчас на её месте огромный пустырь.» (In 2022 this
> part of the 2nd plot was destroyed. In 2023 it was fully demolished; a
> huge vacant lot now stands in its place.)

This is a second, independent naming of "2-й участок" as the administration's
own internal designation for (part of) this demolition zone — confirms the
term wasn't a one-off colloquialism in the Azovstalskaya31 chat, but a
recognized plot label, without yet resolving which official decree or
cadastral instrument assigns it. A user comment on the object also flags
that Wikimapia keeps a dedicated **"historical layer"** ("исторический
слой") for demolished/removed structures — visible in "classic Wikimapia"
mode and reachable via search/statistics, not the default nearest-place
list. This explains why `scripts/410`'s Wikimapia sweep returned 0/48 hits
project-wide (`place.getnearest` apparently excludes this layer) — see
`osint/sources/wikimapia.py` fix note, pending a re-sweep once the API key's
rate limit resets. **Action item**: once re-swept, check the historical
layer specifically for the quarter's other ~47 buildings/plots — if
similarly documented, this becomes a second independent per-building
demolition-confirmation source alongside the resident-chat timeline.

**Second historical-layer object found, unverified** — Wikimapia id
13963999, "Азовстальская ул. 33" ([wikimapia.org/13963999/](https://wikimapia.org/#lang=en&lat=47.100381&lon=37.634461&z=16&m=w&tag=45694&show=/13963999/ru/%D0%90%D0%B7%D0%BE%D0%B2%D1%81%D1%82%D0%B0%D0%BB%D1%8C%D1%81%D0%BA%D0%B0%D1%8F-%D1%83%D0%BB-33)),
an EXACT address match on the quarter spine (pid 6260, `floors` currently
null — a genuinely useful target if this checks out). Reached via a URL
carrying `tag=45694`, likely the historical layer's category ID — see
`osint/sources/wikimapia.py`'s third lookup pass. **Not independently
verified by this project**: `place.getbyid(13963999)` was rate-limited when
checked, and the object's own page sits behind a JS-rendered bot-protection
cookie gate that plain HTTP tools (curl, WebFetch) can't clear. What's on
record here is the user's own read of the page (title + address + reported
presence of images), not our own capture — treat as an unconfirmed lead
until the API sweep resolves it or the page is reviewed directly.

**Меотиды 4 administrative processing directly confirmed** — matches the
already-loaded Бухтоярова death record at this exact address:

> «мне вчера звонили из администрации по поводу Меотиды 4 (люди уехали до
> весны), что им готов акт» (administration called yesterday about Меотиды
> 4 — people who left until spring — saying their demolition act is ready)
> — [t.me/Azovstalskaya31/10756](https://t.me/Azovstalskaya31/10756) (2022-11-30)

**Compensation-housing mechanics (Постановление №175), amended 2023-09-01:**
- Original: compensation housing only in the same district; up to +25 m²
  over the prior unit's area
- Amended (2023-09-01): housing offered in **any** district; area allowance
  cut to +9 m²
- Recipients "сразу выдали кадастровый номер. И право собственности. Но
  продавать нельзя три года" (immediately issued a cadastral number and
  ownership right, but a 3-year resale ban) — [t.me/Azovstalskaya31/12836](https://t.me/Azovstalskaya31/12836)
- Earlier claim-window rule (Постановление ГКО №181, 05.08.2022): owners of
  buildings slated for demolition had **3 months from publication of the
  demolition decision** to assert property rights, plus inheritance
  provisions — [t.me/Azovstalskaya31/8800](https://t.me/Azovstalskaya31/8800)
- 100,000 RUB "имущество" payment was per-family, not per-person, and
  **denied entirely if the family retained any other property** — even
  partially damaged — [t.me/Azovstalskaya31/10628](https://t.me/Azovstalskaya31/10628)
- A named official, "Золотов," is quoted directing residents to check
  building noticeboards and the district administration website for
  demolition announcements — [t.me/Azovstalskaya31/9210](https://t.me/Azovstalskaya31/9210)

A **2023-09-01 rumor** (unconfirmed, explicitly framed as "preliminary
info" by the resident who posted it) claimed mortgage housing might be
built on this site while displaced residents get offered units *elsewhere*
— i.e., even the one redevelopment rumor for this quarter didn't promise
residents a return. Given msg 12112 (above, same chat) says nothing was
planned as of June 2023, and the user's own recent satellite check confirms
the block is still empty now, this rumor does not appear to have
materialized — but it's worth flagging as a rumor, not asserting resolved.

## Prosecutor-office pushback thread (Komsomolskiy20, `registration`/`compensation`)

> «Вношу ясность по поводу квартир ипотеки! 1) этим всем сейчас занимается
> прокуратура, так как много жителей хотят жить на своих местах, где было
> утрачено жилье!» (Clarifying about the mortgage apartments! 1) The
> prosecutor's office is now handling this, because many residents want to
> live at their own former sites, where housing was lost!) —
> [t.me/invite_ZPLyCLn2RItmNWMy/5471](https://t.me/invite_ZPLyCLn2RItmNWMy/5471) (2023-09-06)

A resistance/pushback thread — residents petitioning to rebuild/return to
their own site rather than accept relocation, escalated to the
prosecutor's office. Same shape as the court-resistance angle already
documented in [MUP-CS-005 (Троянда-М)](troianda_m_demolition_challenge.md)
— worth a follow-up search for whether this went anywhere, or died quietly
(consistent with the block remaining empty today).

Other confirmed mechanics: **Решение №61-1 (07.08.2023)** — "О реализации
мер социальной поддержки граждан, жилые помещения которых утрачены или
повреждены" (already known from the AGO compensation-list cross-reference,
now independently confirmed via resident chat — [.../5366](https://t.me/invite_ZPLyCLn2RItmNWMy/5366)); demolition-registry inclusion **exempts residents from needing a separate damage-assessment act** — registry entry alone is grounds for the housing queue ([.../4793](https://t.me/invite_ZPLyCLn2RItmNWMy/4793), 2022-12-07).

## @mariupol_left channel findings (mined 2026-07-23)

A left-bank/Левобережный район district Telegram channel, newly captured
and scanned (`scripts/50`/`419`) against both the project's general
seizure-lifecycle term bank and a quarter-specific street-name filter (213
messages matched one of this quarter's four boundary streets). Three
findings investigated in full:

### 1. "Стадион" district land review (2024) — checked, does not currently
### contradict the zero-new-build finding

> «По району «Стадион». Здесь будет проверка законности выделения земель,
> на которых снесли дома, под ипотечное строительство.» (Regarding the
> "Стадион" district. There will be a review of the legality of allocating
> the land where houses were demolished, for mortgage-financed
> construction.) — activist Сания Денисова, relaying a Moscow/Mariupol
> prosecutor's office call — [t.me/mariupol_left/56029](https://t.me/mariupol_left/56029) (2024-08-06)

Re-ran the quarter's ЕИСЖС new-build proximity check against the full
current object list (91 objects, `data/parsed/eisghs_mariupol_objects.jsonl`,
captured 2026-06-16 — nearly 2 years after this message): nearest object is
879m away, outside the confirmed polygon. Nothing has registered nearby in
the ~22 months since this land-allocation review was announced, which is
long enough that a completed allocation would very likely already show up
in the registry (other DNR land grants in this dataset typically reach
ЕИСЖС registration within 1-2 years). **Does not currently contradict** the
"zero new-build overlap" finding — but the ЕИСЖС capture itself is already
a month stale as of this review, and the review's own outcome (did the
allocation proceed, was it blocked?) is not confirmed either way. Worth a
standing watch item, not a resolved question.

### 2. New magistral highway through the quarter's SE corner — confirmed,
### explains "genuinely undeveloped" without contradicting it

> «Новая магистраль будет начинаться от пересечения бул. 50 лет Октября с
> Комсомольским бул. в Орджоникидзевском районе, пройдет по территории
> комбината МК «Азовсталь»... В процессе реализации проекта предусмотрено:
> реконструкция Комсомольского бул., бул. 50 лет Октября, ул. Гавань
> Шмидта, ул. Котовского, ул. Итальянской, **ул. Ломизова**... Так же под
> снос попадает стадион «Азовсталь»» (The new highway will start at the
> intersection of 50 let Oktyabrya boulevard and Komsomolsky boulevard...
> passing through the former Azovstal combine territory... The project
> includes reconstruction of Komsomolsky boulevard, 50 let Oktyabrya
> boulevard, Gavan Shmidta street, Kotovskogo street, Italyanskaya street,
> **Lomizova street**... The Azovstal stadium is also being demolished) —
> [t.me/mariupol_left/62424](https://t.me/mariupol_left/62424) (2025-09-05),
> citing Приказ №186-од, Минстрой ДНР, 14.08.2025.

**All four of this quarter's boundary streets are named** in this project
(Ломизова explicitly; Комсомольский and 50 лет Октября at the interchange
itself; Азовстальская by territorial proximity to the MK «Азовсталь» site).
The project is a 1.5km overpass/viaduct over the former Azovstal port
waters and the Kalmius river mouth, connecting Орджоникидзевский and
Приморский districts, tied to a larger "Гавань"/"Слободка" mixed-use
redevelopment master plan (visualizations: [t.me/russkiy_mariupol/10245](https://t.me/russkiy_mariupol/10245),
captured via the sender's public preview — not yet independently mirrored
into the raw store).

**Primary text captured and reviewed 2026-07-23** (`scripts/421`, page +
5 files, ~63 MB total, user-run via VPN — minstroy-dpr.gosuslugi.ru confirmed
geoblocked from Claude's own environment). Findings:

- **The decree itself** (SHA-256 `6e56ba53fac326cedae00b3a1050cfd88e1562914d78304712f862901444785c`,
  OCR'd — image-based PDF, 2 pages) is signed by **Министр В.Н. Дубовка**,
  adopted 14.08.2025, published 15.08.2025. Legal basis chain: Указ Врио
  Главы ДНР от 16.05.2023 №156 (ППТ approval procedure); Указ Главы ДНР от
  13.12.2024 №688 (Минстрой's charter); **п.4 Протокола заседания
  Оперативного штаба по восстановлению ДНР от 13.08.2025 №152**
  (a reconstruction operations-staff meeting protocol, one day before
  signature — the actual decision point); ФКЗ №5-ФКЗ от 04.10.2022 ст.23
  ч.28 п.1 (the annexation law).
- **The four ППТ/ПМТ volumes are text-layer PDFs** (SHA-256s
  `da849414…`, `02d49ef0…`, `e429ffa0…`, `4bf639a3…`) developed by
  **ФАУ «Единый научно-исследовательский и проектный институт
  пространственного планирования Российской Федерации»**, commissioned by
  the **federal** Министерство строительства и ЖКХ Российской Федерации
  (not a DNR-local body) — traced to two Russian federal government
  instruments: **распоряжение Правительства РФ от 21.04.2023 №1019-р**
  and **постановление Правительства РФ от 22.12.2023 №2255**. This
  reconstruction planning for the former MK Azovstal territory runs
  through Moscow, not just Donetsk.
- **The route text explicitly names this quarter's own SE edge as a
  construction segment**: "реконструкция магистральных улиц...
  бул. Комсомольский (**на участке от улицы Ломизова до бул. 50 лет
  Октября**)... бул. 50 лет Октября... ул. Ломизова" — the Комсомольский
  segment named is 0.74 km, literally the quarter's SE corner-to-corner
  edge; ул. Ломизова gets its own 0.06 km segment. The overpass/interchange
  (эстакада) crosses the Kalmius river mouth and MK Azovstal's port waters
  to connect to the Р-280 «Новороссия» federal highway
  (Rostov-on-Don–Mariupol–Melitopol–Simferopol).
- **§2.1.3 "Снос объектов капитального строительства"** contains a
  striking admission: *«В предоставленных данных от Федеральной службы
  государственной регистрации, кадастра и картографии (Росреестр)
  отсутствует информация о землепользователях и строениях, расположенных
  на земельных участках в границах ППТ ЛО»* — Rosreestr's own federal
  cadastre has **no landowner/structure data at all** for this territory;
  buildings needing demolition were identified purely from a 1:2000
  digital topographic plan supplied by the Mariupol city administration
  and from OpenStreetMap. This corroborates, at the reconstruction-planning
  level, this project's standing address/ownership-gap findings elsewhere
  in the spine — occupation planning bodies are working from a federal
  cadastre that itself admits it doesn't know who owned what here.
- **No itemized demolition address list found in the extractable text of
  any of the four volumes** — buildings "предлагаемые к сносу" are marked
  only graphically, on a "Схема использования территории" map (М 1:2000,
  in Vol. 2's supporting materials), with a repeated legend label rather
  than a text table. **Correction to this section's earlier claim**: a
  full-text search of all 4 volumes for "стадион" (stadium) returns **zero
  matches** — the primary decree does **not**, in extractable text, name
  the Azovstal stadium as a demolition target. That claim traces only to
  @mariupol_left/62424's own paraphrase of the decree, not to the primary
  text itself (the map image may show it graphically; not reviewed here).
  The "Стадион" district-name question is therefore **still open**, not
  resolved by this capture.
- **Related prior/adjacent planning instruments surfaced on the same map
  legend**, none yet captured: ППТ №7 covering a much larger area whose
  boundary description itself starts "ул. Ломизова, ул. Азовстальской..."
  (приказ Минстроя ДНР от 23.11.2023 №146-од — an earlier planning
  document for a zone that includes this quarter, whose red lines this
  new ППТ partially revises); ППТ ЛО №13 for a *different* route serving
  the railway-station transport hub (приказ Минстроя ДНР от 15.12.2023
  №187-од — same "ЛО 13" linear-object index, reused for an unrelated
  project); ППТ for the Металлургов/Митрополитская/Итальянская/Ковальский
  block (приказ от 26.12.2024 №317-од); a 110kV substation/power-line ППТ
  (приказ от 18.04.2025 №82-од).

Approved 2025-08-14 — **three years after** this quarter's own 2022
demolition (Распоряжение №54), so it is not the original demolition's
cause. It is, however, a plausible administrative explanation for *why the
site was never reallocated to housing* in the interim: land earmarked for
a future transport corridor/interchange is a reason to hold it empty that
doesn't require assuming neglect or oversight. Independently corroborated
by Ukrainian press (Telegraf.com.ua, 2025-09-05, framing the project within
broader redevelopment of the former steelworks site).

### 3. Азовстальская → Тульский renaming: fuller timeline, already
### primary-sourced

The channel's own posts, cross-checked against primary sources **already
in this project's raw store** (both @mariupol_nash and @morgun_ov were
mined in earlier sessions):

- **Постановление №273 (26.02.2025)**, Моргун О.В.'s own channel
  ([t.me/morgun_ov/9102](https://t.me/morgun_ov/9102), already captured,
  sha256 `713ca8b6705ac5b23fe85adbffc3daa7ff7f38aef6993eb5cf1a5c004e9db33a`):
  confirms the "Тульский проспект" name is **kept**, not reverted, framed
  explicitly as gratitude to "друзей из Тульской области" for
  reconstruction assistance, with a promise that a *different* left-bank
  street will eventually be named for Azovstal, pending "public hearings."
  States plainly: **«Отмена предыдущего постановления и принятие нового
  документа связано с адаптацией законодательства ДНР с законодательством
  РФ»** (the repeal of the previous resolution and adoption of the new one
  is due to adapting DNR legislation to RF legislation) — a direct
  administrative admission of the mechanism, not court-tested legal
  reasoning.
- **Final first-instance court rejection, 2025-08-07**
  ([t.me/mariupol_left/62038](https://t.me/mariupol_left/62038)): the
  plaintiff's own account (channel appears to be run by/affiliated with
  the plaintiffs, signed `@LeftMariupol`) — **14 total court-session
  appointments across 3 courts** (ВС ДНР had once returned the case to
  first instance for re-hearing), claim rejected in full, reasoned decision
  pending, appeal to ВС ДНР planned. **Notably: the Mariupol prosecutor's
  office reversed its own position mid-case** — having supported the
  plaintiffs' claim in earlier hearings, it asked the court to reject the
  claim in full at this final session — a documented, dated reversal worth
  its own line in the stakeholder/pressure-pattern record.

This closes out the renaming thread with a definitive endpoint (as of
2026-07-23) and upgrades it from a single court-loss mention to a fully
dated timeline with a self-incriminating administrative quote and a
suspicious prosecutorial reversal — worth folding into
`docs/legal_mechanisms_review.md`'s existing renaming entry.

## New Year 2024/25 resident video-appeal to Putin — transcribed 2026-07-23

Captured via `scripts/418` (rutube, video id `a2b592ea8c3a6b60c71c7a103fc2b804`,
uploader "Hear Mariupol", published 2024-12-31, sha256
`4420efeac24e62e2d0c191813afb8824807e45b931a34cdd99275a760d9842b6`) and
transcribed with Whisper (medium, ru; transcript sha256
`2f04e21f2dee17633f8b3f598ecf67f811054f185ab1aebbdb4dc0e66d9736d6`). Residents
of the "Стадион" district gather on their own building foundations
(«наши котлованы») on New Year's Eve to record a joint appeal to Putin.
Machine-transcribed, addresses lightly garbled by ASR (noted below) —
treat as testimony, not a verbatim court transcript.

**Direct corroboration of this quarter's own findings:**
- Independently states the district's scale as **"48 домов, два детских сада,
  школа и реабилитационный центр для детей инвалидов"** (48 buildings, two
  kindergartens, a school, and a rehabilitation center for children with
  disabilities) demolished in 2022 — the 48-building figure is close to, but
  not identical to, this case study's own confirmed 52-building residential
  roster (`scripts/417`). **The school/2-kindergartens/rehab-center claim is
  not corroborated by our own Overpass sweep**, which found zero
  non-residential structures strictly inside the confirmed polygon. Most
  plausibly, residents' lived "район Стадион" is a broader informal
  boundary than this case study's strict street-intersection polygon — not
  a contradiction, but a genuine open gap: **these 4 non-residential losses
  are not yet geolocated or cross-checked against MinStroy's register.**
- Explicit named addresses (ASR-garbled, transcript sha above; read
  literally then corrected in brackets): *"хочу... встретить своей семьёй
  дома, в Поломизово 9"* → likely **Ломизова, 9**; *"хочу вернуться в свою
  квартиру, улица Застачская, квартира 59"* → almost certainly
  **Азовстальская, кв. 59** (street name mis-heard by Whisper, "-стальская"
  truncated to "-стачская"); *"Комсомольский, 20"* transcribed cleanly.
  These three are consistent with, and add unnamed first-person voices to,
  the existing Azovstalskaya31/Komsomolskiy20/Meotidy chat testimony above.
- States the timeline precisely as **"два года и десять месяцев"** (2 years
  10 months) of self-funded rental housing since the 2022 demolition, dating
  this recording to New Year's Eve 2024→2025 — consistent with the video's
  own December 2024 publish date.
- States plainly that many residents were **denied housing-queue placement**
  because their ownership/inheritance documents burned during the fighting
  and they could not prove inheritance — a direct, first-person account of
  the same document-loss mechanism already documented via the AGO
  compensation lost-dwelling supply-side data.
- Gives residents' own interpreted motive for the Азовстальская → Тульский
  проспект renaming (§3 above): **"у нас даже украли нашу улицу
  Азовстальскую и переименовали её в проспект Тульский, чтобы лишить нас
  жилья на старом месте"** ("they even stole our Azovstalskaya street and
  renamed it Tulsky Prospekt, to deprive us of housing at the old
  address") — testimony-level evidence of residents' own understanding of
  intent, distinct from (and consistent with) the administrative
  "legislative adaptation" pretext quoted from Моргун's channel.
- States the district is being redeveloped for mortgage sale, not resident
  return: **"наш район хотят застроить ипотекой"** — consistent with the
  Стадион land-review finding (§1 above) and the project's existing
  demand-side architecture finding (mortgage channel).

**Open follow-up:** geolocate/verify the school, 2 kindergartens, and
rehabilitation center for disabled children against MinStroy's
non-residential demolition register and OSM, on a *wider* radius than the
strict quarter polygon (the residents' own "район Стадион" boundary is
evidently larger than the 4-street quadrilateral this case study documents).
**Note (2026-07-23): OSM's coverage inside even the strict polygon is now
known to be incomplete** — two small non-residential structures at
Комсомольский 18/18а (commercial, not civic) were missed entirely by the
Overpass sweep and only surfaced via user-supplied video stills (see the
Overview correction above). Any future geolocation pass for the school/
kindergartens/rehab-center should not rely on OSM/Overpass alone.

**Fully resolved, 2026-07-23**: all four non-residential losses named in
the first Putin-appeal testimony (§ above — *"два детских сада, школа и
реабилитационный центр для детей инвалидов"*, two kindergartens, a
school, and a rehabilitation center for children with disabilities) are
now individually identified with primary Wikimapia sourcing, an exact
match to that testimony's own count and composition:

1. **Детский сад №91** (kindergarten), ул. Ломизова 7 — Wikimapia object
   13000772, "Разрушенный детский сад № 91 (ул. Ломизова, 7)"; lists a
   real operating phone number (+380 629 23-21-21) and parent department
   ("Дошкольное учреждение управления образования городского совета
   № 91") — confirms a genuine operating institution, not a speculative
   match. Captured via headless-Chromium fetch, sha256
   `6be181213e7018b8094de3761bcd88c09e10505f73d0a6f88a318846bb7d3d0c`.
   **ON the roster** (`street:ломизова|7`) — was misclassified as
   `residential_spine` by `scripts/417`'s polygon sweep, which has no
   civic-use classification step; corrected in `scripts/412` via
   `NON_RESIDENTIAL_CORRECTIONS` (no longer gets the residential
   khrushchyovka fallback treatment).
2. **Детский сад №103** (kindergarten), ул. Азовстальская 19 — Wikimapia
   object 20922934, "Снесённый детский сад № 103 (Азовстальская ул., 19)",
   directly behind Школа №56. Captured sha256
   `a2e14605f8de72a689e23ce28deb687514ab47d07db84174e3f5dbc5abe148c3`.
   **ON the roster** (`street:азовстальская|19`) — one of the 12
   buildings previously counted as "unconfirmed residential"; it was
   never a residential loss and should not be chased for a floor-count
   photo. Same `scripts/417`/`scripts/412` correction as above.
3. **Школа №56** (school), Морской бул. 8 — Wikimapia object 4076989,
   "Снесённая школа № 56 (Морской бул., 8)"; opened 1967, demolished
   "after hostilities in the 2020s" per Wikimapia's own note. Captured
   sha256 `00685c5e82376f33a62f3cf723b3873414200553494a62c6775e20feb0a2d6d6`.
   **NOT on the property spine** (no pid) — its Visicom footprint polygon
   was independently confirmed live (`api.visicom.ua`, ad hoc
   single-address lookup, not geoblocked; feature_id
   `ADR3JSDC2ZCLBMHTWR`, a real complex L/T-shaped structure, geocode sha256
   `10b75607af77e98016ce8a78ab84856d0f99cccc94ad9e6b6064eba07d94a4ef`,
   footprint sha256 `58ba8ed90d7ed4d5ed56205bb3fe08003a25a4488910f0eceef4e64af1977591`),
   but adding it as a standalone spine property is a follow-up DB task,
   not done here. Note: a map screenshot label read "8а"; Wikimapia's own
   title gives the address as plain "8" — treat "8" as authoritative.
4. **Центр ранней социальной реабилитации детей-инвалидов** (Center for
   Early Social Rehabilitation of Children with Disabilities), ул.
   Азовстальская 31б — Wikimapia object 20923208, exactly matching the
   rutube testimony's "реабилитационный центр для детей инвалидов".
   Captured sha256
   `12c907899890fd07badd990abab9ced3815b9265caabc1db91cb1ac03b2d5618`.
   **NOT on the property spine** — a distinct address from the
   already-documented, on-roster Азовстальская 31 (note the "б" suffix);
   not yet added as a standalone property.

**This closes out the school/kindergarten/rehab-center gap that had been
open since the New Year Putin-appeal video was first transcribed** — the
"2 kindergartens + school + rehab center" claim is now fully sourced, not
merely testimony. The remaining discrepancy is the fourth video's "три
детских сада" (three kindergartens, vs. two here) — either an ASR/count
error in that testimony, or a third kindergarten not yet located; not
resolved. **This also lowers the quarter's true residential building
count below 52** — two roster addresses (Ломизова 7, Азовстальская 19)
were never residential losses; the casualty/compensation totals elsewhere
in this document were computed from the corroboration data, not the
roster count, so they are unaffected, but "52 buildings" should be read
as "52 addresses inside the polygon, at least 2 non-residential."

## Full Wikimapia API sweep of the quarter — 2026-07-23: complete non-residential inventory

A `function=box` query against the Wikimapia API (bbox `37.6260,47.0982,37.6345,47.1018`,
padded to cover the full quadrilateral) returned every object the platform has
mapped inside the block in a single page — `found: 47`, `count returned: 47`,
no pagination needed. Captured verbatim, sha256
`4a3a8ee608e19710b096daef76068a0439f7536268fc59b550e7cfd41777d0aa`.

Cross-referencing all 47 objects' addresses against the 52-address roster
(applying the pre-war→occupation street-rename mapping, Морской→Комсомольский
and Меотиды→50 лет Октября, since Wikimapia's historical layer uses the
pre-war names): **34 objects match existing roster addresses** — independent
confirmation, from a source we had not previously queried systematically,
that the roster's addressing is sound. The remaining objects split into three
groups:

**Group 1 — already documented above** (§ "Fully resolved, 2026-07-23"):
Детский сад №91 (Ломизова 7), Детский сад №103 (Азовстальская 19), Школа №56
(Морской бул. 8), Центр ранней социальной реабилитации (Азовстальская 31б).

**Group 2 — newly identified this sweep, individually captured via
headless-Chromium object-page fetch:**

5. **Комсомольский 18** ("Морской бул., 18" pre-war) — Wikimapia object
   20922971, "Разрушенное нежилое здание". A user comment on the object page
   names the actual tenants: **«Здесь располагался магазин и спортивный клуб
   "Юный лев"»** (a grocery store and the "Yunyi Lev" ["Young Lion"] sports
   club) — corroborates the earlier user-supplied video-still identification
   of this as commercial units, and adds the sports-club detail neither
   source had alone. Captured sha256
   `173a438a0bdd4ec952ecd9e49deac91f6e15fbda07e69b157debbb085596c15c`. Not on
   the residential roster (never had a building_id); guarded in
   `scripts/412`'s `NON_RESIDENTIAL_CORRECTIONS` against a future roster
   rebuild mistakenly tagging it residential.
6. **Азовстальская 31в** — Wikimapia object 20923224, "Орджоникидзевский
   районный центр занятости" (Ordzhonikidze district employment service
   office) — a **5th civic/institutional non-residential loss**, previously
   undocumented, distinct from the on-roster dormitory at Азовстальская 31
   (note the "в" suffix). A district-level government office, not a private
   business — relevant both to the demolish-and-abandon pattern (public
   infrastructure erased along with housing) and to accountability framing
   (occupied-territory administrative capacity destroyed, not preserved).
   Captured sha256
   `98a5c6fd0fabf1bf28265924ca0be528d78fc057a08ef69a8f62463ae860cf80`. Not
   yet added to the property spine (no pid).

**Group 3 — new *residential* leads, not yet added to the roster (open
follow-up, no floor data captured):**

7. **Азовстальская 19/1** — Wikimapia object 18434552, "Снесённый жилой дом".
   Captured sha256 `b69109c3b7c8a5068348cfd813db5a523ec85f964ef5181336796a57eb2330a6`.
8. **Азовстальская 19/2** — Wikimapia object 18434564, "Снесённый жилой дом".
   Captured sha256 `a1a1c66f6c148e2d91b7b306ba754a778123e6dba4e76f3464ded04b2edb4c6b`.

Both sit on the same lot as the plain "Азовстальская 19" address (the
kindergarten, Group 1 item 2) but are **distinct residential buildings** —
the "/1"/"/2" suffixes indicate the lot held at least 3 separate structures,
not one. Neither is on the current 52-address roster (which only has plain
"19", already reassigned to the kindergarten) — meaning the roster's true
residential count is not just "52 minus 2 non-residential" but likely
**52 minus 2 plus at least 2 newly found**, net unchanged at ~52 but with a
different composition than previously understood.

**Typology, 2026-07-23 (user identification):** both 19/1 and 19/2 are the
same 10-storey panel point-tower (точечный дом) series as the individually
photo-confirmed Азовстальская 21 — a third instance of this typology in the
quarter (alongside 21 itself), distinct from the dominant 5-storey
khrushchyovka and from Ломизова 17's rounded-corner tower. Recorded
pre-emptively in `scripts/412`'s `MANUAL_FLOOR_OVERRIDES` (keys
`street:азовстальская|19/1` / `|19/2`) so the data is ready once a proper
property-spine addition (new pid) lands — no floor override takes effect
before that, since the reconstruction script only iterates the roster.
Neither building has an individual confirming photo yet; the identification
rests on the user's direct comparison to 21, not fresh visual evidence.

**Group 4 — minor structures, address-less, documented for completeness but
not chased individually** (all present in the box-query capture above, no
separate object-page fetch performed — genuinely minor, non-residential,
no bearing on the casualty/compensation analysis):

- **Разрушенная котельная** (demolished boiler house / district heating
  plant) — object 30333792, captured individually anyway (sha256
  `03c8db692cc711539589ef3e0d524c288c92eb9ac22953071ba2bcb0ae4cc46e`) since
  utility infrastructure loss is directly relevant to the "demolish and
  abandon, no reconstruction" thesis: the quarter lost not just housing but
  its own heating plant, with nothing rebuilt in its place either.
- Туалет (object 12446396), Магазин «Вкуся» (30242157), Автобусная остановка
  (24192785), Снесённые гаражи (26379011) — present in the box-query capture
  only; street furniture / a single small shop / garages, no case-study
  relevance beyond confirming the block's pre-war built environment was a
  complete residential microdistrict, not a construction site.

## Visicom footprint sweep — 2026-07-23 (`scripts/424`)

Ran the Visicom footprint sweep directly (RUN=C, non-geoblocked, keyed API —
`src/mariupol_seizures/osint/sources/visicom.py` documents this module as
Claude-runnable, not a bulk-capture-behind-VPN case): all 52 roster
addresses plus the newly identified non-residential/off-roster objects
(rehab center, employment office, Азовстальская 19/1, 19/2, Комсомольский
18, Школа №56). 58 queries, 0 outright failures — but 3 need explicit
correction before use, and one new discrepancy surfaced:

**Reliable — genuine, distinct footprint polygons confirmed:** all 52
roster buildings (each geocode response's `name` property matches the
queried house number), plus **Азовстальская 19/1** (feature
`ADR3JSDC2Z23DCHQHX`), **19/2** (`ADR3JSDC2Z23JY8HPP`), and **Комсомольский
18** (`ADR3JSDC2Z9TKTG9KY`) — all three independently confirmed as real
Polygon geometries with exactly-matching address names, corroborating the
Wikimapia-sourced identifications above.

**Discrepancy, not yet resolved**: the roster's own on-file "Азовстальская
19" address (the kindergarten, `street:азовстальская|19`) geocoded not to
plain "19" but to **"19/2а"** (feature `ADR3JSDC2Z23CHR80K`) — Visicom
appears to have no exact "19" entry and matched the nearest sub-address
instead. The lot therefore has **at least 4 sub-addresses**: 19 (as used
on our roster, likely a simplification), 19/1, 19/2, 19/2а. Which polygon
actually corresponds to the kindergarten building itself is not resolved —
flagged for a future targeted lookup, not silently assumed.

**Bad matches — geocoder false-positived on the base address, DO NOT use
as footprints for these addresses:**
- **Азовстальская 31б** (rehab center) and **Азовстальская 31в**
  (employment office) both silently resolved to plain **"31"**
  (`ADR3JSDC2Z23UPTWG2`, the already-on-roster dormitory) — the "б"/"в"
  suffixes have no distinct Visicom entry that this geocode call surfaced.
  Their footprints remain unconfirmed.
- **Школа №56** (Морской бул. 8), captured via this sweep as
  `komsomolsky_9`'s reused feature id `ADR3JSDC2Z9T0H4RHW` (named "70" in
  Visicom's own data — an unrelated address) — a clear false match. **The
  earlier, correct footprint from the 2026-07-23 ad hoc single-address
  lookup (feature `ADR3JSDC2ZCLBMHTWR`, geocode sha256
  `10b75607af77e98016ce8a78ab84856d0f99cccc94ad9e6b6064eba07d94a4ef`,
  footprint sha256
  `58ba8ed90d7ed4d5ed56205bb3fe08003a25a4488910f0eceef4e64af1977591`) stays
  authoritative for this building; today's sweep result for it must be
  disregarded.**

All 58 raw capture files (geocode + feature responses) are in the raw
store regardless of match quality, since the forensic-capture rule is
capture-before-judge — the corrections above live in this doc and in
`scripts/424`'s inline comments, not by deleting the bad captures.

## Correction, 2026-07-23: kindergarten №103 address, rehab-center address conflict, 19/1-19/2 footprint mixup, new Комсомольский 20А typology

Four corrections/additions surfaced after the Visicom sweep above, from
user local knowledge plus a WebSearch cross-check:

1. **Детский сад №103's real address is Комсомольский 9, not
   Азовстальская 19.** A WebSearch cross-check of the kindergarten's own
   name — «Аленький цветочек» (RU) / «Червоненька квіточка» (UA) — against
   3 independent contemporary business directories (little.com.ru,
   kitabi.ru, spravbiz.ru) all agree its address is **Морской бульвар, 9**
   (phone +380(629)23-77-03) — i.e. occupation-era **Комсомольский 9**, not
   Азовстальская 19. This **corrects** the earlier Wikimapia-sourced
   identification (object 20922934, "Снесённый детский сад № 103
   (Азовстальская ул., 19)"), which was evidently a bad crowd-sourced tag.
   `scripts/412`'s `NON_RESIDENTIAL_CORRECTIONS` moved accordingly: the
   kindergarten identification now sits on `boulevard:комсомольский|9`;
   `street:азовстальская|19` is marked **unresolved** — still visually
   non-khrushchyovka when reviewed, but its actual identity is now open
   again, not silently defaulted to either "kindergarten" or "residential."
2. **The rehab center's address — RESOLVED.** User identification placed
   it at **50 лет Октября / Меотиды 20А**, conflicting with the earlier
   Wikimapia-sourced address, Азовстальская 31б (object 20923208).
   Resolved via a pre-war Ukrainian local-news source, mrpl.city, whose
   raw article text gives the institution's own address as **"бульвар
   Меотиды, 20-а"** — captured forensically, SHA-256
   `cd901f2163df229e8a1bc9113c4f9b22309c858353aed3abe8da2f69608c510e`.
   `boulevard:50 лет октября|20а` in `scripts/412` now carries the
   confirmed institution ("Левобережный центр реабилитации детей-
   инвалидов" — Left Bank Center for Rehabilitation of Children with
   Disabilities); the earlier Азовстальская 31б tag is superseded — what,
   if anything, actually occupies that address is now an open question,
   not addressed here.
   - <https://mrpl.city/news/view/kak-detyam-s-invalidnostyu-poluchit-sovremennuyu-psihologicheskuyu-i-fizicheskuyu-reabilitatsiyu-v-mariupole>
3. **Морской/Комсомольский 20А is a 9-floor building with an odd/irregular
   shape** — an 8th typology candidate, user-identified, low confidence
   (no photo reviewed yet — placeholder pending visual confirmation).
   Recorded in `MANUAL_FLOOR_OVERRIDES`.
4. **The Азовстальская 19/1 Visicom footprint was mislabeled (19/2 was
   not).** User clarification: what Visicom's own data labels "19/2а"
   (feature `ADR3JSDC2Z23CHR80K`) is actually the real residential tower
   **19/1** (10-floor point-tower, matching Азовстальская 21's typology).
   What Visicom itself labels **"19/1"** (`ADR3JSDC2Z23DCHQHX`, a small
   footprint) is a **private garage** carrying the same address number as
   the residential tower — not the tower itself. **Correction to an
   over-correction**: an earlier pass here also flagged Visicom's own
   **"19/2"** label (`ADR3JSDC2Z23JY8HPP`) as a garage; a user-supplied map
   screenshot showing 19/2 correctly positioned behind 19/1, independently
   cross-matched to Wikimapia object 18434564 ("Снесённый жилой дом
   (Азовстальская ул., 19/2)") at the same position, confirms Visicom's
   "19/2" label **was never wrong** — it's the genuine tower footprint.
   Only the "19/1" label is a garage mislabel; "19/2" is reliable.
   `MANUAL_FLOOR_OVERRIDES` for `азовстальская|19/1` and `|19/2` carry
   `footprint_note` fields reflecting this final state.

**Net effect on the roster-size framing**: the "52 buildings" figure should
now be read as **52 addresses on the current roster, of which at least 2 are
confirmed non-residential (kindergartens) and at least 2 more genuine
residential losses (Азовстальская 19/1, 19/2) are known but not yet added** —
plus at least 5 additional non-residential civic/commercial losses
(Комсомольский 18, Азовстальская 31б, 31в, Школа №56, and the boiler house)
that were never on the residential roster to begin with and are documented
here rather than on the building-count spine.

## Second Putin appeal (YouTube, Jan 2025) — transcribed 2026-07-23: mayor's own quote on compensation

Captured via `scripts/420` (YouTube, video id `JsGi1qQ1C9w`, "БОМЖИ СО
СТАДИОНА ОБРАТИЛИСЬ К ПУТИНУ. МАРИУПОЛЬ. НАШИ ДНИ", uploader "Просто
Треш", published 2025-01-19, sha256
`1ad5c3a3bb45d63bf7b704d2c9899fb4fcd452367b5f347aeff816e2da8ef9dc`), Whisper-
transcribed (`data/reports/video_transcripts/1ad5c3a3bb45.txt`). A second,
independent resident group appeal, three weeks after the New Year video
above — same district, overlapping claims, one new and significant finding.

**Corroborates, with one count discrepancy:** states **"48
многоквартирных домов, три детских сада и школа"** (48 multi-apartment
buildings, **three** kindergartens, and a school) demolished before "the
start of the special operation" — the 48-building figure matches the New
Year video exactly; the non-residential count is close but not identical
(3 kindergartens + school here vs. 2 kindergartens + school + a
rehabilitation center for disabled children in the New Year video, §
above). Two independent resident accounts now agree the school/kindergarten
losses are real and multiple, but disagree on the exact count — reinforces
rather than resolves the open geolocation gap noted above.

**New finding — direct mayoral quote on the compensation mechanism:**
> «На последней встрече с нашим мэром города Олег Валерьевич сообщил, что
> компенсационное жилье строиться не будет. Нам всем выдадут бесхозные
> квартиры, но мы не хотим чужое жилье.» (At our last meeting with our
> city mayor, Oleg Valeryevich told us that compensation housing will not
> be built. We will all be issued ownerless [бесхозные] apartments
> instead, but we do not want someone else's home.)

"Олег Валерьевич" is **Моргун Олег Валерьевич**, already tracked in
`docs/stakeholder_network.md` (668 decrees attributed) and cited elsewhere
in this case study (§3, Постановление №273). This is a first-hand,
dated (implicitly pre-19.01.2025) account of the mayor **personally and
directly telling displaced residents that the "ownerless" (бесхозяйный)
registry pipeline is the substitute for compensation housing**, not a
parallel track — residents are being offered *other people's*
registry-stripped apartments in lieu of new construction, and object to
this in their own words ("мы не хотим чужое жилье"). This is the clearest
first-person testimony yet obtained of a named senior official directly
connecting the ownerless-designation mechanism to non-delivery of promised
compensation housing — worth flagging for the knowing-dispossession /
Rome Statute accountability track, not just this case study.

The appeal explicitly asks Putin to "изменить госпрограмму" (change the
federal program) to continue funding compensation-housing construction
rather than reallocating mortgage-sale units, consistent with the "Стадион"
land-review (§1) and mortgage-channel findings (New Year video, above).

## Third and fourth Putin appeals — transcribed 2026-07-23: citywide figures, land-transfer date, and a quantified undercompensation gap

Two more independent "Стадион"/left-bank resident appeals, captured via
`scripts/422` and Whisper-transcribed. These are the richest of the four —
each names specific decree numbers, dates, and figures rather than general
grievance. Read together with the two videos above, this is now a
four-video, three-uploader, eight-month (Jun 2024 → Feb 2025) testimony
series, independently converging on the same claims.

**Third video** (YouTube `c1nmNcv5FRw`, "Обращение жильцов района
'Стадион'…", uploader "Mariupol_journal", published 2025-02-28, sha256
`67e46060a078db50d717c2a4c461981b8bc7605e71b61db3a6fe9802d2c303cb`,
transcript sha256 `55c5a06ab0957973f55ab75147259d241d4d2e4e799bc20399b5e95775e991b4`):
- **Citywide figures, not just this quarter**: *"в нашем городе снесено
  362 дома и взамен построен 71 дом"* (362 buildings demolished citywide,
  only 71 rebuilt in their place, most of those not multi-storey) and
  **"нас бомжей в данный момент 18 тысяч человек"** (18,000 people
  currently homeless citywide). These are the first citywide-scale figures
  in this project's testimony record, not building/quarter-specific —
  worth cross-checking against `docs/STATS.md` and the federal damage
  tracker rather than treated as confirmed on their own.
- References a prior presidential decree ("ваш указ") ordering local
  authorities to report on housing provision by 1 April — implies at least
  one earlier, uncaptured Putin-side instrument responding to this appeal
  series; not yet identified or located.
- States compensation-housing construction was halted **without any
  formal order to stop it** — an informal, undocumented policy shift
  claimed directly by residents.
- Names two laws by number: **"закон 141"**, which residents call
  predatory (грабительский) and say was withdrawn and replaced by
  **"закон 161"**. **Both fully identified, captured, and OCR'd 2026-07-23**
  (`publication.pravo.gov.ru`, not geoblocked, fetched directly): **Закон
  ДНР от 18.12.2024 № 141-РЗ** «О поддержке граждан, жилые помещения
  которых утрачены в результате боевых действий на территории Донецкой
  Народной Республики» (sha256
  `7f436096b6c35bba4935ce034314424e002e946a4d88373ed74a8fc1b8e494b4` —
  incidentally already sitting in the raw store from an unrelated earlier
  Telegram-media capture, now cross-linked here) and its first amendment,
  **Закон ДНР от 21.02.2025 № 161-РЗ** (sha256
  `c78a3a1d18c46f9df085566a1527f1df8f00af6aee983f9acc3521172b396fad`,
  signed Д.В. Пушилин). A second, later amendment (24.10.2025, sha256
  `e729dc63e9d332eabc6ecc19d0e3f34e5fb37fc17c227b9c71cb8a4bd314e5b5`) was
  also captured but is a minor technical extension to individual houses,
  not the mechanism residents describe. **The residents' account is
  confirmed almost verbatim by the base law's own text, not just the
  amendment**: Art. 2 §4 of 141-РЗ itself states the exclusivity directly
  — *«Получение гражданами мер поддержки, предусмотренных настоящим
  Законом, лишает их права на получение иных мер социальной поддержки...
  Получение гражданами иных мер социальной поддержки... лишает их права
  на получение мер поддержки, предусмотренных настоящим Законом»*
  (receiving the housing benefit forfeits eligibility for a cash payout,
  and vice versa — the choice is mutually exclusive by law, not merely a
  practical bait-and-switch). Art. 2 §3(3) further requires signing an
  **обязательство об отчуждении** — a binding written commitment to
  transfer ownership of the destroyed dwelling *and its land parcel* to
  the municipality — as a precondition of receiving compensation housing
  at all. Eligible unit size is capped (33m² single/42m² couple/18m² per
  person in a 3+ family, +9m² max variance) regardless of the lost
  dwelling's actual size.
- Confirms the "48 buildings demolished, mortgage housing planned near the
  sea, we're being pushed out because it's valuable land" narrative
  consistent with the other three videos, with the added detail that
  Ukrainian condominium-association (ОСМД) records and privatization
  should have made this recognizably private property.

**Fourth video** (YouTube `18iOWPkcs9I`, "Жители города Мариуполь,
проживающие на Левом берегу, район Стадион", uploader "ДАША СЕРЫЙ
КАРДИНАЛ", published 2024-06-20 — the earliest of the four appeals, sha256
`3921dc70691955d137e200a962461abcd2321c1ebb681ac2e315ce375ad19771`,
transcript sha256 `143a83ec165c38c53926a8f02cb921bf13918cd53ceef9516459aa0e7f4b761d`):
- **Directly accuses the administration of demolishing all 48 buildings
  hastily instead of assessing and repairing them**: *"вместо того, чтобы
  провести оценку разрушений... администрация приняла решение под шумок
  быстро снести все 48 домов"* — residents requested copies of the
  required specialized-organization structural-damage assessment and never
  received one, despite formally requesting it from the city
  administration.
- **A specific, previously uncaptured land-transfer date**: residents
  state they requested information on third-party redevelopment rights and
  were told their land had passed into municipal ownership **as of
  11.08.2023**, with no stated legal basis given — residents explicitly
  ask what basis this happened on and call for prosecutorial involvement.
  Not yet cross-checked against any captured decree; a genuine gap.
- States their buildings were managed under ОСМД (condominium association)
  and apartments were privatized — private property under Ukrainian law,
  making the land transfer a "gross rights violation" in their own words.
- **Quantifies a specific undercompensation gap, tied to named decrees
  already in this project's dataset**: cites **Постановление 175** and
  **Постановление 61.1** as setting compensation at only **45,000
  RUB/m²**, against a stated market rate of **120,000 RUB/m²** — a ~2.7x
  gap. Both decree numbers match instruments **already documented and
  loaded** in this project via the unrelated monitored-channel scan (see
  `memory/monitored_scan_findings_2026-07-21.md`): Решение №61-1 is
  Mariupol city council's compensation-distribution procedure (adopted
  2026-02-13, the top-cited instrument in that scan, paired explicitly
  with Пост. ГКО №175's compensation norms). **This is an independent,
  first-person confirmation from residents of the exact compensation
  mechanism the project had already surfaced from an administrative-side
  channel scan** — the two sources corroborate each other from opposite
  ends (residents' testimony vs. officials' own announcement channel).
- Cites a **Постановление №135** (ASR-garbled qualifier, unclear — "по
  Баршевдару" does not parse as a real term; treat the decree number only,
  not the qualifier) dated around May 2024, under which residents were
  left homeless.
- **Directly ties the Азовстальская → Тульский renaming to loss of
  registration and clearing the way for redevelopment**: *"переименовали
  [улицу]... оставив нас без прописки, а также открыли себе дорогу под
  застрой ипотеки на действие наших снесенных домов"* — a first-person
  causal claim (not just administrative pretext) that the renaming
  mechanism was used specifically to sever residents' formal tie to the
  address and clear the site for mortgage redevelopment. Consistent with,
  and more explicit than, the New Year video's similar claim (§ above).

## Azovstalskaya31 `resident_presence` (244 messages) — mined, mostly logistics

As expected, mostly "is my building/apartment intact," evacuation
coordination, and pet/looting chatter — but 7 new missing-persons leads
surfaced, none previously captured, all still open searches (no resolution
found in the chat itself):

| Name | Address | Note |
|---|---|---|
| Акулич Инга + Невидничий Николай | Азовстальская 31, кв.42 | missing since 1 March (poster's parents) |
| Никитина Ираида Никифоровна (1952) | Азовстальская 31, кв.74 | missing |
| Будаева Надежда Александровна | Азовстальская 31, кв.77, 4 подъезд | missing, sheltered in own entrance's basement |
| Антюхова Анна + Антюхов Николай | Азовстальская 31, 2 подъезд, кв.22 | missing (grandparents, stayed behind) |
| Пархоменко Зинаида Михайловна (78) | Азовстальская 31, кв.21 (1 этаж, 2 подъезд) | missing |
| Горбач Лариса Андреевна (1946) | Азовстальская 24 | missing since 2 March |
| Гузь Валерий Леонтиевич | 50 лет Октября (Меотиды), 34, кв.17 | missing, last seen with neighbor Сугибин Игорь (кв.8) |

Two long-running search threads in this chat (Вовк Любовь Игнатьевна,
Ирина Подрезенко) are already in the loaded tally — confirmed, not new.

## Chat mining: complete

All flag categories across all three quarter-adjacent resident chats
(Azovstalskaya31, Komsomolskiy20, Meotidy 15/20) have now been reviewed:
`burial`, `demolition`, `new_build`, `registration`, `compensation`,
`ownerless_process`, `official_notice`, `sealing`, `resident_presence`.
Nothing left unmined in this source.

## domophoto.ru citywide building catalogue — 11 in-quarter matches, 4
## Soviet standard-design series codes confirmed (2026-07-24)

[domophoto.ru](https://domophoto.ru/cities/32/) (mirrors photobuildings.com)
is a Russian building-photography database with structured per-building
metadata: address, series/project code, floor count, approximate
construction date, demolished/standing status. Crawled citywide (128
streets, 809 building-detail pages, `scripts/427`, user-run per the
robots.txt caveat documented in that script's header). 71 of the 809
captured pages name one of this quarter's four streets in their title, but
— same lesson as the marik_236 AOI sweep — most are on the same boulevards
well OUTSIDE the quadrilateral (e.g. Комсомольский 40-96, Черноморская/
Черноморский as an unrelated false-positive street match). Only **11
house-number matches fall inside the actual roster**:

| Building | domophoto project code | Floors | Status |
|---|---|---|---|
| Ломизова 9, 11, 13 | **1-464Д-83** | 9 | снес (demolished) |
| Ломизова 17 | (no code, "панельные жилые дома") | 14 | снес |
| 50 лет Октября 4, 6, 8 | (no code, "панельные жилые дома") | 5 | снес |
| 50 лет Октября 20 | **1-437** | 5 | снес |
| Комсомольский 30, 36 | **1-439А-41** | 9 | снес |
| Комсомольский 34 | (no code, "панельные жилые дома") | 5 | снес |

This independently confirms, with real Soviet standard-design series codes
rather than only visual-similarity calls: Ломизова 9/11/13 as one series
(upgrading the earlier "Ломизова 11 and 13 are identical to 9" user
identification to a sourced series match), Комсомольский 30/36 as the same
**1-439А-41** family already independently confirmed at Комсомольский
38/2's own photo caption, Ломизова 17's 14-floor count (now a 3rd
independent source agreeing with the dashcam/Yandex-panorama review), and
5-floor khrushchyovka status at 50 лет Октября 4/6/8/20 and Комсомольский
34 (upgrading these from the areal-pattern fallback / group-identification
to individually domophoto-sourced). All 11 confirmed series/floor entries
folded into `scripts/412`'s `MANUAL_FLOOR_OVERRIDES`, confidence raised
from `medium` to `high` where a matching independent source landed.

The other 40/48 roster buildings are simply not in domophoto's catalogue
at all (a crowd-sourced site, not claiming full coverage) — this closes
out the "enrich design notes for a detailed reconstruction" task as far as
this source can take it, not as a complete series census.

**Bug found and fixed while verifying this update, 2026-07-24**:
`scripts/412`'s `_norm_key()` helper replaced spaces with underscores
before dict lookup, but every `MANUAL_FLOOR_OVERRIDES`/
`NON_RESIDENTIAL_CORRECTIONS` key for a multi-word street ("boulevard:50
лет октября|4") is written with a literal space — so all 11 "50 лет
Октября" override entries silently missed their lookup and fell through
to the generic low-confidence areal-pattern fallback, discarding real
sourced data, in every reconstruction-data build up to and including this
session's first rerun. Worse: the same bug broke the non-residential
lookup too, so **50 лет Октября 14 (commercial) and 20а (rehab center)
were silently assigned fake 5-storey residential khrushchyovka floor data**
instead of being correctly excluded as non-residential. Fixed by removing
the space-to-underscore substitution (no dict key anywhere in the file
actually used an underscore) and re-verified: the "50 лет Октября"
group's sourced entries now resolve correctly, and 14/20а now correctly
show `floors: null, actual_use: commercial`/`rehabilitation_center`.

## Independent editorial corroboration: ASTRA memorial report (2026-03-26) —
## 16 dead in one entrance, building not yet identified

[@astrapress/108112](https://t.me/astrapress/108112) (ASTRA, independent
exiled Russian outlet, dated 2026-03-26) — headline "Жители оккупированного
Мариуполя почтили память погибших соседей в котловане, который остался на
месте их дома" (Residents of occupied Mariupol honored the memory of
neighbors who died, in the foundation pit left where their home stood).
Reports that residents of the "Стадион" district held a memorial for **16
people who died in a single building entrance/stairwell (подъезд) in March
2022**, during the siege, filmed at the foundation pit where the building
stood; video sourced from local channels. The article itself cross-
references this project's own already-captured January 2025 Putin-appeal
video and the residents' account that the Азовстальская → «Проспект
Тульский» renaming was intended to strip their right to housing at the old
address — both already primary-sourced elsewhere in this case study,
independent editorial corroboration of testimony this project reached
first via resident-chat mining.

Captured via `scripts/432_capture_astrapress_108112_memorial_video.py`
(user-run, RUN=U): message metadata JSON + a 14.7s video (1280×720,
`osint_astrapress_msg_video`) + 2 ffmpeg stills. Stills show an overgrown
cleared building lot, distant apartment blocks on the skyline (consistent
with the quarter's terrain), and a small group tying flowers/a wreath to a
burnt tree trunk in the rubble field — no on-screen address or building
number visible in either frame.

**Building/entrance NOT identified.** Cross-checked against every already-
loaded casualty tally for this quarter (`civilian_casualty:levoberezhny_
quarter_tsv:*` + `civilian_casualty:levoberezhny_chat_leads:*`): no
building's recorded count is exactly 16. The closest candidate is
**BOULEVARD:комсомольский|20** — already the quarter's heaviest-casualty
building (11 dead/3 missing in the TSV tally + 7 dead/2 missing from the
Komsomolskiy20 chat-leads load, 18 dead total) and the one building with an
independently documented single-building MChS body-recovery report
("достали тела с 20 дома... разобрали, достали 6 тел" — see "Resident-chat
testimony" above). None of this project's records track подъезд-level
(entrance-level) granularity, so ASTRA's "16 in one entrance" could be a
subset of Комсомольский 20's total dead, or a genuinely different,
unresolved building. **Not merged into any existing tally** — flagged here
as an open corroboration lead, not a confirmed match, pending either a
building identification from the source video's full motion or an
independent address-naming source for this specific memorial event.
