# Stakeholder network — actors of the Mariupol dispossession pipeline

Companion to `docs/legal_mechanisms_review.md` (which maps the *instruments*;
this doc maps the *people and organizations* operating them). Generated graph
data: `scripts/40_build_stakeholder_network.py` →
`data/parsed/stakeholder_nodes.jsonl` / `stakeholder_edges.jsonl` +
`data/reports/stakeholder_network.md` (auto-generated counts) +
`data/reports/stakeholder_network.dot` (Graphviz).

**Scope rule (CLAUDE.md):** named occupation officials, judges, and
beneficiaries acting in official/commercial capacity are in scope for
accountability and are NOT minimized. Lawful owners and private housing-list
claimants are excluded from the network entirely (aggregate counts only).

**Attribution rule:** every name below is sourced from a parsed occupation
record in this repo (decree scans, court records, land orders, the federal
damage-assessment XLSX, EGRUL extracts). Positions/titles are stated only as
they appear in the signed documents. Occupation records evidence the *act*,
never valid title.

---

## Tier 1 — Federal RF (funding, contracting, programme control)

| Actor | Role in pipeline | Evidence base |
|---|---|---|
| **ППК «Единый заказчик в сфере строительства»** | Responsible executor for **1,769 of 1,941** buildings in the Russian federal reconstruction tracker — the funding/contract gateway for rung [E] rebuild | `damage_assessment.jsonl` `responsible_executor` |
| **Shef-regions: Санкт-Петербург, Тульская обл., Московская обл.** | Patron-region capital-repair programmes in Mariupol (also: per-district allocation in the ЖКХ programme text) | `damage_assessment.jsonl` `contractor`; region80 ЖКХ programme |
| **Крост** (СПб) | Restoration contractor, **309** buildings | `damage_assessment.jsonl` |
| **ГК «ЕКС»** | Contractor, **251** buildings | 〃 |
| **ГК «Трансстройинвест»** | Contractor, **217** buildings | 〃 |
| **ООО «Монотек Строй» / АО «ИНТЕКО»** | Contractors (joint entries), **187** buildings | 〃 |
| **ПСК «Строймонолит» / АО «УК Новый Капитал»** | Contractors, **121** joint + 30/91 separate | 〃 |
| **Крокус Групп** | Contractor, **114** buildings | 〃 |
| **Спецснабтранс** | Contractor, **54** buildings | 〃 |
| **ООО «ГК КрашМаш»** (ИНН 7842525925, St. Petersburg, director Казаков Виктор Александрович) | Demolition contractor, confirmed at pr. Metallurgov 47 (Troianda-M case) via on-screen video text independent of company's own promotional material; director on record in trade press (Oct 2022 Mariupol start date, 35 specialists, 25 equipment units, unique 60m-boom Caterpillar 390DLME) | `troianda_m_demolition_challenge.md`; `scripts/169`, `scripts/180` |
| **Московский политех** | Listed as executing entity, **120** buildings | 〃 |
| **АО «ДОМ.РФ»** | Federal housing operator: 2% mortgage programme (rung [F] resale), lift-replacement financing | region80 ЖКХ programme; [REPORTED] demand-side docs |
| **ФАУ «РосКапСтрой»** (Roskapstroy) | Federal autonomous institution, Ministry of Construction; parent of RKS-NR | RKS-NR/Roskapstroy own sites, captured `scripts/170` (2026-06-26) |
| **ООО «РКС-НР»** | Founded 05.2022; general contractor for DNR/LNR repair-restoration; director Шарипов Ильдар Радикович (also paid by Moscow's Москапстрой); confirmed physical demolition contractor link via `lenina_104_106_108_110` AND `troianda_m_demolition_challenge` (paper-trail role; physical demolition at Metallurgov 47 itself attributed to KrashMash, see Tier 4) | Roskapstroy site; appellate ruling 33-2575/2025 |
| **Хуснуллин М.Ш.** (Marat Shakirzyanovich Khusnullin) — Deputy PM | Federal oversight of occupied-territory reconstruction generally; Russian business media associate Moscow's Москапстрой (which pays Sharipov) with his domain; prior Moscow construction deputy-mayor scheme per Dossier Center | Dossier Center "Мариупольский передел" (Echo FM mirror, `scripts/170`) — **candidate, not yet independently cross-checked against an official government source beyond government.ru's bio page** |

Working hypothesis to verify: contractor assignment by district follows the
shef-region split — joinable per-building via `damage_assessment.jsonl`
district keys.

**New candidates from Dossier Center "Мариупольский передел"
(2026-06-26, see [[dossier_center_mariupol_peredel]] in memory) —
not yet cross-checked against EGRUL or added to the formal actor table:**
Anton Koltsov (already tracked above as Кольцов А.В.); Evgeny Balitsky
(Zaporizhzhia occupation "governor," quoted authorizing transfer of seized
property to security forces); Dmitry Sablin (Russian MP, reported GRU
links); Roman Tesluk (named as a cryptocurrency intermediary in a
retroactive-ownership resale scheme). These are accountability-track leads
from independent journalism, not yet verified against a primary document
this project controls — treat as sourced-but-unverified pending further
research.

## Tier 2 — DNR republic (legal framework, land allocation, adjudication)

| Actor | Role in pipeline | Evidence base |
|---|---|---|
| **Пушилин Д.В.** — Глава ДНР | The apex signer: **50 of 51** captured land-reallocation распоряжения (rung [D], no-auction grants to developers); Указ №301 (renaming framework, [H]); Указ №420 (master plan); ГКО №162 (demolition framework, [C], as GKO chair) | `dnr_land_orders.jsonl` `signing_official`; scripts 13/35/37/38 captures |
| **Правительство ДНР** | Signatory authority on **219** of 395 dispossession-relevant region80 acts (КРТ rent rates, маневренный фонд/служебное жильё procedures, ЖКХ programme) | `pravo_region80_relevant.jsonl` |
| **ГКО ДНР** (dissolved 30.09.2022) | Wartime demolition framework №162/205/245 + распоряжения incl. №56 (Mariupol list — internal, unpublished) | scripts 13/38 captures; MinStroy register |
| **Минимущества (МИЗО) ДНР** | Property/land administration acts (6 region80 acts) | `pravo_region80_relevant.jsonl` |
| **Фонд государственного имущества ДНР** | State-property disposal acts (4) | 〃 |
| **Минстрой ДНР** | Demolition register keeper; construction acts (3) | `minstroy_demolition_register.jsonl` |
| **DNR courts (26 returning records) + named judges** | Rung [B]: особое-производство ownerless transfers, 8,271 relevant cases across the region (89 judges with ≥30 decided cases; Попова И.К. alone signed 401 grants); judges named per case | Postgres `actor` (role=judge, org=court), `court_case.judge` |

## Tier 3 — Mariupol municipal (operational execution)

The signing officials of the ownerless/demolition decrees — the operational
core of rung [A] and [C]. Position titles appear on decree letterheads (raw
scans in store); names below are as-signed.

| Official | Signed instruments | Counts |
|---|---|---|
| **Кольцов А.В.** | Ownerless decrees **652/968**; demolition decrees **16/20**; Постановление №493 (05.03.2026, маневренный фонд — 18 buildings → МУП «УК Жилсервис»); **врио глава МО ГО Мариуполь since 13.06.2025** (Указ Главы ДНР №493/13.06.2025 — a different instrument from Постановление №493 above despite the matching number; see chronology below) | `ownerless_decrees.jsonl`, `demolition_decrees.jsonl` |
| **Моргун О.В.** | Ownerless **156**; demolition **1**; глава администрации города Мариуполя 23.01.2023→06.11.2023, then врио главы МО ГО Мариуполь 06.11.2023→12.06.2025 (full chronology below) | 〃 |
| **Перепечай Б.Н.** | Ownerless **70** | 〃 |
| **Дмитриев А.В.** | Ownerless **55**; also demolition-commission member | 〃 |
| **Краснолуцкая Т.Ю.** | Ownerless **25** | 〃 |
| **Матейко В.А.** | Ownerless **8** | 〃 |
| **Иващенко К.В.** | Распоряжение №61 (03.11.2022) — municipal property-lease rulebook, the [A]→[D]/[F]/[G] disposal bridge; глава администрации города Мариуполя 06.04.2022→22.01.2023 (full chronology below) | script 38 target ([CAPTURED]); appointment chronology confirmed 2026-06-12 |

### Command-chain chronology — heads of Mariupol administration (script 44, OCR'd 2026-06-12)

The completed denis-pushilin.ru archive crawl (script 39) + index (script 43)
surfaced 9 Указы Главы ДНР that fully date-bracket every change of head of the
Mariupol occupation administration since its creation. All were scanned
images with no text layer; OCR'd via script 44 (`ocrmypdf --language rus
--skip-text --rotate-pages --deskew`, derived artifacts logged with
`derived_from`/`transform` per CLAUDE.md). Full chain, every appointment
personally signed by Д.В. Пушилин (as Глава or Врио Главы ДНР):

| Date | Указ | Action |
|---|---|---|
| 31.03.2022 | №108 | **Creates** «администрация города Мариуполя» as a DNR local administration, citing the pre-existing 2015 template Указ №13/19.01.2015 «Временное (типовое) положение о местных администрациях ДНР» — occupied Mariupol was slotted into a template built for occupied-territory administration within 5 weeks of the city's fall. |
| 06.04.2022 | №123 | **Appoints Иващенко К.В.** «Назначить Иващенко Константина Владимировича главой администрации города Мариуполя.» |
| 22.01.2023 | №13 (врио) | **Releases Иващенко К.В.** «Освободить Иващенко Константина Владимировича от замещаемой должности главы администрации города Мариуполя.» |
| 22.01.2023 | №14 (врио) | **Releases Моргун О.В.** from his prior post: «Освободить Моргуна Олега Валериевича от замещаемой должности главы администрации Новоазовского района Донецкой Народной Республики» — same day as №13, clearing him for transfer to Mariupol. |
| 23.01.2023 | №15 (врио) | **Appoints Моргун О.В.** «Назначить Моргуна Олега Валериевича главой администрации города Мариуполя.» |
| 06.11.2023 | №541 | **Releases Моргун О.В.** «Освободить Моргуна Олега Валериевича от замещаемой должности главы администрации города Мариуполя.» |
| 06.11.2023 | №542 | **Re-designates Моргун О.В.**, same day: «Назначить временно исполняющим полномочия главы муниципального образования городского округа Мариуполя ДНР Моргуна Олега Валериевича на срок до дня избрания главы...» — entity renamed from «администрация города» to «муниципальное образование городского округа», reflecting Mariupol's formal incorporation as a DNR municipal entity. |
| 12.06.2025 | №492 | **Releases Моргун О.В.** «Освободить Моргуна Олега Валериевича от временного исполнения полномочий главы муниципального образования городского округа Мариуполя ДНР.» |
| 13.06.2025 | №493 | **Appoints Кольцов А.В.**, next day: «Назначить временно исполняющим полномочия главы муниципального образования городского округа Мариуполя ДНР ... Кольцова Антона Викторовича на срок до дня избрания главы...» — **current as of 2026-06-12**. |

**Tenure summary:**
- **Иващенко К.В.**: 06.04.2022 → 22.01.2023 (~9.5 months) — signed Распоряжение №61 (03.11.2022) during this term.
- **Моргун О.В.**: 23.01.2023 → 06.11.2023 as глава администрации, then 06.11.2023 → 12.06.2025 as врио главы МО ГО Мариуполь (~2.5 years total) — accounts for his 156 ownerless decrees.
- **Кольцов А.В.**: врио главы МО ГО Мариуполь from 13.06.2025 — **current head** as of 2026-06-12. His 652/968 ownerless + 16/20 demolition decrees, signed in under a year, show a sharply accelerated signing rate vs. Моргун's 156 over 2.5 years — corroborates [[lifecycle_completion_removal_decrees]]'s independent "accelerating" finding (9 снятие-с-учёта decrees found 2026-03→06).

This closes "Known gaps / next steps" item 1 below: the command chain is now
fully dated and primary-sourced — **Пушилин (apex, every appointment + every
land grant) → Иващенко (2022) → Моргун (2023–2025) → Кольцов (2025–present)**,
each installed by Пушилин's own signature. Decree-signing date ranges in
`ownerless_decrees.jsonl`/`demolition_decrees.jsonl` can now be cross-checked
against these tenure windows as a corroboration/QA pass (not yet run).

Raw OCR text + sha256 lineage: `data/parsed/denis_pushilin_appointment_chronology.jsonl`.

**Demolition commission members** (from the 20 parsed «О сносе» decrees):
Цыба Л.В., Лысенко М.Г., Мирошниченко Я.С., Клисак Н.А., Хараджа О.С.,
Кирьякулова О.В., Овсиенко И.А. — all listed as Администрация городского
округа Мариуполь; **Хаджинов Д.М.** — МУП «Коммунальник». Role strings are
partially truncated by OCR; full titles recoverable from raw scans.

**Municipal organs:** Администрация городского округа Мариуполь (court
petitioner in the особое-производство cases — see Postgres petitioner
actors); МУП «УК Жилсервис» (recipient of pooled seized stock, №493);
МУП «Коммунальник»; Мариупольское городское управление юстиции (registration
organ, e.g. №5351/14.11.2022 for Распоряжение №61).

## Tier 4 — Commercial beneficiaries (developers receiving reallocated land)

From the 51 captured DNR land orders ([D], no-auction КРТ grants signed by
Пушилин) + EGRUL extracts. **All looked-up INNs are region-93 registrations
with OGRN dates 2024–2026 — i.e. entities created post-occupation,
seemingly for the purpose of receiving the grants.**

| Developer | Land orders | INN / OGRN date | Director (EGRUL) | Founders (EGRUL учредители) |
|---|---|---|---|---|
| СЗ-1 «Порфир» | **11** | 9310009271 (EISGHS match, EGRUL pending) | — | — |
| СЗ «ЭВОДОМ-5» | **9** (8+1 variant) | 9303038232 (EISGHS match, EGRUL pending) | — | — |
| СЗ «Строительное управление-2007» | **6** | 9310008599 (EISGHS match, EGRUL pending) | — | — |
| СЗ «Строительное управление-2007 Инвест» | **2** | 9310015807 (EISGHS match, EGRUL pending) | — | — |
| СЗ «Олимпстрой НР» | 2 | 9309027678 / 2024-05-28 | Сарибекян А.В. | Сарибекян А.В. **100%** (ИНН 615425703530, Rostov Oblast) — same person as director |
| АО «ЭВЕРЕСТ ДОМОСТРОЕНИЕ» | 2 | 9303042743 / **2026-03-06** | Попченко В.Г. | n/a — АО, no shareholder disclosure in basic EGRUL extract |
| СЗ «Солнечная» | 2 | 9311026992 (EISGHS match, EGRUL pending) | — | — |
| «Региональная строительная компания» | 2 | 9309026106 (EISGHS match, EGRUL pending) | — | — |
| СЗ «Восход» | 2 | 9310013976 / 2024-04-17 | Майоров М.И. | Майоров М.И. **33.4%**, Скоркина О.А. **33.3%**, Романькова И.Н. **33.3%** — all Moscow ИНН (77x) |
| СЗ «МираСтрой 3» | 1 | 9303036524 / 2024-02-15 | **Василенко И.И.** | **Василенко И.И. 90%** (ИНН 505397224950, Moscow Oblast) + Сущёв А.Б. **10%** (ИНН 504793037222, Moscow Oblast) |
| СЗ «МираСтрой 4» | 1 | 9303036531 / 2024-02-15 | **Василенко И.И.** ← same person, 2 LLCs | **Василенко И.И. 47.5%** + Сущёв А.Б. **10%** (same 2 as МираСтрой 3, Moscow Oblast) + Коршаков Д.А. **10%** + Соболев А.Д. **32.5%** (both Moscow) |
| СЗ «НОВОЕ ВРЕМЯ 3» | 1 | 9309028294 / 2024-09-20 | Митин С.В. | **100%** ООО «УК «БРИК ИНВЕСТ»» (ИНН 9310017730, region-93/DNR — holding co., own founders unknown) |
| СЗ «Корпорация СМУ-5» | 1 | 9310017508 (EISGHS match, EGRUL pending) | — | — |
| СЗ «СИРИУС БИЛД» | 1 | 9310014320 (EISGHS match, EGRUL pending) | — | — |
| СЗ «Антарес» | 1 | 9310014480 / 2024-05-28 | Радченко М.Р. | Радченко М.Р. **90%** (ИНН 771991715001, Moscow — same person as director) + Гуливер А.В. **10%** (ИНН 772021556533, Moscow) |
| СЗ «РКС-Девелопмент» | 1 (decree №291 — note: decree bundles ≥2 separate parcels, see below) | 9310007980 (decree text, EGRUL pending) | — | — |
| СЗ «Новое время 2» | 1 (decree №291, same decree as RKS-Devel. above — 3,136 m² parcel, Troianda-M/Metallurgov 47 footprint) | EGRUL not yet pulled — **caution: a directory search for this name also returns an unrelated Ufa/Bashkortostan company building in Khimki; do not conflate** | — | — |
| ООО «СГМ МОНТАЖ» | (registry) | 9310018029 / 2025-03-19 | Харламова Т.С. | Чернов А.И. **100%** (ИНН 771002232940, Moscow) |

### Founders / ownership chains (script 41, 2026-06-12)

Local re-parse of the 8 already-captured EGRUL records'  `СвУчредит`
(founders/shareholders) blocks — `data/parsed/egrul_founders.jsonl`, no new
network calls. 7 of 8 disclose individual or org founders (АО «ЭВЕРЕСТ
ДОМОСТРОЕНИЕ» does not — joint-stock companies don't disclose shareholders
in the basic extract).

- **Every individual founder is registered in mainland Russia — none in
  region-93/DNR.** Moscow (77x ИНН): Чернов А.И. (СГМ МОНТАЖ), Радченко
  М.Р. + Гуливер А.В. (Антарес), Майоров М.И. + Скоркина О.А. + Романькова
  И.Н. (Восход), Коршаков Д.А. + Соболев А.Д. (МираСтрой 4). Moscow Oblast
  (50x ИНН): Василенко И.И. + Сущёв А.Б. (МираСтрой 3 & 4). Rostov Oblast
  (61x ИНН): Сарибекян А.В. (Олимпстрой НР). This is direct EGRUL evidence
  that the post-occupation "local" SPVs receiving no-auction land grants are
  beneficially owned from mainland Russia — relevant to the
  population-transfer/"transfer of the occupier's population" framing
  (8(2)(b)(viii)) at the commercial-beneficiary tier.
- **Василенко И.И. + Сущёв А.Б. jointly own *and* direct both МираСтрой 3
  and МираСтрой 4** (sequential INNs, same registration day, 2024-02-15) —
  confirms the prior director-level finding at the ownership level: one
  two-person mainland-Russia partnership controls both grant recipients.
  Василенко's stake differs (90% in МираСтрой 3 vs 47.5% in МираСтрой 4,
  where Коршаков Д.А. and Соболев А.Д. hold the rest).
- **СЗ «НОВОЕ ВРЕМЯ 3» is 100% owned by ООО «УК «БРИК ИНВЕСТ»»** (ИНН
  9310017730, region-93/DNR registration) — a holding company, not an
  individual. Its own founders are unknown; БРИК ИНВЕСТ's INN does not match
  any of the 17 developer-company INNs (no cross-link to another grant
  recipient found yet). **Candidate for a follow-up EGRUL lookup** to extend
  the ownership chain one more hop.
- **Director-founder overlap**: Сарибекян А.В. (Олимпстрой НР) and Радченко
  М.Р. (Антарес, 90%) are both director *and* majority founder of their
  respective SPVs — i.e. not pure nominees, personally exposed.

Remaining 9 developers' founders pending the captcha-free EGRUL Phase-2 run
below (`scripts/41_parse_egrul_founders.py` is local-only and re-runnable
against the expanded set once captured).

## Edge taxonomy (graph model, script 40)

| rel | from → to | Source |
|---|---|---|
| `signed` | official → instrument-class node | ownerless/demolition decrees, land orders |
| `commission_member` | person → demolition commission | `demolition_decrees.jsonl` `officials` |
| `petitioned` | municipal admin → court-proceedings node | Postgres `actor` role=signing_official (petitioner) |
| `ruled_in` | judge → court-proceedings node | Postgres `actor` role=judge |
| `granted_land_to` | Глава ДНР → developer | `dnr_land_orders.jsonl` (decree refs in evidence) |
| `received_contract` | contractor → reconstruction node | `damage_assessment.jsonl` |
| `oversees` | ППК «Единый заказчик» → contractors | 〃 |
| `directs` | person → developer LLC | `egrul_inn_lookups.jsonl` |
| `transferred_stock_to` | Кольцов/№493 → МУП «УК Жилсервис» | decree №493 ([REPORTED] until captured) |
| `delegates_to` | Глава ДНР → city admins (Указ №301) | script 38 capture |

## Accountability mapping (Rome Statute)

- **Command chain (art. 28 / 25(3)(b)):** Пушилин (framework + land grants +
  every appointment) → city administration heads, now **fully dated**
  (Иващенко 06.04.2022→22.01.2023 → Моргун 23.01.2023→12.06.2025 → Кольцов
  13.06.2025→present, see Tier 3 chronology) → signing officials (Кольцов,
  Моргун, Перепечай, Дмитриев, Краснолуцкая, Матейко) → commission members.
  Each link is evidenced by signed instruments already in the raw store with
  SHA-256 chains.
- **Unlawful appropriation (8(2)(a)(iv) / 8(2)(b)(xiii), (xvi)):** ownerless
  decrees + court transfers + №493 stock pooling + land grants.
- **Population transfer (8(2)(b)(viii)):** служебное жильё channel
  (demand-side docs) + 2% mortgage to imported personnel; the housing lists
  attest the disposal of appropriated stock.
- **Aiding/abetting (25(3)(c)):** commercial tier — developers receiving
  no-auction grants on seized land, federal contractors building on cleared
  footprints (demolish→rebuild address laundering).
- **Judicial actors:** judges granting особое-производство transfers — the
  judicial veneer of rung [B]; named per case in the DB.

## First-run findings (script 40, 2026-06-12)

Graph: **52 persons + 53 orgs, 138 relations, ~8,100 evidenced acts.**

- **Кольцов А.В. is the operational center of gravity**: 652 ownerless
  decrees + 16 demolition decrees signed — 668 instruments, vs 157 for the
  next signer (Моргун О.В.).
- **Judges ranked** (cases from the DB): Романов Д.С. **288**, Мяконькая
  Т.А. **201**, Гревцова В.А. **188**, Кралинина Н.Г. **173**, Белоусов П.В.
  **162**, Тлеужанова Б.Е. **146**, Струнов Н.И. **143**, Резниченко В.А.
  **138**, Нидзиева Н.Н. **128** — ~27 named judges in total.
- **The prosecutor petitions too**: Прокуратура города Мариуполя appears as
  petitioner-of-record in особое-производство transfers, once naming the
  officeholder — **Гнездилов Д.В., старший советник юстиции**. A
  DNR-prosecution organ initiating civil expropriation petitions is a
  distinct accountability lane from the administration's own filings.
- **Petitioner identity consolidation**: the court portal's petitioner field
  is clerk-typed free text — 60+ raw spellings reduced to **8 entities**
  (Mariupol city admin [52 variants], Прокуратура, МИЗО ДНР, ФГИ ДНР,
  Минстрой ДНР, морской порт ГУП, Орджоникидзевский район admin, and one
  individual, Христофоров М.В.). Keyword buckets + rapidfuzz ≥0.8, raw
  spellings preserved per node.
- **МИЗО ДНР and ФГИ ДНР petition Mariupol courts directly** — DNR-republic
  organs acting as petitioners in what is nominally a municipal ownerless
  process, evidencing vertical integration of the pipeline.

## Known gaps / next steps

1. **Appointment decrees** («о назначении») — **DONE 2026-06-12.** The
   script-39 archives-only crawl completed in full (2,894/2,894 PDFs);
   script 43 indexed all 6 archives and flagged 13 Мариуполь-matched Указы,
   9 of which form the complete appointment chronology (see Tier 3 above),
   captured incidentally by the full crawl. Script 44 OCR'd + extracted all
   9 (scanned, no text layer). Result: Иващенко (06.04.2022→22.01.2023) →
   Моргун (23.01.2023→12.06.2025) → **Кольцов (13.06.2025→present,
   врио глава МО ГО Мариуполь)** — fully dated, primary-sourced.
   `scripts/42_capture_appointment_decrees.py` is now **redundant** (all 4 of
   its targets were already captured by the full script-39 run before
   script 42 was even written) — no need to run it.
2. **Remaining INN lookups** — **ready to run, captcha-free.** The "8
   pending" were actually 9 developers whose INN is already known
   (EISGHS fuzzy-match ≥97 or decree text) but never EGRUL-verified:
   Порфир, ЭВОДОМ-5, Строительное управление-2007 (+ Инвест variant —
   2 distinct INNs), Корпорация СМУ-5, Солнечная, Региональная строительная
   компания, СИРИУС БИЛД, РКС-Девелопмент. All 9 INNs are now pre-filled in
   `data/parsed/egrul_manual_inns.json` (17 total incl. the 8 already
   resolved) — run `scripts/20_lookup_egrul.py` to fetch+verify+capture all
   17 via `egrul.org/{INN}.json` (no captcha needed for pre-filled INNs).
3. **EGRUL founders** (учредители) — **done for the 8 already-resolved
   developers**, see "Founders / ownership chains" above
   (`data/parsed/egrul_founders.jsonl`, script 41). After item 2's run
   captures the remaining 9, re-run script 41 (local, no network) to extend
   the founder table. Follow-up candidate: ООО «УК «БРИК ИНВЕСТ»» (ИНН
   9310017730, 100% owner of НОВОЕ ВРЕМЯ 3) — one more EGRUL hop.
4. **Position titles** for the 6 ownerless-decree signers — recoverable from
   decree letterhead OCR (raw scans in store; parse upgrade to script 06).
5. **Judge-level statistics** — cases per judge / grant rates per judge, from
   the DB (script 40 report includes the counts once run against Postgres).

## Federal-tier chain: VSK → Олимпситистрой → Оборонспецстрой → Тимур Иванов (2026-06-20)

A new loader, `load_open_source_investigations` (script 40), ingests curated
findings from published investigative journalism — needed because this chain
is Moscow-registered federal institution-building with no DNR-local SPV, so
it's invisible to the EGRUL/decree/land-order pipelines that surface every
other developer on this network. Source file:
`data/parsed/open_source_investigations.jsonl` (add future findings there,
not by hand-editing the generated nodes/edges output).

**The chain:** ППК «Военно-строительная компания» (ВСК, 100%-state MoD
subsidiary, already on the spine via the `scripts/134` vskmo.ru crawl for the
Nakhimov Naval School branch) contracts **ООО «Олимпситистрой»**
(ИНН 7719585979, ОГРН 1067746433204, Moscow; founders Хавронин Д.А. /
Фомин А.Г., 50/50) as main contractor — 2022 revenue ~47bn RUB, ~2x
pre-invasion. Olimpsitistroy subcontracts to **ООО «Оборонспецстрой»**
(ИНН 7734691114, ОГРН 1127747177887), developer-of-record for **ЖК
«Невский»** in Mariupol (12 five-story buildings, 1,011 apartments,
**housing distributed rather than sold** — direct demand-side evidence,
see `memory/demand_side_architecture.md` channel 3 / Rome Statute
art. 8(2)(b)(viii)). Oboronspetsstroy separately purchased marble for
**Тимур Иванов**'s (former Russian deputy defense minister, who lobbied VSK
into existence in 2020) mansion and owns Tver-Oblast land adjacent to his
family estate — the personal-benefit thread from his 2024-2025 Russian
corruption conviction.

**Not yet done:** address/cadastral match for ЖК Невский against the spine;
confirmation of the VSK-subcontracted ~60,000 m² medical center's location.
**Naming-collision flag:** Olimpsitistroy (Moscow) is unrelated to the
already-on-spine «Олимпстрой НР» (`org:олимпстрой-нр`, ИНН 9309027678,
Donetsk-registered) — name similarity only.
