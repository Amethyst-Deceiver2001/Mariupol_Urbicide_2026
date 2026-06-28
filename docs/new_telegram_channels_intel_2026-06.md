# Four new Telegram channels — intel review (June 2026)

*Analysis date: 2026-06-27. Capture: `scripts/174` (2026-06-26/27). Deep-intel
pass: `scripts/177` (pure local analysis over the forensic store, no network).
Parsed output: `data/parsed/new_channels_intel_{records.jsonl,summary.json}`.
Raw rulings/posts: `data/raw/<sha>.html|json`.*

Four channels were captured to follow up the top-cited URLs surfaced in the
`@mrpl_besxozxata` deep-intel pass (`scripts/171`,
`memory/mrpl_besxozxata_deep_intel_2026-06-26.md`): one apparent official
ministry channel and three resident legal-advice channels. The official channel
turned out to be a **genuine primary source**; the three advice channels are
**demand-side corroboration** of the seizure regime documented elsewhere in this
project.

| Channel | Role | Msgs / text | What it is |
|---|---|---|---|
| **@mizodnr** | **OFFICIAL primary source** | 1,632 / 851 | Channel of **МИЗО ДНР** — Министерство имущественных и земельных отношений ДНР (Ministry of Property & Land Relations). The ministry that administers the ownerless/registration regime, in its own voice: weekly «Итоги работы министерства», #вопрос_ответ procedure explainers, signed "МИЗО ДНР". |
| @donurcenter | legal-advice (commentary) | 40,140 / 38,911 | City-wide resident help-desk run by «юрист Рубина Ольга». Dominated by displaced owners asking the *same* question — what to do when their home was declared *бесхоз*. |
| @yuridicheskiyeuslugiMariupolDon | legal-advice (commentary) | 17,283 / 15,303 | Mariupol/Donetsk legal-services channel; heavy court/registration/compensation Q&A. |
| @advocate_Basivskiy | legal-advice (commentary) | 430 / 356 | Small advocate channel; cites the №66-РЗ / №153 / №175 instruments this project already tracks. |

**Treatment.** @mizodnr is on the same footing as denis-pushilin.ru — a primary
source whose statements are evidence of the *act*. The three advice channels are
**commentary**: useful to map which decrees/mechanisms residents are fighting and
to corroborate the demand side, but any decree claim in them is verified against
the decree text before citing as fact (negation-blind/unreliable-classifier
caveats apply).

---

## A. @mizodnr — the ministry narrating its own seizure machinery

The ministry's channel is, in effect, an admission file. Every quotation below is
from a captured, hashed post.

### A1. Self-stated ownerless throughput and goal

> «За первые три месяца 2026 года **отдел учёта и инвентаризации бесхозяйного
> имущества департамента по реформированию собственности** поставило на учёт
> **184 бесхозяйных объекта**. Это позволит **перевести их в государственную
> собственность**…»
> — @mizodnr/1453, 2026-04-15, sha `ae677db746f71f84…`

The ministry names its own org unit (a *Department for the Reform of Property*
with a *Bookkeeping-and-Inventory-of-Ownerless-Property unit*), the Q1-2026
throughput (184 objects), and the stated objective in plain words: **transfer to
state ownership**. This is the supply-side counterpart to the court doctrine's
«передачи… в собственность государства» language
(`docs/dnr_bezkhoz_citizenship_doctrine_2026-06.md`).

A single weekly digest shows the pipeline running at volume:

> «…Направлены в Росимущество **23 декларации на объекты недвижимости** с целью
> последующей их **передачи в региональную и муниципальную собственность**… по
> постановке на учёт в качестве бесхозяйных **18 объектов** водоснабжения…
> Внесли в Реестр имущества ДНР **159 новых объектов** и обновлены данные по
> 1163 объектам…»
> — @mizodnr/1119, 2026-02-06, sha `9fd330ae19b3cc3a…`

The ministry's own public bezkhoz-notice endpoint is also on the channel:

> «Министерство имущественных и земельных отношений ДНР **сообщает о выявленных
> бесхозяйных недвижимых вещах**… Контактные данные… г. Донецк, проспект Павших
> Коммунаров, 102.»
> — @mizodnr/153, 2025-03-28, sha `090dcd8375ee9bfe…`

### A2. The citizenship-tiered registration regime, administered personally by the minister

The registration-ban chain (Указ №1103 → №145 → №1006) is already documented in
`docs/legal_mechanisms_review.md` [A]; @mizodnr adds the administering ministry's
**own confirmation** of it — previously only press-summary-sourced (ppt.ru):

> «Указом Президента РФ от 29.12.2025 № 1006 внесены изменения в особенности:
> осуществления государственной регистрации связанных с недружественными
> государствами юридических лиц… государственной регистрации прав на недвижимое
> имущество таких юридических лиц… совершения отдельных нотариальных действий.»
> — @mizodnr/1028, 2026-01-14, sha `5d2cd4ee0a359d28…` (+ explainer «карточки»/media)

The minister runs the citizenship-tiered machine personally:

> «Прямая линия министра имущественных и земельных отношений **Якова Ходоса** —
> О регистрации прав на недвижимое имущество в ДНР **гражданами недружественных
> государств**.» — @mizodnr/1236, 2026-02-26, sha `ddb62b439e68e53a…`

> «**Яков Ходос** провёл приём граждан… Обратившиеся получили разъяснения по
> **выдаче спецразрешений (для граждан недружественных стран)**, работе
> **комиссии по правоустанавливающим документам**, возможностям аренды
> госимущества…» — @mizodnr/1293, 2026-03-11, sha `543b3130a6a6a493…`

This names, from the administering side, the two bodies the seizure doctrine
relies on: the **special-permit regime** for hostile-state (Ukrainian) citizens
(the §-145 "collegial body" residents call **СРК**) and a **«комиссия по
правоустанавливающим документам»** (Title-Documents Commission) — the body that
decides whether a displaced owner's Ukrainian-era title is "legalised," the exact
choke-point weaponised in court case 33-2875/2025 (the legalisation Catch-22).
Whether the Title-Documents Commission and the СРК are the same body or two is
left open — a follow-up.

### A3. Mariupol as the cadastral pilot zone

> «**Мариуполь стал пилотной зоной** для апробации Единой цифровой платформы
> «Национальная система пространственных данных» (НСПД)… «Администрация города
> уже эксплуатирует данную платформу в закрытом режиме»… замдиректора-главный
> технолог филиала ППК «Роскадастр» по ДНР **Екатерина Колоденко**… НСПД — это
> **цифровой двойник страны**: с точными границами… и сведениями о недвижимости.»
> — @mizodnr/1224, 2026-02-24, sha `07792bee8a09cd81…`

The depopulated city is the test bed for the Roskadastr "digital twin" that
underpins the whole property-transfer programme — a notable instrumentalisation
of Mariupol's emptied-out status.

### A4. Title-recognition rule = the demand-side hinge of the ownerless track

The ministry's own #вопрос_ответ explainer states the claim-it-or-lose-it rule:

> «Что нужно знать правообладателям земельных участков, права на которые возникли
> до принятия ДНР в состав РФ… Такие документы **необходимо представить для
> государственной регистрации прав**…» — @mizodnr/138, 2025-03-07

This is the affirmative-assertion requirement (Указ №73 §13 / Пост. ГКО №153)
that, unmet by a displaced owner, feeds the [A] ownerless track — stated by the
ministry as routine guidance.

### Named occupation officials (in scope for accountability — not minimised, CLAUDE.md)

| Name | Office | Source |
|---|---|---|
| **Яков Ходос** | Министр имущественных и земельных отношений ДНР (administers spec-permits for hostile-state citizens + Title-Documents Commission) | /1236, /1293 |
| **Александр Дудник** | и.о. Министра имущественных и земельных отношений ДНР (March 2025) | /100 |
| **Инна Мартыненко** | Первый заместитель министра (муниципальное имущество, land transfers; Докучаевск curator) | /1051 |
| **Екатерина Колоденко** | замдиректора-главный технолог филиала ППК «Роскадастр» по ДНР (НСПД Mariupol pilot) | /1224 |

Org units named: **департамент по реформированию собственности** → **отдел учёта
и инвентаризации бесхозяйного имущества**; **комиссия по правоустанавливающим
документам**. Candidate additions to `docs/stakeholder_network.md` (Tier 2).

---

## B. @donurcenter / advice channels — the demand-side mirror of the doctrine

The court doctrine (supply side) holds that a displaced Ukrainian owner is deemed
to have abandoned the home **unless** they actively assert the claim through
Russian/occupation channels (`docs/dnr_bezkhoz_citizenship_doctrine_2026-06.md`).
@donurcenter is that same fact pattern from below — hundreds of displaced owners
scrambling to perform exactly that assertion. The single most-requested item on
the 40k-message channel is one document:

> «Алгоритм действий **собственника и его представителя, если объект попал в
> бесхоз**» — посменная памятка + **образец доверенности для консульства РФ на
> управление недвижимым имуществом.» — @donurcenter/100274, 2025-01-21

Representative resident asks (one day's sample, Jan 2025):

- «образец доверенности (**от гражданина Украины на гражданина РФ**) на дом и
  земельные паи. Дом попал в бесхоз. Мы записались на приём в Консульство…»
  (/100255)
- «генеральн[ая] доверенност[ь] гр. с укр.паспорта на гр. с российским паспортом
  **для снятия квартиры с бесхоза**…» (/100370)
- «доверенность… гр. Украины на гр. РФ можно оформить **в Европе**?… **Снять с
  бесхоза может доверенное лицо?**» (/100372)

This corroborates, from the victims' side, every load-bearing element of the
doctrine and the registration-ban chain:
1. the **two-tier citizenship rule** — owners understand they cannot act as
   Ukrainian citizens and must route through an **RF-citizen proxy or the RF
   consulate**;
2. the **POA mechanism** as the survival route (and Указ №1006's targeting of it);
3. that the trigger is the home being **declared «бесхоз»** — i.e. the ownerless
   designation, not any sale or transaction.

### Instruments residents are actually fighting (advice-channel citation frequency)

Treated as **commentary** (verify against decree text before citing):

- **Постановление №61-1 (07.08.2023, red. №127-3 22.12.2024)** — most-cited in
  @donurcenter; the municipal property-disposal/rent rulebook context.
- **Распоряжение №619 (12.10.2023)** — citywide inventory order, 11 hits in
  @yuridicheskiyeuslugiMariupolDon (already [A]-tracked).
- **Указ №73, Закон №5-ФКЗ, Указ №116, Закон №66-РЗ** — the transition-property
  and ownerless framework, recurring across all three channels.
- Heavy **doverennost / power-of-attorney** discussion (724 hits in
  @yuridicheskiyeuslugiMariupolDon alone) — the POA survival mechanism №1006 bans.

Escalation/appeal endpoints residents are pointed to (candidate follow-up
sources): `ombudsmanrf.org/appeal`, `sledcom.ru/reception`, `glavadnr.ru`,
`minstroyrf.gov.ru`, `vsrf.ru` cassation, and notary chambers (`notariat.ru`).

---

## Provenance anchors (SHA-256 of captured @mizodnr posts)

| Post | sha256 (prefix) | Fact |
|---|---|---|
| /1453 | `ae677db746f71f84` | 184 bezkhoz objects → state ownership, Q1 2026 |
| /1119 | `9fd330ae19b3cc3a` | 23 real-estate declarations to Rosimushchestvo in one week |
| /1028 | `5d2cd4ee0a359d28` | Указ №1006 (29.12.2025) — ministry confirmation |
| /1236 | `ddb62b439e68e53a` | Minister Ходос direct-line on hostile-state-citizen registration |
| /1293 | `543b3130a6a6a493` | Ходос reception: spec-permits + Title-Documents Commission |
| /1224 | `07792bee8a09cd81` | Mariupol = НСПД cadastral pilot zone |
| /153  | `090dcd8375ee9bfe` | Ministry public ownerless-property notice endpoint |

## Caveats

- @mizodnr is DNR-wide; most posts are routine land-policy/agriculture. The
  ownerless/registration material is a minority but is the ministry stating its
  own throughput and goals — high evidentiary value precisely because it is the
  administering body, unguarded.
- The advice channels are commentary, not authority; resident understandings of
  decrees are not always exact, and are used here only to evidence the *demand
  side* (who is being burdened, and how they understand the regime), never as a
  source on what a decree says.
- Full reproduction from `data/raw/` via `scripts/177`.
