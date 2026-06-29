# Legal Mechanisms of Dispossession — Mariupol (2022–2026)

**A stage-by-stage review of the legal instruments the Russian occupation uses to
strip Mariupol residents of their property, mapped to the seizure lifecycle and
to the two accountability endpoints (RD4U restitution + Rome Statute).**

This is the framework layer behind the operational records the pipeline already
holds (court cases, ownerless register, demolition register, land orders, ЕИСЖС).
Each operational act cites an enabling norm; this document catalogues those norms.

> **Source-status legend** — every instrument is tagged with how well we hold it:
> - **[CAPTURED]** — primary text in our raw store / loaded in the DB (source_type noted).
> - **[CITED]** — referenced *inside* a captured record (court ruling, decree preamble) but the act's own text is not yet captured.
> - **[REPORTED]** — established from secondary research (HRW, Dossier, news, memory); needs primary capture to be claim-grade.
> - **[region80 ▶]** — a `scripts/35_crawl_pravo_region80.py` target: the DNR-level act whose authoritative text that crawl should retrieve.
>
> Nothing tagged [REPORTED] or [CITED] is claim-grade until its primary text is
> captured and hashed. This document is a research map, not an evidence assertion.

---

## Three legal tiers

The dispossession runs on three stacked layers of law. Knowing which tier a norm
sits on tells you where to capture it:

| Tier | Issuer | Where published | Our source |
|---|---|---|---|
| **Federal** | РФ Президент / Госдума / Правительство; codes (ГК, ГПК, ЗК, ЖК РФ) | pravo.gov.ru federal blocks; КонсультантПлюс | partial; mostly [REPORTED] |
| **DNR regional** | Глава ДНР, Народный Совет ДНР, Правительство ДНР, (wartime) ГКО ДНР | **publication.pravo.gov.ru / region80** + нпа.днронлайн.рф | **scripts 35/37 + script 13** |
| **Mariupol municipal** | Глава администрации г. Мариуполя | mariupol.gosuslugi.ru | scripts 05/08 [CAPTURED] |

The new region80 crawl fills the **middle tier** — the connective legal tissue
between the federal framework and the municipal operational orders. It is the
layer most thinly held today.

---

## The pipeline and its legal mechanism at each rung

```
 ENABLING FRAMEWORK ──▶ [A] OWNERLESS/APPROPRIATION ──▶ [B] COURT TRANSFER ──▶
 [C] DEMOLITION ──▶ [D] LAND REALLOCATION ──▶ [E] REBUILD ──▶ [F] RESALE
                                          └▶ [G] HOUSING ALLOCATION (parallel)
                                          └▶ [H] TOPONYMY / ADDRESS LAUNDERING (parallel)
```

### Framework (top of chain) — the authority to remake the city

| Instrument | What it does | Status |
|---|---|---|
| **ФКЗ от 04.10.2022 №5-ФКЗ** (admission of the DNR into the RF) | Makes Russian civil/land/housing law applicable in Mariupol — the predicate for everything below. | [REPORTED] · federal |
| **Постановление ГКО ДНР №1 (06.04.2022)** «Об урегулировании вопросов строительства, реконструкции, капитального ремонта, восстановления поврежденных и разрушенных объектов на территории ДНР» | The master predicate for the entire demolish→land→rebuild chain — the **first GKO act, signed 3 days after the GKO itself was created** (Указ №121, 03.04.2022; predates ФКЗ-5-ФКЗ by 6 months — a DNR wartime act later folded into the federal framework). Directs every line ministry + concern + district/city administration to compile lists of damaged/destroyed objects "включая жилую и социальную инфраструктуру"; authorises Russian contractors (mutual recognition of RF licences/permits; works under this Постановление are explicitly **not** "самовольное строительство" and are exempted from DNR construction-permitting law). **§2.5 is the origin clause**: the "authorised body" seizes land plots "for state needs" (при необходимости) and hands them to contractors **free of charge** for the duration of works. **§3.1** requires local administrations to give contractors unimpeded access and "resolve" (i.e. override) any third-party rights/encumbrances on those plots. Cited by Постановление №282 (29.09.2022, below, [D]) as its enabling instrument. Names Никоноров А.Ю. (Руководитель Администрации Главы ДНР) as responsible official — candidate addition to stakeholder network. | **[CAPTURED]** — denis-pushilin.ru `Post_GKO_1.pdf` (sha256 `378f56aa0169..`), OCR'd 2026-06-12 (9,499 chars; sha `0e8d8e232357..`) |
| **Указ Главы ДНР №420 (30.07.2022)** «О концепции разработки генерального плана г. Мариуполя» | Authorises the master-plan / demolish-and-rebuild programme citywide. | [CAPTURED] (raw store, per memory) · [region80 ▶] verify |
| **Постановление ГКО ДНР №162 (23.07.2022)** «Порядок сноса зданий…, повреждённых в результате ведения боевых действий» | The demolition procedure: commission, inspection, authorisation chain. Top of chain for every demolition. Signed Пушилин. | [CAPTURED] (script 13, нпа.днронлайн.рф) |
| **Постановления ГКО ДНР №205 (27.08.2022), №245 (19.09.2022)** | Amend №162 (add HQ review step; further amendment). | №205 [CAPTURED]; №245 [CITED] |
| **Указ врио Главы ДНР №73 (28.12.2022)** «Об особенностях регулирования имущественных отношений и отношений по государственному кадастровому учету недвижимого имущества, государственной регистрации прав на недвижимое имущество на территории ДНР» | The base property-relations/cadastral-transition framework, in force **until 01.01.2028**. Минюст ДНР performs cadastral registration (apartment units, IZHS houses on plots ≤3,000 м², inheritance, etc.) pending the Russian federal cadastral authority's territorial office. **§8**: from 01.01.2024, property transactions (sale, gift, rent >3yr, trust management) require **mandatory notarization or are void** (ничтожность) — a procedural barrier for displaced owners trying to transact remotely. **§13**: pre-existing (incl. Ukrainian-era) registered rights are recognised as "юридически действительными" — *if a claimant asserts them* — the claim-it-or-lose-it hinge that, left unclaimed, feeds the [A] ownerless track. Cited repeatedly by Указ №290 (16.08.2023, below, [E]) as пункты 11¹/11²/11⁷. | **[CAPTURED]** — denis-pushilin.ru `Ukaz_73_28122022.pdf` (sha256 `c72912278f45..`), OCR'd 2026-06-12 (14,102 chars; sha `280ef69ed42b..`) |
| **ФКЗ-4 от 15.12.2025** (the Dec-2025 pivot) | **Abolishes the court stage** for ownerless property: registry inclusion alone now confers municipal title. Collapses [A]+[B] into an administrative act. | [REPORTED] · federal (ФКЗ-4 itself); DNR implementing acts **[CAPTURED]** — закон ДНР №134-РЗ (05.12.2024, base "Об особенностях регулирования жилищных отношений…в переходный период") + №240-РЗ (22.12.2025) + №275-РЗ (17.04.2026), region80 (scripts 35/37) |
| **Federal property-registration-ban decree chain — Указ №1103 (24.12.2024) → №145 (14.03.2025) → №1006 (29.12.2025)** «Об особенностях осуществления государственной регистрации... на территориях ДНР, ЛНР, Запорожской и Херсонской областей» | Found via `@mrpl_besxozxata` chat analysis (2026-06-26), not the formal-acts crawl — citizens discussing it pointed to it before this project's own crawler did. Three-step escalation, each closing a remaining avenue for Ukrainian/"unfriendly-state" citizens to retain property: **№1103** (24.12.2024) bans registration of unfriendly-state-linked legal entities and of unfriendly-state citizens' property rights, both without special permission. **№145** (14.03.2025) extends/clarifies: legal-entity ban through 01.01.2026, citizen property-rights ban through **01.01.2028**; carves narrow exemptions (foreign military contractors serving in the Russian armed forces, soldiers discharged after 24.02.2022 for specified reasons, and their spouses/children/parents — military-service-linked persons, not ordinary civilian owners) decided by a "collegial body" within 3 business days — **this is what residents in the chat call "СРК" (Специальная региональная комиссия)**, not a separately-named institution. **№1006** (29.12.2025) closes the remaining loophole residents were using — bans **notarization of powers of attorney** and other legally-significant acts concerning this property for unfriendly-state citizens, through 31.12.2027. Interacts directly with Указ №73 §8 above (which already made notarization *mandatory* for any property transaction from 01.01.2024) — the combined effect is that a Ukrainian citizen now cannot transact AT ALL without the notarization act itself being banned for them specifically. Doverennost/POA was the single most-discussed survival mechanism in 6,620 of the chat's messages (`mrpl_besxozxata_intel_summary.json`); №1006 directly targets it. | **[CAPTURED]** — press summaries via `ppt.ru` (№1006, sha256 `94b9bdb1d6b4..`) and `rg.ru` (№145 full text, sha256 `162fd0a8e8da..`), `scripts/172`; №1103 sourced via web search only, primary text not yet captured. **Corroborated by the administering ministry's own channel** (@mizodnr/1028, 14.01.2026, sha256 `5d2cd4ee0a359d28..`, `scripts/174`/`177`) — МИЗО ДНР confirms №1006 covers registration of hostile-state-linked legal entities, their property rights, **and «совершения отдельных нотариальных действий»** (the notarial-acts/POA ban), with explainer «карточки». The minister, **Яков Ходос**, personally runs reception lines on «регистрации прав… гражданами недружественных государств», issuing **спецразрешения** and citing a **«комиссия по правоустанавливающим документам»** (Title-Documents Commission) — the supply-side body deciding whether a displaced owner's Ukrainian-era title is "legalised" (the choke-point in ВС ДНР case 33-2875/2025). See `docs/new_telegram_channels_intel_2026-06.md` |
| **Закон ДНР №279-РЗ (принят Народным Советом 15.05.2026)** «Об особенностях выявления, учета, изменения категорий (перечней) и использования объектов имущества, расположенных на территории ДНР, на которые возникает право государственной собственности» | The newest (last month) DNR-wide absorption framework: 29 categories of former-Ukrainian-state/municipal property (incl. property of Ukrainian "территориальных общин (громад)") transfer to Russian state ownership "в силу закона" pending federation/DNR/municipal property demarcation. Scope is overwhelmingly **infrastructure/institutional** (roads, rail, ports, airports, defence, schools, hospitals, utilities, pharmacies) — **not** private residential housing, which stays on the [A] ownerless track (закон №66-РЗ etc.). Category 1) (property of Ukrainian territorial communities/громады) is the only item that could touch *municipally*-owned (pre-war Mariupol city council) housing stock — no privately-owned residential category appears. Mainly evidence the absorption-legislation programme is still actively expanding in mid-2026. | **[CAPTURED]** — denis-pushilin.ru `279rz.pdf` (sha256 `4ab965fe0ed3..`), OCR'd 2026-06-12 (21,064 chars; sha `d8210e434e04..`) |

### [A] Ownerless designation / appropriation — manufacturing "no owner"

The civil-law engine. A privately owned, war-emptied flat is declared
*бесхозяйная недвижимая вещь* and routed to municipal ownership.

| Mechanism / instrument | Role | Status |
|---|---|---|
| **ГК РФ ст. 225** (бесхозяйная вещь) | Substantive basis for treating a flat as ownerless. | [REPORTED] · federal |
| **Постановление ГКО ДНР №153 (08.07.2022)** «О признании права собственности на недвижимое имущество, расположенное на освобожденных территориях ДНР, ранее временно находившихся под контролем Украины» | The general predicate for *recognising* property rights at all in newly-occupied territory (Mariupol fully occupied by 20.05.2022): state registration of rights on "освобождённых территориях" proceeds **only** on the basis of sale/gift/exchange contracts or inheritance certificates produced by a claimant. Everything outside this — the typical situation of a displaced owner who cannot produce paperwork or appear in person — is exactly what the ownerless track (закон №66-РЗ + Постановление №300, below) absorbs. Predates закон №66-РЗ (2024) by ~20 months. | **[CAPTURED]** — denis-pushilin.ru `Post_GKO_153.pdf` (sha256 `cd5cd9bf1012..`), OCR'd 2026-06-12 (2,075 chars; sha `82cb70028b9c..`) |
| Mariupol admin **ownerless-designation постановления** + the **12,948-entry ownerless registry** | The operational act: utility cut-off → "ownerless" notice → inspection → designation → registry inclusion. | [CAPTURED] (scripts 05/26/27; `ownerless_designation` 604 + `registry_inclusion` 12,948) |
| DNR procedure governing how a municipality runs the ownerless process | The regional rulebook the municipal decrees execute. | **[CAPTURED]** — закон ДНР №66-РЗ (21.03.2024, base) + №272-РЗ (17.04.2026) + №269-РЗ (03.04.2026, disposal/compensation) + №137-РЗ (13.12.2024, amendment), region80 (scripts 35/37) |
| **Закон №66-РЗ ст. 5(3)(а) — personal-appearance step, citizenship-neutral on its face, citizenship-coded in effect** | The one procedural escape from ownerless designation: an owner can stop the process by personally appearing within 30 days of the public notice with proof of title — but the statute names **only "паспорт гражданина Российской Федерации"** as acceptable ID, with no foreign-passport clause, and ВС ДНР practice treats a representative/POA-holder's appearance as not counting at all, only the title owner's own. Document-confirmed in ВС ДНР case №33-641/2024 (doc_id 1166152, Mariupol, captured `scripts/12`, 2026-06-26) and replicated across 4 more cases outside Mariupol, captured the same day: №33-1731/2025 (Докучаевск) and №33-1590/2025 (Торез) — owners who personally appeared (even after a years-long delay) won procedurally; №33-1529/2025 (Донецк, owner explicitly "находится за пределами Российской Федерации") and №33-1509/2025 (Володарское, absent owner + present POA-holding tenant of years' standing, paying utilities) — both lost, the POA-holder's own appeal for standing rejected outright. **This is a DNR-wide judicial practice, not a Mariupol-specific anomaly.** None of the 5 rulings state any owner's citizenship explicitly — "находится за пределами Российской Федерации" (outside RF territory) is the operative language, not a nationality finding — but for Mariupol-area owners this is in practice a near-proxy for displacement to Ukraine/the EU. Same structural shape as Указ №1006's POA-notarization ban above: a facially citizenship-neutral procedural rule whose real-world burden falls overwhelmingly on displaced Ukrainian owners. Found via @mrpl_besxozxata chat msg 84043 (thread msg 84041 explicitly frames it as foreign-citizen disadvantage); the 4 comparison cases were user-supplied, found independently of that chat thread. | **[CAPTURED + READ]** — ВС ДНР doc_id 1166152 (sha256 `ac395f60643148d2573b9c73a4926d301936562142b9c1db66633ee895a8c252`) + case_ids 1988037/1986749/1986186/1985702 (`dnr_supreme_court_docket_case`); see `memory/mrpl_besxozxata_deep_intel_2026-06-26.md` |
| **Постановление ГКО ДНР №300 (29.09.2022)** «О порядке использования в городе Мариуполе жилых помещений, имеющих признаки бесхозяйных» | Mariupol-specific regional (ГКО) procedure governing residential premises that exhibit signs of ownerlessness — the wartime-emergency predicate, ahead of the general закон №66-РЗ (2024) above, that the municipal ownerless-designation постановления execute for Mariupol specifically. | **[CAPTURED]** — denis-pushilin.ru `/postanovleniya-gosudarstvennogo-komiteta-oborony/Post_GKO_300.pdf` (sha256 `fe28a13f901a..`), scanned image (no text layer), signed Пушилин; found via script 43 index of the completed script-39 archive crawl, 2026-06-12 |
| **ФКЗ-4 15.12.2025** | Removes the judicial check; registry = title. | [REPORTED] |
| **Указ Главы ДНР №515 (02.11.2023)** «О порядке вскрытия жилых и нежилых помещений в многоквартирных домах при отсутствии их собственника (владельца, пользователя)…» | Establishes a "Типовой порядок" for **forced entry into apartment-building units when the owner/occupant is absent**, citing ГК РФ ст.1067 (necessity) and ЖК РФ ч.3 ст.3. Stated scope is narrow — emergency repair of building-wide engineering systems (аварийные ситуации) — not a general ownerless-inspection power. Still establishes the *legal mechanism* (administration enters an apparently-unoccupied unit without the absent owner's consent) that the ownerless-designation inspection step (`ownerless_designation`) operationally mirrors. Worth checking whether any captured inspection records cite this Указ as authority. | **[CAPTURED]** — denis-pushilin.ru `Ukaz_N515_02112023.pdf` (sha256 `3e763b6843a1..`), OCR'd 2026-06-12 (18,964 chars; sha `ed094e07737c..`) |
| **Mariupol municipal property-lease rulebook — Распоряжение главы администрации г. Мариуполя №61 (03.11.2022)** «Об утверждении Временного порядка передачи в аренду имущества муниципальной собственности города Мариуполя, Временной методики расчета арендной платы…» | **[CAPTURED] + READ 2026-06-29 — CORRECTS the prior [A]→[D]/[F]/[G] "disposal bridge" framing.** A working HTML mirror was found and captured (`scripts/207`) after the original PDF route went dead. Read in full: **both attachments (the Временный порядок and the Временная методика) explicitly EXCLUDE объекты жилого фонда and вспомогательные помещения жилого фонда** (the exclusion clause is repeated verbatim in each attachment's opening article) — this is a generic procedural framework for leasing *non-residential* municipal property (commercial premises, целостные имущественные комплексы of municipal enterprises, embedded non-residential space inside residential buildings e.g. ground-floor shops) to any legal entity/individual/sole proprietor, with no reference anywhere in the text to the ownerless/bezkhoz pipeline or to residential housing stock. **It is NOT part of the residential [A]→[F]/[G] reallocation chain** — that earlier characterization should be treated as superseded. It may still be the operative instrument for *commercial* space recovered alongside seized residential buildings (e.g. ground-floor retail), a narrower and unverified claim. | **[CAPTURED]** — `scripts/207` (npa.dnronline.su article-route HTML mirror, plain HTTP, no geoblock; the original PDF link is the confirmed dead end, do not re-try); registered Мариупольское горуправление юстиции №5351/14.11.2022, signed К.В. Иващенко. |
| **Распоряжение главы администрации г. Мариуполя №619 (12.10.2023)** «О проведении сплошной инвентаризации объектов недвижимого имущества (многоквартирных жилых домов и домов индивидуального жилого строительства), расположенных на территории муниципального образования города Мариуполя» | Citywide property-inventory order ("сплошная инвентаризация") — the inspection step immediately upstream of [A]'s ownerless-designation/registry-inclusion stage, applied per-district (zone offices named by district, e.g. "Участок Жовтневого района — ул. Гранитная, 114" per a building-specific notice photographed at пр. Ленина 106, 2026-06-19) requiring residents to produce title documents by a zone-specific deadline (106's zone: 01.03.2024) or be treated as not having claimed the unit. Full preamble text captured **verbatim, repeatedly**, as quoted boilerplate inside resident-chat messages across multiple buildings (e.g. `deep_intel_records.jsonl` rows for `invite_QaRRTdUZFw0OTU6`, `invite_ooUT61cOOFZjMDcy`; `kronshtadtskaya_chat_signals.jsonl` flags `official_notice`/`resident_presence`) — but the decree's own primary scan, and the building-106-specific zone notice itself, are NOT yet in the raw store. | [CITED] (text only, across ≥5 chats) — pending primary capture; a photo of the 106-specific zone notice was shown directly in conversation 2026-06-19 without a source URL/timestamp and could not be forensically ingested as-is (see case study note) |

→ **RD4U:** A3.6 (loss of access). **Rome:** appropriation of property not justified
by military necessity, art. 8(2)(a)(iv); the displaced owner never consents.

**Comparative pattern (29.09.2022 batch):** the same GKO sitting that produced
Mariupol's Постановление №300 (ownerless-housing designation, above) also issued
**Постановление №267** «Об обращении недвижимого имущества в муниципальную
собственность» — an *individual* seizure, **without compensation**, of a
residential building at пос. Старобешево, ул. Хапланова, д. 16, transferred into
Старобешевского района municipal property. Same mechanism ("принудительное
изъятие... без компенсации собственнику... возникновение права муниципальной
собственности"), same date, different town — confirming the 29.09.2022 batch was
a **standardized template rolled out across multiple newly-stabilized frontline
settlements simultaneously**, not a Mariupol-specific improvisation. **[CAPTURED]**
(sha256 `b6fd0c04c0b9..`, OCR'd 2026-06-12, 2,515 chars; sha `58a3dedc4ae2..`).

A **second, distinct** seizure track exists in the same batch: Постановления
№283/284/285 (29.09.2022), each "Об изъятии имущества для государственных нужд"
**with compensation**, all for Донецк addresses (ул. Лучезарная 4 — жилой дом →
Управление специальных программ ДНР; бул. Пушкина 2А — часть общественного
здания, partly already adjudicated to Фонд гос. имущества ДНР by a 2018
arbitration ruling; ул. Щорса 48 — нежилые объекты → Администрация Главы ДНР).
This "eminent-domain-with-compensation-for-state-use" track is mechanically
distinct from the "ownerless-without-compensation-to-municipality" track above —
no Mariupol instance of it has been found yet; if one surfaces it would need its
own row here. **[CAPTURED]** (shas `add1aecc771d..`/`3d69d2d157f4..`/
`a258463ae501..`, OCR'd 2026-06-12, 6,009/6,811/5,939 chars).

A separate ГКО act in the same batch — **Постановление №228 (06.09.2022)**, "Об
обращении имущества ООО «КОМБИНАТ «КАРГИЛЛ»... в государственную собственность" —
nationalizes a foreign (US, Cargill) commercial asset at г. Донецк, ул. Бойцовая
80. Confirmed **not Mariupol** (location is Donetsk); a third, commercial-asset
nationalization track, out of scope for this property pipeline. **[CAPTURED]**
(sha256 `afaecc9b9d12..`, OCR'd 2026-06-12, 2,883 chars; no further action).

### [B] Court transfer — the judicial laundering of title (pre-Dec-2025)

| Mechanism | Role | Status |
|---|---|---|
| **ГПК РФ гл. 33** (особое производство) — *признание права муниципальной собственности на бесхозяйную недвижимую вещь* | The case type. Self-incriminating lifecycle, dated, signed by named judges. | [CAPTURED] (scripts 03/178/182–185; **8,271 cases across 26 DNR courts**, 87.1% granted; `court_petition`/`court_transfer`/`appeal`) |
| Occupation court rulings | Per-property transfer act. | [CAPTURED] |

→ Superseded going forward by ФКЗ-4 (Dec 2025) but governs the 2022–2025 stock.

### [C] Demolition — erasing the building (and the identity chain)

| Instrument | Role | Status |
|---|---|---|
| ГКО ДНР №162/205/245 (framework, above) | Authorises razing. | [CAPTURED]/[CITED] |
| **Указ врио Главы ДНР №40 (02.12.2022)** «О порядке выявления и сноса объектов, поврежденных в результате боевых действий» | DNR-wide "Порядок сноса объектов, поврежденных в результате боевых действий" — requires publication of demolition-candidate object information on local-administration AND Минстрой ДНР websites. Cites ФКЗ №5-ФКЗ ст.21 ч.2 directly (post-annexation legal basis), unlike ГКО №162/205/245 (pre-annexation, GKO-era acts). **Both amendments now OCR'd 2026-06-28** (`scripts/194`): **№657 (03.12.2024)** is a pure institutional renaming pass — every instance of "местная администрация" (local administration) is replaced with "орган местного самоуправления" (local self-government body), formalizing occupied territories' incorporation into the Russian municipal-government structure; **its substantive change is §1.4.7, which adds language requiring that demolition trigger "снятие с государственного кадастрового учета и (или) государственной регистрации прекращения прав на недвижимое имущество"** — the demolition decree now explicitly authorises de-registering the property and terminating the owner's recorded rights, closing the demolish→deregister loop in writing rather than leaving it implicit. It also updates the reference to the **«Оперативный штаб по восстановлению»** from the body created by ГКО №75 (20.05.2022, wartime/pre-annexation) to the one created by **Указ №157 (16.05.2023)** as "Оперативного штаба по восстановлению субъекта Российской Федерации — Донецкой Народной Республики" — the same operational body re-grounded in federal-subject law post-annexation, not a new body (relevant to the stakeholder-network entry added 2026-06-28). **№513 (24.06.2025)** is narrower: adds "архитектуры" to the responsible-department reference twice, and **removes the Operational HQ's role as gatekeeper of the demolition list** — §1.2.1 replaces "перечню, установленному решением Оперативного штаба..." (the list set by the HQ's decision) with "законодательству Российской Федерации и Донецкой Народной Республики" (general legislation) — a procedural loosening that drops the one named decision-making body from the demolition-designation step. Relationship to ГКО №162/205/245 (which predate №40 by 3-4 months) remains unresolved by either amendment — neither references them; still flagged for future review. | **[CAPTURED]** — denis-pushilin.ru `Ukaz_40_02122022.pdf` (sha256 `fc4085b07ad3..`), OCR'd 2026-06-12 (10,564 chars; sha `5636362dc585..`); amendments `Ukaz_N657_03122024.pdf` (sha `9d9f8ea0..`, OCR sha `c79fcf7f..`, 4,143 chars) + `Ukaz_N513_24062025.pdf` (sha `d33496fa..`, OCR sha `e2a7a4f4..`, 1,738 chars) |
| **Распоряжение ГКО ДНР №56 (29.09.2022)** — Mariupol demolition list | Named-building demolition order (e.g. Нахимова 82). | [CITED] (case 33-2575/2025); **confirmed absent from region80** (full 2,221-record index searched 11.06.2026, scripts 35/37), from нпа.днронлайн.рф's 7-item ГКО Распоряжения 2022 category (`npa.dnronline.su`, script 38), **and** from denis-pushilin.ru's own `/rasporyazheniya-gosudarstvennogo-komiteta-oborony/` archive — `Rasp_GKO_{1,2,5,8,9,10,28,51}.pdf` exist but `Rasp_GKO_56.pdf` returns HTTP 404 (verified 2026-06-12). Three independent normative-acts sources now agree: №56 is an internal operational order, not published on any normative-acts portal |
| Mariupol admin **«О признании объектов подлежащими сносу» / «О сносе»** распоряжения | Per-district demolition lists. | [CAPTURED] (script 08; `demolition` events) |
| **MinStroy demolition register** | Administrative manifest of razed buildings. | [CAPTURED] (scripts 14/15; 525 Mariupol buildings) |

→ **RD4U:** A3.1/A3.2 (destruction). **Rome:** extensive destruction/appropriation
of property not justified by military necessity, art. 8(2)(a)(iv).

### [D] Land reallocation — handing cleared land to developers without auction

| Instrument | Role | Status |
|---|---|---|
| **ЗК РФ** provisions on allocation **без торгов** for КРТ (комплексное развитие территорий) | Federal basis for no-auction grants. | [REPORTED] · federal |
| **Постановление ГКО ДНР №282 (29.09.2022)** «Об особенностях изъятия и предоставления земельных участков, необходимых для… восстановления объектов капитального строительства… поврежденных и разрушенных в результате боевых действий» | The **land-for-reconstruction seizure procedure**, predating закон №39-РЗ (29.12.2023) by ~15 months. Implements Постановление №1's §2.5 (Framework, above): local administration + contractor + "субъект обследования" survey the site and the contractor drafts a "план застройки" (site plan), approved by the **«Оперативный штаб по восстановлению ДНР»** (Operational HQ for DNR Reconstruction — new named body, candidate addition to stakeholder network). **§4 is the key clause**: where the approved план застройки covers privately-owned land plots (previously granted for personal use), those plots — *after identifying their owners* — are seized "в установленном порядке" with compensation (replacement housing, replacement land, or cash capped at normative/average valuation). Owners get a 3-month public-notice window (posted on official sites, public boards, on-site signage) to file a claim with proof of ownership; after that window, the administration drafts the seizure-and-compensation act within 10 days. Explicitly covers "территории разрушенной вследствие боевых действий индивидуальной жилой застройки" (destroyed individual-housing areas) — directly on-point for Mariupol private houses. | **[CAPTURED]** — denis-pushilin.ru `Post_GKO_282.pdf` (sha256 `301263e3ef29..`), OCR'd 2026-06-12 (6,079 chars; sha `9a3643a9f2ed..`) |
| **Распоряжения Главы ДНР (Пушилин)** leasing parcels to застройщик-SPVs without auction — e.g. **№289 (07.09.2023)**, №125/162/163/164, №291, №290, №419/420, №415 | The reallocation act: parcel → named beneficiary. | [CAPTURED] (scripts 10/11; `dnr_land_orders.jsonl`; 15 parsed) — but published on the DNR legislative portal; **[region80 ▶]** is the federal-register copy |
| DNR КРТ / no-auction land-allocation procedure | The rulebook behind the распоряжения. | **[CAPTURED]** — закон ДНР №39-РЗ (29.12.2023, base) + amendments (№145-РЗ/221-РЗ/263-РЗ/266-РЗ) + Постановление №29-4 (21.03.2024, "без проведения торгов" rent-rate procedure) + №64-4 (03.07.2025, amends №29-4), region80 (scripts 35/37) |

→ **Rome:** appropriation + the system/intent layer (named beneficiary + official).

### [E] Rebuild — the new building under a new address

| Instrument | Role | Status |
|---|---|---|
| **ЕИСЖС / наш.дом.рф** registration (per-дом ID, РПД, ввод в эксплуатацию) | The new-build record; carries the project-name-vs-address mismatch that proves footprint identity + address break. | [CAPTURED] (scripts 17/18; 20 objects; `reallocation` events) |
| Russian **damage-assessment / reconstruction tracker** | Federal record of the destroyed building it replaces. | [CAPTURED] (script 32; `mirror_source` corroboration) |
| **Указ Главы ДНР №290 (16.08.2023)** «Об особенностях внесения в ЕГРН сведений о ранее учтенных объектах недвижимости и выполнения комплексных кадастровых работ… а также выявления правообладателей ранее учтенных объектов недвижимости» | Implements Указ №73 (28.12.2022, Framework, above): mass + application-based migration of "ранее учтенные объекты недвижимости" (РУОН — i.e. Ukrainian-cadastre-era records) into the Russian ЕГРН via "комплексные кадастровые работы" (ККР) performed exclusively by ППК «Роскадастр», citing ФЗ №218-ФЗ ст.69/69.1 and ФЗ №221-ФЗ. **§1.7**: scanning/registration of РУОН documents proceeds "вне зависимости от… присутствия (проживания) правообладателя… на территории ДНР" — a displaced owner's absence doesn't block their property entering the new Russian cadastre under their name (if a Ukrainian-era document trail exists) — but see Указ №73 §13/§8 (Framework, above) for the claim-it-or-lose-it hinge and the notarization barrier. This is the cadastral machinery underneath every "ЕИСЖС / наш.дом.рф" new-build registration in this rung. | **[CAPTURED]** — denis-pushilin.ru `Ukaz_290_16082023.pdf` (sha256 `cb2206fc29a1..`), OCR'd 2026-06-12 (24,461 chars; sha `ce6bfa8ca3c2..`) |

**Legal basis for "rebuild on the same footprint"** (the [E]/[F] mechanism in
`docs/case_studies/nakhimova_82_chernomorsky_1b.md`): Постановление ГКО №175
(30.07.2022, [G] below) §5.3 — "Компенсационное жилье предоставляется в доме,
строящемся **на месте разрушенного объекта недвижимого имущества**, в котором
находилось жилье заявителя" — replacement housing is built *on the site of the
destroyed property*. This is the earliest located primary-text statement of the
demolish→rebuild→reallocate principle: 8 months before the Нахимова 82 →
Черноморский 1Б case and 17 months before закон №39-РЗ.

→ See `docs/case_studies/nakhimova_82_chernomorsky_1b.md` for the worked example.

### [F] Resale — transferring title to the occupier's population

| Instrument | Role | Status |
|---|---|---|
| **Льготная ипотека 2%** (federal subsidy, open to ANY RF citizen, to 2030) | Financial inducement channel — the population-transfer engine. Mar 2024–Apr 2025 also covered the secondary market for SVO participants / силовики / бюджетники. | [REPORTED] · federal |
| ЕИСЖС sold-out percentages | Evidence of disposal (e.g. Черноморский 1Б 94% sold). | [CAPTURED] |

→ **Rome:** art. **8(2)(b)(viii)** — transfer of the occupier's own civilian
population into occupied territory. The subsidy law is the *instrument of policy*.

### [G] Housing allocation (parallel) — service housing + legitimation

| Instrument | Role | Status |
|---|---|---|
| Federal law on **служебное жильё** to officials/military/police/teachers/doctors until **01.01.2028** | Direct state allocation to imported personnel — population-transfer core. | [REPORTED] · federal |
| **Постановление ГКО ДНР №175 (30.07.2022)** «О компенсации за утраченное или поврежденное жилье, а также за утраченное имущество первой необходимости лицам, пострадавшим в результате боевых действий» | The **base war-damage compensation procedure**, DNR-wide. Establishes compensation norms of **33 м² (single occupant), 42 м² (family of 2), +18 м²/additional member (family ≥3)**; valuation at **35,000 RUB/м²** for destroyed housing, up to **6,000 RUB/м²** for capital repair of damaged housing; replacement ("компенсационное") housing capped at **150 м²** (§5.2) and — critically — **built on the site of the destroyed property** (§5.3, see [E] cross-reference above). District/city-administration commissions process claims. | **[CAPTURED]** — denis-pushilin.ru `Post_GKO_175.pdf` (sha256 `63b87ec3a915..`), OCR'd 2026-06-12 (57,729 chars; sha `80c5a8805486..`) |
| **Постановление ГКО ДНР №263 (29.09.2022)** «Об урегулировании имущественных вопросов пополнения маневренного фонда города Мариуполя» | Mariupol-specific regional (ГКО) act regulating the property questions of replenishing the city's маневренный фонд — the wartime-emergency regional predecessor (Sept 2022) to the municipal Decree №493 (05.03.2026, Кольцов) below, which pools 18 buildings into the same fund. | **[CAPTURED]** — denis-pushilin.ru `/postanovleniya-gosudarstvennogo-komiteta-oborony/Post_GKO_263.pdf` (sha256 `f3a676688bc3..`), scanned image (no text layer), signed Пушилин; found via script 43 index of the completed script-39 archive crawl, 2026-06-12 |
| **Маневренный фонд — Decree №493 (05.03.2026, Кольцов)** moving 18 buildings to МУП «УК Жилсервис» | Pools seized stock for allocation. | [REPORTED]; absent from region80 (likely Mariupol municipal, not DNR regional). DNR-level framework **[CAPTURED]**: Постановление ГКО №263 (29.09.2022, Mariupol-specific, above) + Постановления №93-2 + №93-3 (both 18.09.2025, маневренный фонд / служебное жильё procedures) + №29-2 (21.03.2024, служебное жильё), region80 (scripts 35/37) |
| Mariupol **housing-distribution lists** (5,822 queued / 1,889 distributed) + **25 m² compensation cap** | Legitimation channel to displaced locals; cap suppresses claims. | lists [CAPTURED] (scripts 16/29; `displacement_claim` corroboration); cap [REPORTED] |

**Note on the 25 m² figure:** Постановление №175 (above) — the only base
compensation-norm instrument captured so far — sets norms of **33/42/+18 м²**
and a **150 м²** replacement-housing ceiling, **not 25 м²**. The 25 m² cap
therefore remains [REPORTED] and is a *different* instrument/scheme — possibly
a служебное/маневренное-жилье allocation norm (distribution-list track) rather
than a war-damage compensation norm. Needs its own primary capture; do not
conflate with №175's norms.

→ **Rome:** 8(2)(b)(viii) (служебное жильё to imported personnel) + disposal of
appropriated property (lists). **RD4U:** the lists themselves attest A3.6 loss.

### [H] Toponymy / address laundering (parallel) — severing the paper trail

| Instrument | Role | Status |
|---|---|---|
| **Renaming-authority framework — Указ Главы ДНР №301 (20.06.2022)** «О присвоении наименований, переименовании географических объектов и составных частей населенных пунктов ДНР» | DNR-wide enabling norm: approves the "Временные правила присвоения наименований, переименования географических объектов и составных частей населённых пунктов ДНР" and **delegates renaming of streets/microdistricts/other settlement components to district and republic-significance city administrations** (incl. Mariupol). The legal basis under which the Mariupol-specific renaming decrees below are issued. | **[CAPTURED]** — signed scan in raw store (sha256 `764ee734...`, captured via script 39 from `denis-pushilin.ru/doc/ukazy/Ukaz_301_20062022.pdf`; created 2022-06-20 09:13 CEST per PDF metadata, matches decree date); page 1 verified — title/heading/Пушилин signature block confirmed 2026-06-12. Also [CITED] on нпа.днронлайн.рф (`npa.dnronline.su` mirror), but that portal's `doc.нпа.днронлайн.рф` PDF link is dead (host NXDOMAIN; bare-domain path 404s — likely stale post-migration link), so denis-pushilin.ru is the operative primary source. |
| DNR/Mariupol **street-renaming decrees** (≈75 streets / 113 objects russified), issued by the Mariupol administration under the Указ №301 delegation | Changes the address so the destroyed property "no longer exists" — defeats cadastral/address joins and compensation claims. | partly [CAPTURED] in `data/toponyms.csv`; the **decrees themselves confirmed absent from region80** (full index searched 11.06.2026, scripts 35/37) and absent from the нпа.днронлайн.рф "Распоряжения глав городов и районов ДНР" category (only 4 items total, checked 2026-06-12) — likely issued directly by Mariupol admin (mariupol.gosuslugi.ru, scripts 05/08), not published on any normative-acts portal |

→ **RD4U:** the mechanism of *denial* the Register exists to overcome. Pairing the
renaming decree with the new ЕИСЖС address is high-value corroboration.

---

## The region80 crawl — results (2026-06-11/12)

`scripts/35_crawl_pravo_region80.py` captured the **complete region80 index**
(2,221 records across 12 index pages — forensic manifest of all DNR official
publications) plus the **dispossession-relevant PDF subset** (lexicon: снос/
бесхозяйн/изъят/земельн/жил/переселен/компенсац/градостроительн/генплан/
переименован/кадастр…, 43 stems) — **395 PDFs + metadata captured**, all hashed
and timestamped 2026-06-11. `scripts/37_parse_pravo_region80.py` then categorized
the 395 captures against the priority list below and wrote
`data/parsed/pravo_region80_relevant.jsonl`.

| # | Priority target | Outcome |
|---|---|---|
| 1 | ФКЗ-4 / DNR implementing acts (Dec-2025 court-stage abolition) | **Resolved** — закон ДНР №134-РЗ (05.12.2024) + №240-РЗ (22.12.2025) + №275-РЗ (17.04.2026) |
| 2 | Указ Главы ДНР №420 (30.07.2022) master-plan — re-confirm federal-register copy | Not re-checked this pass (already [CAPTURED] from a prior session); not in the 395-record lexicon subset |
| 3 | DNR ownerless-property procedure | **Resolved** — закон ДНР №66-РЗ (21.03.2024) + №272-РЗ (17.04.2026) + №269-РЗ (03.04.2026) + №137-РЗ (13.12.2024) |
| 4 | DNR КРТ / no-auction land-allocation procedure | **Resolved** — закон ДНР №39-РЗ (29.12.2023) + Постановление №29-4 (21.03.2024, "без проведения торгов") + №64-4 (03.07.2025, amendment) |
| 5 | Маневренный фонд / служебное жильё DNR acts | **Resolved** (general framework) — Постановления №93-2/№93-3 (18.09.2025) + №29-2 (21.03.2024). Decree №493 itself remains uncaptured (likely Mariupol municipal) |
| 6 | Street-renaming decrees | **Confirmed absent** from region80 — likely Mariupol municipal (mariupol.gosuslugi.ru, scripts 05/08) |
| 7 | Распоряжение ГКО ДНР №56 (29.09.2022) — federal copy | **Confirmed absent** from region80 — likely нпа.днронлайн-only (script 13's domain) |

Net: **4 of 6 outstanding [region80 ▶] gaps closed** with primary cited acts; the
remaining 2 are confirmed-absent from this register and redirected to their
likely actual sources. All 395 captured PDFs are scanned images with no text
layer (`pdftotext` yields only form-feed bytes) — OCR is not in the toolchain,
but [CAPTURED] status only requires holding the primary signed document +
bibliographic metadata (both held, hashed, in `data/state.sqlite`/`data/raw/`),
not an extracted text layer.

Each captured record is now linked via `data/parsed/pravo_region80_relevant.jsonl`
(act number, date, signing authority, document type, SHA-256, mapped pipeline
rung) — closing the loop from *enabling norm* → *operational act* → *specific
property*.

---

## Endpoint cross-reference (mechanism → claim)

> RD4U category definitions verified 2026-06-11 against the Board's own claim
> forms (rd4u.coe.int): **A3.1** = damage/destruction of *residential* immovable
> property; **A3.2** = same for *non-residential*; **A3.3** = loss of housing/
> residence (distinct from A3.1 — the claimant lost their home, not just
> damage to the structure); **A3.6** = loss of access/control of property in
> occupied territory ("cannot be used, transferred, or sold without relying on
> Russian authorities"). A property/claimant can file **more than one** category
> for the same property — `property.rd4u_category` is therefore a
> comma-separated set (script 36), not a single value.

| Rung | Lifecycle stage (DB `seizure_stage`) | RD4U | Rome Statute |
|---|---|---|---|
| A Ownerless | `ownerless_designation`, `registry_inclusion` | A3.6 | 8(2)(a)(iv) |
| B Court transfer | `court_petition`, `court_transfer`, `appeal`, `entered_force` | A3.6 | 8(2)(a)(iv) |
| C Demolition | `demolition` | **A3.1/A3.2 + A3.6** (destroyed *and* you can't access the cleared site without the occupation) | 8(2)(a)(iv) |
| D Land grant | `reallocation` | — (enables; attaches to the *new-build* record, not the original owner's claim) | 8(2)(a)(iv) + intent/beneficiary |
| E Rebuild | `reallocation` (new-build) | — | 8(2)(b)(viii) predicate |
| F Resale | `resale` | — | **8(2)(b)(viii)** |
| G Housing | `displacement_claim` (corrob) | **A3.3 + A3.6** (lost the residence *and* lost access/control) | 8(2)(b)(viii) |
| H Toponymy | (cross-cutting) | denial mechanism | facilitation |

Damage-tracker corroboration (`mirror_source`, independent of any seizure-pipeline
stage) → **A3.1** (residential) / **A3.2** (non-residential) per its
`property_type` field. 971 properties currently carry only this signal — they
are documented as war-damaged but not yet linked to a seizure act; good
candidates for further A3.6-evidence research.

---

*Forensic note: occupation/DNR normative acts are evidence of the seizure system,
NOT valid title. Ukraine does not recognize them; neither do we. Capture every
act before parsing; SHA-256 + source URL + UTC timestamp on each (CLAUDE.md).*

See `docs/reconceptualization_2026.md`, `docs/case_studies/`, and the memory
files for `[[federal-law-dec2025-pivot]]`, `[[demand-side-architecture]]`,
`[[demolition_rebuild_address_laundering]]`, `[[developer-beneficiaries-dnr]]`,
`[[dnr_wide_scaffolding_review]]` (2026-06-12 DNR-wide scaffolding scan: 14 new
[CAPTURED] instruments across Framework/[A]/[C]/[D]/[E]/[G]).
