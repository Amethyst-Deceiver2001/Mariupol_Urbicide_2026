# Mariupol Urbicide Project — Source List

All sources used across the project's research: burial sites catalogue, case studies, stakeholder network, legal analysis, and general investigation. Grouped by source family. Occupation/Russian-state sources are labelled as such where they appear; they are used for cross-reference only.

---

## 1. Occupation Primary — Decrees and Administrative Documents

**Распоряжение ГКО ДНР №56** (29 September 2022) — demolition list naming проспект Строителей д.78, 80, 88, 112. Text mirrored at base.garant.ru. Confirmed absent from нпа.днронлайн and denis-pushilin portals (internal operational order). The same order's 177-address Mariupol schedule, per the DNR MinStroy Unified Demolition Register CSV (row 277), also names прт. Металлургов, д. 47 — the Troianda-M demolition-authorization instrument (`case-study-troianda-metallurgov.html`); mirror: <https://minstroy-dpr.gosuslugi.ru/app/uploads/2024/09/eb14dd_reestr-snosa_16_03_2026.csv> (geoblocked, captured via VPS).

**Распоряжение ГКО ДНР №54** (29 September 2022) — the Levoberezhny quarter's own demolition order (MUP-CS-012), naming full odd-numbered ул. Ломизова 3–19, even-numbered бульвар 50 лет Октября 4–22, бульвар Комсомольский 2–38/2, and odd-numbered ул. Азовстальская 7–33 (54 addresses). No independently captured decree text/URL for №54 itself exists yet — the citation is resolved via the same DNR MinStroy Unified Demolition Register CSV as №56 above (row-level address list, `data/parsed/minstroy_demolition_register.jsonl`, csv sha256 `d431a53003e51456c4052a805e1cc6c42e9417b315314df7e4b23ca40742ea37`), which lists every address the order covers. Register coverage is visibly incomplete for a handful of in-polygon addresses (Азовстальская 24, 50 лет Октября 11/26/28, and 50 лет Октября 9 — the last chat-confirmed demolished despite no register row) — a genuine open gap, not evidence against those buildings' inclusion. Cited in `docs/case_studies/levoberezhny_quarter_demolish_and_abandon.md` and `levoberezhny-quarter-exhibit.html`.

**Распоряжение ГКО ДНР №172** (18 April 2023) — demolition list naming проспект Строителей д.72, 117. Text mirrored at base.garant.ru.

**Распоряжение Главы ДНР №289** (07 September 2023) — leases the 3,204 m² Nakhimova 82 / Chernomorsky 1B parcel to ООО «СЗ-1 Порфир» without tender, for the "«Многоквартирный жилой дом... по просп. Нахимова 82»" investment project; signed Пушилин. Source: <https://denis-pushilin.ru/doc/rasp/rasporiazhglavaN289_07092023.pdf> (geoblocked, captured via VPS; OCR'd `scripts/246`-adjacent pass, 2026-07-07). Cited in Exhibit A (Nakhimova 82).

**Minstroy DNR project-planning-territory (ПТТ) document, `@minstroydnr/3932`** (5 October 2023) — designates the ~36 ha Primorsky КРТ redevelopment zone (bounded by Кронштадтская/Строителей/Нахимова/Черноморская), demolition of 9 multi-apartment buildings for >25,000 m² of new construction; signed Александр Авдиенко, head of urban-planning and architecture, Минстрой ДНР. Source: <https://t.me/minstroydnr/3932>. Cited in Exhibit A (Nakhimova 82) and `docs/legal_mechanisms_review.md`.

**Постановление ГКО ДНР №175** (30 July 2022) «О компенсации за утраченное или повреждённое жильё…» — the base war-damage compensation procedure: a choice between compensational housing built on the site of the destroyed property (§5.3) or cash at 35,000 RUB/m² of lost living space. Set against the Mariupol municipality's own 2025 valuation of 111,038 RUB/m² (composite) / 146,205 RUB/m² (new-build) — see §3149 entry below — the cash option covers less than a third, and on the primary market less than a quarter, of the city's own declared value. Source: <https://glavadnr.ru/doc/GKO/post/Post_GKO_175.pdf>. Cited in Exhibit A (Nakhimova 82, arithmetic section).

**Распоряжение главы администрации г. Мариуполя №619** (12 October 2023) «О проведении сплошной инвентаризации объектов недвижимого имущества (многоквартирных жилых домов и индивидуального жилого строительства)…» + amendment **№71** (24 February 2024, deadline extension only) — citywide door-to-door housing inventory, framed as routine seasonal winter-preparedness accounting; the inventory form officially records "вид собственности" including "самозаселение" (informal occupancy) per building, months before any bezkhoz enforcement round. Now the leading candidate for the instrument "Распоряжение №264" (06.06.2024, below) actually refers to: a confirming news article and admin channel post (both user-supplied, 2026-07-08) show door-to-door visits began 23.10.2023 and asked residents to produce title documents plus ID for the owner and all residents on the spot, matching earlier chat-corpus findings of a zone-specific document-production deadline under this same decree — treat №264 as a probable miscitation of №619 rather than a separate act. A fourth corroborating source (user-supplied, 2026-07-08): an Орджоникидзевский-район administration notice scheduling door-to-door inventory for 29–30.05.2024 at eight named addresses, same personal-appearance/title-document demand, seven months into №619's run — and citing its legal basis as **Закон ДНР №66-РЗ (21.03.2024)**, not №619 by number, suggesting №66-РЗ is the DNR-wide statutory basis implemented locally via №619; also republished on Мариуполь 24 TV (t.me/mariupol24tv/62295). **A fifth source — direct photographic proof of physical enforcement** (user-supplied, 2026-07-08, @Mariupol_Buro/64646, community tips channel "БЮРО ⁉️ Подслушано в Мариуполе"): a resident photo of a printed notice taped to a gate in Гавань/Слободка (Приморский район) cites "Распоряжения Главы администрации города Мариуполя № 619 от 12.10.2023" **by number and date on the enforcement instrument itself**, instructing the resident to bring title documents to the Приморский district administration (ул. Черноморская, 6, Mon–Fri 9:00–12:00) "для идентификации объекта недвижимого имущества" — the first primary-source artifact naming №619 directly rather than describing it secondhand; handwritten-dated ≈01.07.24, stamped by the district administration. Closes essentially all remaining doubt that №619 is a genuine, currently-enforced instrument. Source: <https://mariupol-r897.gosweb.gosuslugi.ru/netcat_files/401/4727/619.pdf>, <https://mariupol-r897.gosweb.gosuslugi.ru/netcat_files/401/4727/71.pdf>, confirming article <https://mariupol.gosuslugi.ru/dlya-zhiteley/novosti-i-reportazhi/novosti_100.html>, TV republish <https://t.me/mariupol24tv/62295>, БЮРО photo post <https://t.me/Mariupol_Buro/64646>. **[CAPTURED]** — `scripts/270`/`271`/`273`/`275`/`276`, sha256 `152136124ed240...` (№619, 8pp OCR'd)/`8517285a1d08ab...` (№71, 2pp OCR'd)/`4d00bdfa1f611d...` (confirming article)/`aff0cbb607bb...` (TV republish)/`fe171db4ce7c...` (БЮРО photo post). Cited in `docs/legal_mechanisms_review.md`.

**mariupol.gosuslugi.ru novosti_284** (09 January 2025) «В Мариуполе стартовал второй этап инвентаризации» + attached list **MKD_Invintarizatsiya.xlsx** (171 addresses) — a distinct, later "phase 2" of the inventory mechanism, downstream of №619's initial citywide survey: owners in 170 (per the article; the attached list has 171 rows) multi-storey buildings still under repair/restoration who have not yet registered title in Rosreestr must personally appear at any МФЦ with a full title-document package by 01.04.2025, explicitly framed as excluding the unit from the ownerless list. The list spans four districts (ЖРА 72, ОРА 68, ИРА 16, ПРА 14) and includes **проспект Ленина (Мира) д.104/106/108/110** — all four buildings in the existing Ленина 104/106/108/110 restoration-without-restitution case study — plus three проспект Нахимова addresses (д.88/1, д.98, д.118) and улица Черноморская д.31. Source: <https://mariupol.gosuslugi.ru/dlya-zhiteley/novosti-i-reportazhi/novosti_284.html>, list <https://mariupol.gosuslugi.ru/netcat_files/userfiles/MKD_Invintarizatsiya.xlsx>. **[CAPTURED]** — `scripts/277`, sha256 `237f2bb02ebfc0...` (article)/`496e526918590b...` (xlsx). Cited in `docs/legal_mechanisms_review.md`.

**"Гражданин Мариуполя" (@mrpl_ctzn) post #15533** (11 January 2025) — quotes Игорь Овсиенко, head of the Орджоникидзевский district administration: the President set the task of distributing all compensation housing in 2025, and the ongoing inventory (Распоряжение №619) exists to determine how many residents can be housed via bezkhoz/ownerless stock versus how much new compensation housing must still be built — an on-record admission tying the seizure/inventory pipeline directly to the compensation-housing shortfall. Unfulfilled as of this entry (2026-07-08), over 18 months past the stated deadline. Source: <https://t.me/mrpl_ctzn/15533>. **[CAPTURED]** — `scripts/278`, sha256 `9c7072ce50db9a...`. Cited in `docs/legal_mechanisms_review.md`.

**"Черный Список | Мариуполь" (@BLMariupol) post #19588** — Зелинского 13, a building saved from demolition by a resident campaign and restored, but with 74 apartments still uninhabitable; nearly all of those units have now been placed into bezkhoz status despite residents already appearing before a February 2024 document commission and a subsequent kilometer-long registration queue. Second building matching the restoration-without-restitution modality documented for пр. Ленина 104/106/108/110. Source: <https://t.me/BLMariupol/19588>. **[CAPTURED]** — `scripts/279`, sha256 `61d8a1595467033...`. Cited in `docs/legal_mechanisms_review.md`.

**"ЮРИСТ | Якубенко Борис Александрович" (@yakubenko_pravo_dnr) post #263** — DNR-licensed lawyer's professional advisory post: compensation-housing ордер (warrant) does not confer ownership, which vests only upon the recipient's own Rosreestr registration; cites a real client case where an heir cannot obtain an inheritance certificate because the deceased never registered, and warns non-registration risks the unit reverting to municipal ownership. Corroborates the "ордер-is-not-title" finding from the МКР «Невский» case study. Source: <https://t.me/yakubenko_pravo_dnr/263>. **[CAPTURED]** — `scripts/280`, sha256 `f7f3155328e1a2...`. Cited in `docs/legal_mechanisms_review.md`.

**ASTRA (@astrapress) post #76631** (15 March 2025) — independent Russian outlet reports Mariupol residents (пр. Победы 55/61), homeless for a third year, recorded a video appeal to Putin with "БОМЖИ" signs, quoted stating DNR authorities "decided to simply take apartments from living owners and call them ownerless." Cites 362 buildings demolished citywide, only 71 rebuilt, ~18,000-apartment shortfall (a different metric from the Dossier Center's 5,141-unit figure — report both, do not merge). Lists five unresolved compensation-housing failures (no same-district replacement housing, excluded share-ownership holders, deceased decision-holders, deceased-parent registrations, unprivatized housing). References ASTRA's own 19.06.2024 investigation into mortgage construction on seized demolished-building land. Source: <https://t.me/astrapress/76631>. **[CAPTURED]** — `scripts/281`, sha256 `e8b69f9b3ecfe8...`. Cited in `docs/legal_mechanisms_review.md`.

**Two TASS-sourced Моргун statements** (@novosti_mariupol1/25839, 04.04.2025; @mariupol24tv/91856, 20.05.2025) — Mariupol acting head Олег Моргун: municipal bezkhoz units to grow 5.5x to ~750 (142 current, 600 court decisions in force); owners can have a unit removed from the registry at any inventory stage by coming forward. Second statement: ~3,800 bezkhoz units citywide (~3,000 in ЕГРН, ~800 court-confirmed of ~1,000 petitions, ~200 denied when the owner appeared with documents); legal basis Закон ДНР №66-РЗ; 10,400+ queued for compensation housing since 2022, 5,600+ still queued, to be housed via new construction and bezkhoz apartments. Source: <https://t.me/novosti_mariupol1/25839>, <https://t.me/mariupol24tv/91856>. **[CAPTURED]** — `scripts/282`, sha256 `6c4010c14d709e...` (04.04.2025)/`59ecad60fca7f0...` (20.05.2025). Cited in `docs/legal_mechanisms_review.md`.

**Игнат Яремчук year-end briefing** (@allmarinews/39282, ~37 min, dated by content to late Dec. 2025) — Mariupol deputy head of administration, property/inventory portfolio, on-camera legal-mechanism walkthrough: explicit statutory ban on registering ownership rights for citizens of "unfriendly states" in the ЕГРН, with a discretionary security-service-linked collegial body as the sole override; ~60%/40% registered/unregistered residential-fund split; the 1 July 2026 Ukrainian-document-validity deadline restated on record; announcement of a new two-tier social/commercial tenancy regime for non-owner occupants of bezkhoz units; confirmation that returning owners whose unit already became municipal property are compensated with "квартиры из числа иных безхозяйных" (other ownerless units); a probate/heirs registration barrier and a since-unfulfilled promise to publish a corrective list by late January 2026; the 3-month EGRN provisional-bezkhoz window. Whisper-transcribed; ASR mis-transcribes some 4-digit years (e.g. "1928" for "2028") — treat exact digits as provisional. Source: <https://t.me/allmarinews/39282>. **[CAPTURED] + TRANSCRIBED** — `scripts/284`, sha256 `6ac5a6fe35a59f...`; transcript `data/parsed/allmarinews_39282_transcript.txt`. Cited in `docs/legal_mechanisms_review.md`, `docs/stakeholder_network.md`, `docs/exhibits/dispossession-pipeline.html`, `docs/exhibits/mariupol-master-dossier.html`.

**Олег Моргун Q&A livestream** (@morgun_ov/9992, ~46 min) — companion video to the Яремчук briefing above, same capture/transcription run; names Мариуполь administration property-office intake addresses Аэродромная 7 and бульвар Шевченко 301Б, and touches on border/filtration remarks. Source: <https://t.me/morgun_ov/9992>. **[CAPTURED] + TRANSCRIBED** — `scripts/284`, sha256 (video, see `data/raw` custody log via `source_document.url = 'https://t.me/morgun_ov/9992'`); transcript `data/parsed/morgun_9992_transcript.txt`. Cited in `docs/legal_mechanisms_review.md`, `docs/stakeholder_network.md`.

**Распоряжение главы администрации г. Мариуполя №264** (06 June 2024) «О проведении всеобщей инвентаризации муниципального жилищного фонда» — the citywide inventory order residents' own collective complaint template names as authorizing personal-appearance-with-original-documents-only inspections. **Number/date now doubted, likely a miscitation of №619 (2026-07-08)**: absent from the official six-document keyword index of every inventarization-related act on mariupol-r897.gosweb.gosuslugi.ru, despite its alleged title containing "инвентаризации" verbatim; the complaint's substantive claim (document production to a visiting commission, in person, or the unit is treated as unclaimed) matches confirmed findings for the real, correctly-numbered Распоряжение №619 (above). Decree's own primary text not yet found — known only via citation inside `@mrpl_besxozxata/34504` ("Жалоба_бесхоз.doc"). Cited in `docs/legal_mechanisms_review.md` and the dispossession-pipeline exhibits — treat as unconfirmed pending independent discovery.

**Постановление Администрации г.о. Мариуполь №1223** (05 August 2025) «Об утверждении Порядка инвентаризации недвижимого имущества, право собственности на которое возникло у муниципального образования городского округа Мариуполь…» + amendments **№1565** (09 October 2025, roster only), **№1727** (12 November 2025, roster only), **№1740** (14 November 2025, substantive) — the post-court-transfer physical inventory procedure for movable property left inside municipally-acquired real estate; includes a forced-eviction precondition (§5.3), forced door/lock replacement (§5.5), and a video-recorded room-by-room cataloguing protocol reaching down to furniture contents (§9.4–9.5); commission includes an MVD «Мариупольское» seat. **№1740 extends this entire procedure to properties made ownerless purely by ЕГРН registry entry (no court ruling)** — closing the gap between the registry-only pathway and the court-ordered pathway; also adds a Департамент капитального строительства seat and downgrades MVD's role from "по согласованию" to "по запросу". Source: <https://mariupol-r897.gosweb.gosuslugi.ru/netcat_files/396/4721/p.1223.pdf>, <https://mariupol-r897.gosweb.gosuslugi.ru/netcat_files/396/4721/p.1565.pdf>, <https://mariupol.gosuslugi.ru/netcat_files/396/4721/p.1727.pdf>, <https://mariupol.gosuslugi.ru/netcat_files/396/4721/p.1740.pdf>. **[CAPTURED] + READ** — sha256 `c0de9d5c08e2c0...` (№1223 PDF), `ce5dc46e20e087...` (№1565 PDF), `726e92bf7d838c...` (№1727 PDF), `668b1e7c84dae4...` (№1740 PDF); OCR derivatives `876a0fa469c396...`/`d80800cc7624c5...`. Cited in `docs/legal_mechanisms_review.md`.

**mariupol.gosuslugi.ru housing-queue (жилищная очередь) explainer page** — published terms for compensational-housing distribution to residents of demolished multi-apartment buildings. A unit is assigned to a resident unilaterally, with no choice of address; the resident may only accept or refuse (a first refusal re-queues them for another unilateral assignment; a second drops them from the queue entirely, leaving only cash compensation). Required documents include "original Russian Federation citizen passports of all owners" — compensation eligibility is conditioned on Russian citizenship. Source: <https://mariupol.gosuslugi.ru/dlya-zhiteley/poleznye-materialy/kvartirnaya-ochered/>. **[CAPTURED]** — `scripts/269`, sha256 `28d53b94fbf3156f...` (2026-07-07). Not geoblocked (TLS trust-store gap, not a network block — see script for detail); a separate 2026-06-09 capture of the same page at a different mirror host also exists (sha256 `51d7852fbdf3c79a...`). Cited in Exhibit A (Nakhimova 82, arithmetic section).

**Постановление АГО Мариуполь от 26.03.2025** «Об установлении показателя средней рыночной стоимости одного квадратного метра общей площади жилого помещения… на 2025 год» — the city's own official 2025 housing valuation: 146,205 RUB/m² (primary/new-build market), 75,871 RUB/m² (secondary/resale market), 111,038 RUB/m² (composite average, the figure actually applied for the low-income housing-queue threshold). Captured as a document attachment inside a Telegram post, not independently hosted. Source: <https://t.me/ssaniaworld/3149> (document attachment). Cited in Exhibit A (Nakhimova 82, arithmetic section) and `docs/legal_mechanisms_review.md`.

**DNR head land-allocation orders (Пушилин), Nos. 390–394** — sequential grants to СЗ-1 ПОРФИР (ИНН 9310009271) for проспект Строителей 74–88. Captured in project pipeline `data/raw/` with SHA-256 chain-of-custody.

- Decree portal: <https://denis-pushilin.ru/acts/>
- Normative acts portal: <https://нпа.днронлайн.рф>
- Regional law portal: <https://pravo.region80.ru>

**Mariupol ownerless-property decrees (постановления о бесхозяйном имуществе)** — 968 decrees captured from the Mariupol городское управление юстиции portal; signatories include Кольцов А.В. (652), Моргун О.В. (156), Дмитриев А.В. (55). Two kinds carry per-property lists: *designation* decrees («О признании… бесхозяйными и включении в Реестр») and *removal/reclaim* decrees («О снятии с учёта…» / «Об исключении… из Реестра», Закон ДНР №66-РЗ). The removal set (40 decrees, 208 rows, re-parsed 2026-07-02) is the pipeline's **reversal** signal — living owners/heirs surfacing with title proof, or, in one case, winning a court challenge (Ильичевский суд, дело №2а-916/2025) — not a seizure-completion endpoint; residential-only. Portal geoblocked; captured via `scripts/05`. See `docs/legal_mechanisms_review.md` [A] and `memory/lifecycle_completion_removal_decrees.md`.

**@nmrpl — «Официальный телеграм-канал Администрации ГО Мариуполь»** — the Mariupol city-district administration's official Telegram channel (<https://t.me/nmrpl>). Text-only crawl 2026-07-02 (`scripts/234`, 45,068 messages); 39 document attachments pulled (`scripts/232`/`233`). Primary source for the dated bezkhoz-candidate list series (earliest snapshot `ИЖС_бесхоз_Мариуполь.xlsx`, 27.03.2023 — the earliest bezkhoz document found anywhere in the project) plus a distinct industrial/commercial-sites bezkhoz track. Does **not** carry the individually-signed «Постановление Администрации №XXX» decree PDFs — those are exclusive to mariupol.gosuslugi.ru (`scripts/05`).

**Mariupol ownerless registry (ФКЗ-4 master list)** — 12,948-entry registry-as-title list across four Mariupol district courts.

**Demolition decrees (Mariupol municipal administration)** — 20 decrees captured + MinStroy register 637 rows (525 Mariupol buildings).

**Non-residential ("commercial/industrial") ownerless-signs lists (MinStroy DNR, June 2023)** — the non-residential parallel to the 12,948-row residential ownerless registry. Three captured primaries from the official Minstroy DNR channel: `Мариуполь_НЕ_ФУНКЦИОНИРУЮЩИЕ_ОБЪЕКТЫ_.xlsx` (<https://t.me/minstroydnr/3063>, 07.06.2023, 1,234 commercial premises "имеющие признаки бесхозности"; sha256 `0bb9f92bc16c8b…`), plus two dated industrial-parcel/commercial supplements `Перечень_промышленных_площадок…` (<https://t.me/minstroydnr/3227>, sha256 `10329c544204…`; <https://t.me/minstroydnr/3235>, 30.06.2023, sha256 `e6fd4ea0f13c…`) whose industrial tables carry cadastral numbers + parcel areas. Parsed by `scripts/290` → `data/parsed/nonresidential_ownerless.jsonl` (1,277 objects); loaded via `scripts/292` as `seizure_event(stage='ownerless_designation')`. A **newer combined residential+non-residential edition dated 05.06.2026** is referenced by residents (<https://t.me/mrpl_besxozxata/94813>) but held only as low-res phone-photos — `scripts/293` is the VPS crawl to capture the administration primary.

**Non-residential demolition list («Снос.pdf»)** — «ПЕРЕЧЕНЬ объектов, подлежащих сносу на территории города Мариуполя», 42 non-residential objects (shopping centres, hotels, warehouses, a bakery, «Дом связи», the «Ледо» complex, a DOSAAF building), posted by the official administration channel @nmrpl (<https://t.me/nmrpl/11325>, sha256 `f865092711e7…`). Largely non-overlapping with the MKD-focused MinStroy demolition register. Parsed by `scripts/291` → `data/parsed/nonresidential_demolition.jsonl` (42 objects, 40 address-resolvable); loaded via `scripts/292` as `seizure_event(stage='demolition')`.

**Russian federal damage/reconstruction tracker (XLSX)** — 1,941 buildings, contractor + destruction-% map. Via ЕИСЖС / наш.дом.рф.
- <https://наш.дом.рф>

**ЕИСЖС new-build object register** — objects 65280, 69427, 69749, 69751, 70142, 70147 («Резиденция Селект», «Резиденция II» and related developments on проспект Строителей).

**Occupation court dockets — 4 Mariupol district courts** (Жовтневый, Приморский, Орджоникидзевский, Ильичевский). 2,694 особое производство (бесхозяйная вещь) cases captured; see `docs/STATS.md` for current event counts. Portal addresses captured at time of crawl; geoblocked for direct access.

**DNR "Supreme Court" case 33-2575/2025** (13.11.2025, reporting judge Гуридова Н.Н.) — appellate ruling upholding denial of the 60-resident Troianda-M / Metallurgov 47 collective claim; also cited re: DNR State-Committee Directive No. 56 in the Stroiteley case study (MUP-CS-006). Captured `scripts/223` (run from user's VPS, geoblocked portal).
  - <https://vs--dnr.sudrf.ru/modules.php?name=sud_delo&srv_num=1&name_op=doc&number=2122362&delo_id=5&new=5&text_number=1>

**DNR Law 66-РЗ** and related ФКЗ-4 framework instruments — enabling legislation for the ownerless-property pipeline. Full texts in `data/raw/pravo_region80/`.

**Housing distribution lists (demand side)** — 5,822 / 1,889 rows; occupied-side record of displaced persons.

**Колхозники-документ / инвентаризация** — internal occupation inventory of housing stock with notes including "Дом полностью выгорел, во дворе труп, требуется уборка территории" (used in §03 of the master dossier).

**Corporation for the Development of Donbas (Корпорация развития Донбасса) press service** — developer marketing materials for «Резиденция Селект», проспект Строителей 74–88, 180 flats, Q4 2028 delivery.
- mariupol-news.ru, 16 January 2026

**Developer listing via Domklik / наш.дом.рф** — resale listing data, prices, flat configurations.

**ОГРН 1249300011873** — company registration for the Mariupol municipal housing department entity appearing on eviction ("ОПЕЧАТАНО") seals, Проспект Ленина 133.

---

## 2. Independent / Exiled Russian Media

**Meduza** — primary Russian-language independent outlet used throughout.
- "Каждый день просыпаешься — и ты кто-то новый. Сегодня ты могильщик" (Kirill Rukov), 10 June 2022. Gravedigger feature: Yaroslav Dema, Dmytro Kuznetsov; пр. Победы 32/42 and пр. Строителей 160 courtyard grave records.
  - <https://meduza.io/feature/2022/06/10/kazhdyy-den-prosypaeshsya-i-ty-kto-to-novyy-segodnya-ty-mogilschik>
- October 2023: Starokrymske cemetery expansion.

**zona.media (Медиазона)** — independent Russian news.
- «Карта разрушений. Как оккупированный Мариуполь сносят и отстраивают заново» (Alla Konstantinova, 29 January 2024) — resident (Oksana) testimony on fleeing 16.03.2022, occupation authorities inspecting/servicing her vacant flat, and being denied re-entry at the Ivangorod border crossing in Nov. 2023 ("нежелательный контакт"); Aleksandr Borman (orphan housing-queue beneficiary, 29 Героическая) denied reinstatement, told the lot was "приобретен под частную застройку"; Oct. 2022 mobile-housing-fund decree (30-day documentation deadline) and Oct. 2023 inventory procedure; demolition count 321/407 houses (Mar. 2023), 1,829 objects flagged for repair; RKS-Development resale pricing at Дом с часами (~150,000 RUB/m²; 1-bed 5M RUB, 2-bed 8.5M RUB), RKS-Development spokesperson on record disclaiming any compensation role; construction-labor testimony (Mikhail, Novosibirsk migrant worker, "Дружба" hotel-to-dormitory conversion) and the Ivan Orynchuk/«ТехнСтрой» award-then-embezzlement-arrest episode. Independent (non-occupation-aligned) corroboration of demolition-count and resale-pricing figures previously sourced only from occupation channels/developer sites. Captured `scripts/286`; Borman and RKS-Development pull-quotes added to the Stroiteley case study (MUP-CS-006), 2026-07-08.
  - <https://zona.media/article/2024/01/29/mariupol>

**Novaya Gazeta Europe** — used for context on occupation administration.
- «Доступное захваченное жильё» (22 February 2024) — resident denied compensation after her building was demolished and the lot bought by a private developer. Cited in the Stroiteley case study (MUP-CS-006); captured `scripts/222`. Also cited in the Nevsky microdistrict case study (VSK/Olimpsitistroy/Ivanov chain; социальный-наём allocation).
  - <https://novayagazeta.eu/articles/2024/02/22/dostupnoe-zakhvachennoe-zhile>

**Dossier Center (dossier.center)** — «Мариупольский бенефициар»: Timur Ivanov / ООО «Олимпситистрой» as the actual builder of ЖК/МКР «Невский» beneath the MoD's VSK. Cited in the Nevsky microdistrict case study.
  - <https://dossier.center/hus-ivanov/>

**Север.Реалии / RFE-RL (severreal.org)** — «"Это всё напоказ". Как в Мариуполе получают новые квартиры»: MoD-built new flats allocated via договор социального найма (revocable social tenancy), not ownership. Cited in the Nevsky microdistrict case study.
  - <https://www.severreal.org/a/kak-v-mariupole-poluchayut-novye-kvartiry-/32367722.html>

**Verstka (verstka.media)** — occupied-territory "ownerless"-designation mechanism; social-tenancy vs ownership for war-affected residents. Cited in the Nevsky microdistrict case study.
  - <https://verstka.media/kak-vlasti-priznayut-beshoznym-zhile-na-okkupirovannyh-territoriyah>

---

## 3. Ukrainian and International Journalism

**Associated Press / AP Special Projects** — anchor for citywide burial scale.
- "Russia scrubs Mariupol's Ukraine identity, builds on death" (Michael Biesecker et al., December 2022). ~10,300 new graves; Starokrymske cemetery satellite analysis; "building upon a city of death" framing; Erashova family case. Cited in the Stroiteley case study (MUP-CS-006); captured `scripts/222`.
  - <https://apnews.com/article/russia-ukraine-war-erasing-mariupol-499dceae43ed77f2ebfe750ea99b9ad9> (verified 2026-06-30; the previously listed `.../russia-ukraine-war-mariupol-graves` slug now 404s — link rot, replaced)
- AP/Planet Labs satellite imagery of cemetery expansion.

**BBC Panorama / Centre for Information Resilience (CIR)** — satellite grave count.
- Analysis of Maxar imagery, 7 November 2022: ≥4,600 graves at Starokrymske by that date, 1,500 new since June 2022.
- CIR Eyes on Russia project: <https://eyesonrussia.org>

**Reuters** — video documentation: Solnechnaya 8 courtyard burials; Andrei Lodygin and neighbours digging graves in frozen ground.

**Radio Svoboda / Svoboda (Крим.Реалії)** — video at проспект Строителей 160; Andriushchenko statements on Novotroitske sectors (26 April 2023).

**Kyiv Independent** — Vynohradne / Manhush highway construction (2025); occupation-era updates.
  - <https://kyivindependent.com>

**Babel (babel.ua)** — Drama Theatre rubble clearance; bodies trucked to Manhush.
  - <https://babel.ua/en/news/78890-the-occupiers-in-mariupol-completed-dismantling-the-rubble-of-the-destroyed-drama-theater-the-found-bodies-were-buried-in-a-mass-grave>

**Ukrainska Pravda** — Andriushchenko statements (ул. Киевская 53, ~100 bodies; пр. Победы × бул. Меотиды, ~100 bodies; Drama Theatre toll, May/July 2022).
  - <https://www.pravda.com.ua/eng/news/2022/05/24/7348183/>

**0629.com.ua** — Mariupol local news outlet; memorial "Пам'ятаємо кожного маріупольця" (victim-by-victim record used for courtyard burial addresses).
  - <https://www.0629.com.ua/photo/645>
  - <https://www.0629.com.ua/news/3844728/rosiani-pobuduvali-vijskove-ucilise-na-misci-futbolnoi-bazi-fk-mariupol>

**RBC-Ukraine / rbc.ua** — makeshift burial found in Mariupol (27 July 2023 discovery at Prymorskyi park / Nakhimov школа).
  - <https://www.rbc.ua/rus/news/mariupoli-viyavili-shche-odne-stihiyne-pohovannya-1690470612.html>

**Espreso** — second makeshift burial discovery in Mariupol park.
  - <https://espreso.tv/viyna-z-rosiyeyu-v-okupovanomu-mariupoli-viyavili-shche-odne-mistse-stikhiynogo-pokhovannya-lyudey-miskrada>

**Hromadske / Громадське радіо** — occupation administration coverage.

**UNITED24 Media** — Manhush mass-grave site cleared, converted to R-280 highway staging area (2025–2026 satellite confirmation).
  - <https://united24media.com/latest-news/russia-erases-mass-burial-site-near-occupied-mariupol-satellite-images-show-18125>

**Axios** — satellite imagery of Vynohradne (April 2022).
  - <https://www.axios.com/2022/04/22/ukraine-mariupol-mass-graves>

**freeradio.com.ua / Вільне Радіо (MRPLmap)** — пр. Мира 127: ≥45 named victims, concealed Starokrymske trench chronology 2022–2024.

**cxid.media** — "Прихована поховання у Маріуполі збільшується з 2022 року."
  - <https://cxid.media/news/v-okupovanomu-mariupoli-znayshly-prykhovane-pokhovannia-iake-z-iavylosia-u-2022-rotsi/>

**ZMINA (zmina.info)** — courtyard burials in Покровськ/Mariupol; пр. Будівельників 189 (~11 buried); вул. Троїцька (~20 buried).
  - <https://zmina.info/news/u-pokrovsku-mizh-budynkamy-pochaly-z%CA%BCyavlyatysya-pohovannya-czyvilnyh-a-deyaki-tila-zagyblyh-zalyshayutsya-prosto-neba/>

**Glavcom (glavcom.ua)** — mass burial discovered in Mariupol.
  - <https://glavcom.ua/news/u-mariupoli-znajdeno-masove-pokhovannja-zhertv-rosijskikh-obstriliv-1116976.html>

**Obozrevatel (obozrevatel.com)** — open-air morgue on asphalt; Manhush mass grave destroyed.
  - <https://incident.obozrevatel.com/crime/v-mariupole-ustroili-morg-na-asfalte-tela-lezhat-pod-solntsem-v-25-gradusnuyu-zharu-foto-18.htm>
  - <https://war.obozrevatel.com/ukr/okupanti-znischili-v-mangushi-masove-pohovannya-mariupoltsiv-vbitih-pid-chas-oblogi-u-2022-rotsi.htm>

**Novynarnia** — handwritten grave note "Дима, мама погибла 9 марта 2022 г. … Я маму похоронил возле детсадика" (22 March 2022).

**Focus.ua** — "Залезли в подвал, а там – 200 трупов": Andriushchenko on basements with 100–200 dead.
  - <https://focus.ua/voennye-novosti/521508-zalezli-v-podval-a-tam-200-trupov-sovetnik-gorodskogo-glavy-rasskazal-o-zhizni-v-mariupole>

**NV (nv.ua)** — 200 bodies under collapsed building; occupiers refused to clear rubble.
  - <https://nv.ua/ukraine/events/mariupol-okkupanty-otkazalis-razbirat-zavaly-pod-kotorymi-nashli-tela-200-pogibshih-50244654.html>

**Slovo i Dilo (slovoidilo.ua)** — over 100 bodies found under rubble of one Left-Bank building.
  - <https://ru.slovoidilo.ua/2022/06/27/novost/obshhestvo/mariupole-zavalami-odnogo-domov-obnaruzhili-bolshe-sotni-tel-pogibshix-sovetnik-mera>

**Ombudsman Ukraine (ombudsman.gov.ua)** — Commissioner statement: Mariupol reburial from house yards suspended; genocide framing.
  - <https://ombudsman.gov.ua/en/news_details/upovnovazhenij-mariupol-poterpaye-vid-trupnogo-smorodu-proces-perepohovannya-z-dvoriv-budinkiv-prizupineno-ce-genocid>

**Dnipro.tv** — Mykola Osychenko (Mariupol TV president) stated Illichivskyi morgue documented 87,000 dead (29 August 2022).

---

## 4. Occupation / Russian-State Sources (cross-reference only, labelled)

*The following are occupation administration or Russian-state controlled outlets. Used only for cross-reference or to document what the occupation itself recorded. Their framing is propaganda; their body-cause attributions are unreliable.*

**DAN / dan-news.ru** (Donetsk News Agency, occupation) — "Могилы во дворах, ненависть к нацистам и мечты о мире": courtyard graves in Mariupol residents' own words as reframed by occupation press.
  - <https://dan-news.ru/stories/mogily-vo-dvorah-nenavist-k-nacistam-i-mechty-o-mire.-kak-zhivut-i-o-chem/>

**URA.RU** (Russian state-adjacent) — photo feature: graves in Mariupol courtyards; 23rd microdistrict playground graves; church-yard burials.
  - <https://ura.news/articles/1036284256>

**mariupol-news.ru** — occupation city administration press service. Corporation for the Development of Donbas announcement of «Резиденция Селект» (16 January 2026). Also: МКР «Невский» build-out and Putin's 19 March 2023 visit («Тот самый микрорайон… посетил Путин»), cited in the Nevsky microdistrict case study.

**ТАСС / RIA Novosti / Lenta.ru** — used for cross-reference on demolition timelines; not cited as authoritative. ТАСС «ВСК МО РФ возвела в Мариуполе микрорайон Невский» (`tass.ru/obschestvo/20450945`) used to cross-check MoD-build scale figures.

**ППК «Военно-строительная компания» (vskmo.ru)** — the Russian MoD's own military-construction company; its site is the builder's self-account of МКР «Невский» (18 buildings / ≈1,880 apartments, «подарили мариупольцам»). Created by Указ Президента РФ №504, 18.10.2019 (<http://kremlin.ru/acts/bank/44754>). Cited in the Nevsky microdistrict case study.
  - <https://vskmo.ru/2023/12/08/doma-gde-poselilos-schaste/>

**«Единая Россия» (er.ru) / Аргументы и Факты (aif.ru)** — the launch-showcase record: Turchak's visit to the displaced Ponomaryov family (er.ru, 23.07.2022) and the «Новоселье по пропуску» move-in mechanism — ордер, pass-gated complex, «будет в собственности» (aif.ru, 01.12.2022). State-aligned framing; cited in the Nevsky microdistrict case study.
  - <https://er.ru/activity/news/edinaya-rossiya-pomozhet-s-zhilyom-mnogodetnoj-seme-iz-mariupolya-chej-dom-razrushili-vsu>
  - <https://aif.ru/society/people/novosele_po_propusku_kak_pogorelcy_v_mariupole_poluchayut_novye_kvartiry>

**Vedomosti (vedomosti.ru)** — mainstream Russian business daily, state-tolerated but not state-owned; reports on a 20.10.2025 government legislative-commission bill recognizing DNR/LNR/Zaporizhzhia/Kherson bezkhoz housing as republic/oblast/municipal property (the likely federal-level companion to №272-РЗ), quoting Rosreestr's 550,000-object regional figure (Aug. 2025) and a Federation Council senator's on-record claim that "all obstacles to recognition of ownership rights have been eliminated" — useful as a documented-official-rhetoric contrast against this project's own evidence of active barriers (border filtration, citizenship gates). Captured `scripts/287`.
  - <https://www.vedomosti.ru/society/articles/2025/10/21/1148414-beshozyainoe-zhile-v-novih-regionah-pereidet-v-gosudarstvennuyu-sobstvennost>

---

## 5. Human Rights Investigations and UN / International Bodies

**Human Rights Watch** — "Counting the Dead: Documenting Loss in Mariupol" (2024). Joint investigation with SITU Research and Truth Hounds. Satellite analysis of five cemeteries: ≥10,284 new burials (March 2022–February 2023); ≥8,034 excess deaths. Coordinates published for key sites including Митрополитська 98 (47.107290, 37.514850), Drama Theatre (47.09600, 37.54864). Evidence-destruction finding: "effectively erased the physical evidence at hundreds of potential crime scenes."
  - <https://www.hrw.org/feature/russia-ukraine-war-mariupol/counting-the-dead>
  - Russian-language version: <https://www.hrw.org/ru/feature/russia-ukraine-war-mariupol/counting-the-dead>

**Amnesty International** — Mariupol civilian harm documentation (general context).

**OHCHR / UN Human Rights Monitoring Mission in Ukraine** — civilian casualty and IHL documentation (general context).

**Uppsala Conflict Data Program (UCDP)** — estimated range of 27,000–88,000 fatalities in Mariupol, most civilians.

**UNOSAT — UN Satellite Centre** — WorldView-3 damage assessment, 12 May 2022. Assessed all five buildings at проспект Строителей 74–88 as "Moderate Damage" (Very High confidence). Datasets: CE20220223UKR, CC-BY-SA.
  - HDX portal: <https://data.humdata.org/organization/unosat>

---

## 6. Civil Society and OSINT Documentation

**mariupolRIP Telegram channel** ("Погибшие и Пропавшие, Мариуполь") — civilian documentation of deaths and burials street by street, 2022. Street-by-street records used for courtyard grave corroboration. Channel root captured `scripts/222`; cited generically (no message-level link pinned down) for the Stroiteley 74–88 burial records in the Stroiteley case study (MUP-CS-006). Full-channel text scan (5,961 messages, `scripts/302`–`304`, captured 2026-07-12, user-run per project convention since Telegram crawls are never run by Claude) read the channel directly as a primary source rather than through any spreadsheet's summary cells — surfaced 284 leads never cited elsewhere, 72 matched a property with an on-file seizure event. Cited citywide in the death-sites case study (MUP-CS-010). Empty-caption grouped photo albums (invisible to keyword classifiers) systematically swept 2026-07-21 (`scripts/399`/`404`/`405`, 66 albums/157 photos) plus a before/after-message technique exploiting the corpus's recurring caption-less-album + separate narrative-post pattern (`scripts/406`) — 13 new sites, folded into the Levoberezhny quarter case study (MUP-CS-012) among others.
  - <https://t.me/mariupolRIP>

**Azovstalskaya, 31 and Komsomolsky (Morskoy), 20 resident building chats** — two of this project's 28-chat deep-mined Telegram corpus (`src/mariupol_seizures/chat_buildings.py`), both sitting directly inside the Levoberezhny quarter (MUP-CS-012). Mined 2026-07-21 for casualty testimony, demolition timeline, and compensation-housing mechanics: precise MChS body-recovery counts matching the spreadsheet-derived tally, four new/partial casualty leads not yet formally loaded, a dated demolition timeline (Минстрой ДНР list published 24.10.2022 → cleared by December 2022), a district-administration quote confirming no reconstruction was planned as of 22.06.2023, and a residents' prosecutor-office pushback thread (06.09.2023). See `docs/case_studies/levoberezhny_quarter_demolish_and_abandon.md` for full quotes and message-level links.
  - <https://t.me/Azovstalskaya31> (`scripts/74`/`76`)
  - <https://t.me/invite_ZPLyCLn2RItmNWMy> (Komsomolsky/Morskoy 20, `scripts/139`)
  - Example: post 19765 (пр. Будівельників 138 burial record).
  - <https://t.me/mariupolRIP/19765>

**Wikimapia (historical layer) — Levoberezhny quarter non-residential loss cluster** — four Wikimapia historical-layer objects, user-supplied URLs, captured via headless-Chromium fetch (`playwright`) 2026-07-23. Together these fully identify all four non-residential losses named in the first Levoberezhny-quarter Putin-appeal testimony (two kindergartens, a school, a rehabilitation center for children with disabilities — see `docs/case_studies/levoberezhny_quarter_demolish_and_abandon.md`):
  - [wikimapia.org/13000772](https://wikimapia.org/#lang=en&lat=47.100739&lon=37.627455&z=17&m=w&tag=45694&show=/13000772/ru/) — "Разрушенный детский сад № 91 (ул. Ломизова, 7)", lists operating phone number +380 629 23-21-21. SHA-256 `6be181213e7018b8094de3761bcd88c09e10505f73d0a6f88a318846bb7d3d0c`.
  - [wikimapia.org/4076989](https://wikimapia.org/#lang=en&lat=47.100739&lon=37.627455&z=17&m=w&tag=45694&show=/4076989/ru/) — "Снесённая школа № 56 (Морской бул., 8)", opened 1967, demolished "after hostilities in the 2020s" per the object's own note. SHA-256 `00685c5e82376f33a62f3cf723b3873414200553494a62c6775e20feb0a2d6d6`.
  - [wikimapia.org/20922934](https://wikimapia.org/#lang=en&lat=47.100074&lon=37.630395&z=17&m=w&tag=45694&show=/20922934/ru/) — "Снесённый детский сад № 103 (Азовстальская ул., 19)". SHA-256 `a2e14605f8de72a689e23ce28deb687514ab47d07db84174e3f5dbc5abe148c3`.
  - [wikimapia.org/20923208](https://wikimapia.org/#lang=en&lat=47.100220&lon=37.632744&z=17&m=w&tag=45694&show=/20923208/ru/) — "Центр ранней социальной реабилитации детей-инвалидов (Азовстальская ул., 31б)". SHA-256 `12c907899890fd07badd990abab9ced3815b9265caabc1db91cb1ac03b2d5618`.

**Visicom API (ad hoc single-address query)** — direct geocode + footprint-polygon confirmation for Морской бул. 8 (Школа №56 candidate, feature_id `ADR3JSDC2ZCLBMHTWR`), not geoblocked, queried live 23.07.2026 (`api.visicom.ua`). Geocode SHA-256 `10b75607af77e98016ce8a78ab84856d0f99cccc94ad9e6b6064eba07d94a4ef`, footprint SHA-256 `58ba8ed90d7ed4d5ed56205bb3fe08003a25a4488910f0eceef4e64af1977591`. Confirms a real, distinctly-shaped structure at this address; does not independently verify the school identification itself, which rests on the Wikimapia/Google Earth sourcing above.

**Wikimapia API (`api.wikimapia.org`) — full box-query sweep of the Levoberezhny quarter** — 2026-07-23, `function=box` query over bbox `37.6260,47.0982,37.6345,47.1018` (the full quadrilateral, padded), authenticated with the project's registered `WIKIMAPIA_KEY` (`.env`; not geoblocked, but rate-limited per key — first key hit `code:1004 Key limit has been reached`, retried successfully with a second registered key). Returned every object Wikimapia has mapped inside the block in one page (`found: 47`, `count: 47`, no pagination needed) — box-query response captured verbatim, SHA-256 `4a3a8ee608e19710b096daef76068a0439f7536268fc59b550e7cfd41777d0aa`. 34/47 objects matched existing roster addresses (independent corroboration of the roster's addressing, once the pre-war→occupation street-rename mapping — Морской→Комсомольский, Меотиды→50 лет Октября — is applied). Five additional objects individually captured via headless-Chromium object-page fetch (see `docs/case_studies/levoberezhny_quarter_demolish_and_abandon.md` § "Full Wikimapia API sweep of the quarter" for full analysis):
  - [wikimapia.org/20922971](https://wikimapia.org/20922971/ru/x) — "Разрушенное нежилое здание (Морской бул., 18)" — a user comment names the tenants: «магазин и спортивный клуб "Юный лев"». SHA-256 `173a438a0bdd4ec952ecd9e49deac91f6e15fbda07e69b157debbb085596c15c`.
  - [wikimapia.org/20923224](https://wikimapia.org/20923224/ru/x) — "Орджоникидзевский районный центр занятости (Азовстальская ул., 31в)" — 5th civic/institutional non-residential loss identified. SHA-256 `98a5c6fd0fabf1bf28265924ca0be528d78fc057a08ef69a8f62463ae860cf80`.
  - [wikimapia.org/18434552](https://wikimapia.org/18434552/ru/x) — "Снесённый жилой дом (Азовстальская ул., 19/1)" — new residential lead, not yet on roster. SHA-256 `b69109c3b7c8a5068348cfd813db5a523ec85f964ef5181336796a57eb2330a6`.
  - [wikimapia.org/18434564](https://wikimapia.org/18434564/ru/x) — "Снесённый жилой дом (Азовстальская ул., 19/2)" — new residential lead, not yet on roster. SHA-256 `a1a1c66f6c148e2d91b7b306ba754a778123e6dba4e76f3464ded04b2edb4c6b`.
  - [wikimapia.org/30333792](https://wikimapia.org/30333792/ru/x) — "Разрушенная котельная" (demolished district boiler house) — address-less utility-infrastructure loss. SHA-256 `03c8db692cc711539589ef3e0d524c288c92eb9ac22953071ba2bcb0ae4cc46e`.

**Visicom API — full footprint sweep of the Levoberezhny quarter** — 2026-07-23, `scripts/424_visicom_footprint_sweep_quarter.py` (RUN=C source, non-geoblocked, keyed via `.env` `VISICOM_KEY`, Claude-runnable per `src/mariupol_seizures/osint/sources/visicom.py`'s own module annotation). Queried all 52 roster addresses plus 6 newly identified non-residential/off-roster objects; 58 total, 0 outright failures. **Reliable**: all 52 roster buildings, plus Азовстальская 19/1 (`ADR3JSDC2Z23DCHQHX`), 19/2 (`ADR3JSDC2Z23JY8HPP`), Комсомольский 18 (`ADR3JSDC2Z9TKTG9KY`) — genuine distinct Polygon footprints, name-matched. **Not reliable, do not use**: Азовстальская 31б and 31в both false-matched to plain "31" (`ADR3JSDC2Z23UPTWG2`); Школа №56 false-matched via this sweep to an unrelated address ("70", `ADR3JSDC2Z9T0H4RHW`) — the correct school footprint remains the earlier ad hoc lookup (feature `ADR3JSDC2ZCLBMHTWR`, see the Visicom entry above). Also surfaced an unresolved discrepancy: the roster's own "Азовстальская 19" geocoded to a 4th sub-address, "19/2а" (`ADR3JSDC2Z23CHR80K`), not plain "19" — see `docs/case_studies/levoberezhny_quarter_demolish_and_abandon.md` § "Visicom footprint sweep" for full detail. All 58 raw geocode/feature responses captured regardless of match quality (capture-before-judge).

**mrpl.city — Left Bank rehabilitation center address confirmation** — pre-war Ukrainian local news article, resolves the Wikimapia-vs-user-identification conflict over the rehab center's address in favor of бульвар Меотиды, 20-а (occupation-era 50 лет Октября 20А). Captured verbatim 2026-07-23, SHA-256 `cd901f2163df229e8a1bc9113c4f9b22309c858353aed3abe8da2f69608c510e`.
  - <https://mrpl.city/news/view/kak-detyam-s-invalidnostyu-poluchit-sovremennuyu-psihologicheskuyu-i-fizicheskuyu-reabilitatsiyu-v-mariupole>

**Kindergarten №103 address cross-check (WebSearch, 2026-07-23)** — corrected the earlier Wikimapia-sourced address for Детский сад №103 «Аленький цветочек» / «Червоненька квіточка». Three independent contemporary business directories agree on Морской бульвар, 9 (occupation-era Комсомольский 9), not Азовстальская 19 as Wikimapia's crowd-sourced tag claimed:
  - <https://mariupol.kitabi.ru/firms/detskiy-sad-103-alenkiy-cvetochek-komsomolskiy-bulvar-9>
  - <https://ua.spravbiz.ru/mariupol/company-detskii-sad-no-103-alenkii-tsvetochek/>
  - <https://little.com.ru/kindergarten/1146.html>

**memorial.ua** — Ukrainian-language biographical memorial site (civilian and children's obituaries). 3,320 pages crawled 2026-07-12 (`scripts/305`–`307`); the site's own robots.txt names and disallows `ClaudeBot` specifically (alongside GPTBot/CCBot/etc.) while general browsers are permitted, so the crawl was run from the project user's own machine, not by Claude. Yielded 464 confirmed Mariupol deaths, 7 matched to a seized property, including the flagship просп. Ленина (Мира), 127 finding (Ганна Гулінська, Володимир Роменський) in the death-sites case study (MUP-CS-010). Required a small hand-verified Ukrainian→Russian street-name translation table (10 entries, each checked against the property spine) since the site writes in Ukrainian while the spine's address inventory is built from Russian-language occupation sources.
  - <https://memorial.ua>
  - <https://memorial.ua/obituaries/civilians/hulinska-hanna-5417>
  - <https://memorial.ua/obituaries/civilians/romenskyi-volodymyr-7067>
  - <https://memorial.ua/obituaries/civilians/kfedorova-nadiia-12510>

**victims.memorial** — victim memorial register, 2022.

**Маріуполь зараз / Mariupol Now** (Petro Andriushchenko, adviser to the Mayor of Mariupol) — official statements on body counts, rubble clearance, exhumations, Nakhimov school building-over-graves, Manhush destruction. Primary source for scale claims attributed to the city's official-in-exile.
  - Telegram channel: <https://t.me/mariupolrada>

**MRPLmap / Mariupol Destruction and Victims Fund** — пр. Мира 127: ≥45 named victims, hidden trench at Starokrymske tied to rubble clearance (satellite chronology 2022–2024).

**Civil Voices Museum (civilvoicesmuseum.org)** — Rinat Akhmetov Foundation. Eyewitness testimony archive.
  - "Поховали чоловіка у дворі під турніком" (man buried under pull-up bar in courtyard).
    <https://civilvoicesmuseum.org/stories/%22pohovali-cholovika-u-dvori-pid-turnikom%22>
  - "Того дня було дуже багато загиблих. Друга я поховав у дворі школи."
    <https://civilvoicesmuseum.org/stories/togo-dnya-bulo-duzhe-bagato-zagyblyh-druga-ya-pohovav-u-dvori-shkoly>

**Donetsk Regional State Administration memorial (dn.gov.ua)** — victim memorial database; used for named courtyard burials (e.g. Сергій Калина, Андрій Галушко, Марія Паскаль at пр. Металургів).

**Bellingcat** — Mariupol property registration documentation, including "[RENAMED · per Bellingcat — underlying Mariupol decree not yet captured]" for the registry-to-resale case study (MUP-CS-004).
  - <https://www.bellingcat.com>

**OSINT4Ukraine / Project Mariupol** (Hague-based, 70+ analysts) — collaborating organisation; no specific article cited, general corroboration.

**ZraDomir (zradomir.com.ua)** — Ukrainian collaborator-accountability database; cited in the Lenina 104–110 case study.
  - <https://zradomir.com.ua/offenders/polishchuk-andrii>

**VKontakte** — one-off occupation-official wall post, cross-referenced in the master dossier.
  - <https://vk.com/wall-61542146_14776>

**YouTube / youtu.be** — occupation-published and resident-published footage, individually verified per video (title/caption matching found unreliable in this project's own review; every citation confirmed against the full file).
  - example: <https://youtu.be/n-_gv-AmbEM>

---

## 7. Satellite and Geospatial

**Maxar Technologies** — satellite imagery of Vynohradne trench cemetery (22–29 March 2022); Manhush cemetery expansion (April 2022); Starokrymske expansion. Via Axios, NBC, NPR, Space.com.

**Planet Labs** — satellite imagery of Mariupol cemetery expansion (AP Special Projects investigation).

**Google Maps API** — geocoding pipeline for address normalisation.

**UNOSAT WorldView-3** — see §5 above.

**pastvu.com** — archival street photography (e.g. проспект Нахимова 82, 1991–92), cited in the Nakhimova 82 exhibit's before/after chips.
  - <https://pastvu.com/p/948634>

**Yandex Maps / Panorama** — 2012 street-level imagery of pre-destruction buildings, cited in the Stroiteley case study (MUP-CS-006).
  - <https://yandex.com/maps>

**Google Earth (historical imagery gallery)** — 2019-08-08 dated historical satellite/imagery layer, used to identify Ломизова 7 as Детский сад №91 (Kindergarten №91), previously misclassified as residential on the Levoberezhny quarter roster (MUP-CS-012, `scripts/417`). WebFetch cannot render Google Earth's JS-heavy viewer directly (confirmed 2026-07-23 — page returns only a browser-support warning, no renderable content); identification is user-supplied, not independently machine-verified against the imagery.
  - <https://earth.google.com/web/@47.09967686,37.62822495,30.64202654a,621.99799661d,35y,0h,0t,0r/data=ChYqEAgBEgoyMDE5LTA4LTA4GAFCAggBOgMKATBCAggASg0I____________ARAA>

---

## 8. Legal and Institutional Frameworks

**Rome Statute, Article 8(2)(a)(iv)** — unlawful, wanton, and large-scale destruction and appropriation of property not justified by military necessity.

**Rome Statute, Article 8(2)(b)(viii)** — transfer of population into occupied territory.

**Fourth Geneva Convention, Article 53** — prohibition of destruction of property without military necessity.

**Hague Convention (1907), Article 46** — protection of private property under occupation.

**Berkeley Protocol on Digital Open Source Investigations** — standards for digital evidence in human rights investigations. Published by the UN Office of the High Commissioner for Human Rights.
  - <https://www.ohchr.org/sites/default/files/2022-04/OHCHR_BerkeleyProtocol.pdf>

**Council of Europe Register of Damage for Ukraine (RD4U)** — restitution claim categories A3.1, A3.3, A3.6. Claim form requirements.
  - <https://www.registerofdamage.org>

**ECtHR Grand Chamber, *Ukraine and Netherlands v. Russia* [GC], 9 July 2025** — first international court judgment establishing Russia's responsibility for the full-scale invasion; Article 1 Protocol 1 (property) violations on a "systematic administrative practice" / "coherent strategy" basis.
  - Application Nos. 8019/16, 43800/14, 28525/20.

**ECtHR, *Loizidou v. Turkey*** — Northern Cyprus property-deprivation precedent cited throughout.

**DNR Law 66-РЗ** «О некоторых вопросах признания права собственности на жилые помещения в Донецкой Народной Республике» (21.03.2024) — enabling framework for the ownerless-property pipeline; Article 5(3)(a) requires personal appearance with Russian passport to prevent ownerless declaration.
  - Full text (Head of DNR official site): <https://glavadnr.ru/doc/zakony/66rz.pdf>

**DNR Law (без номера-РЗ, №459-IIНС) от 30.06.2023** «Об особенностях регулирования имущественных и земельных отношений на территории Донецкой Народной Республики в переходный период» — the master property/land-conversion predicate law implementing ФКЗ №5-ФКЗ ст.21 DNR-wide; ст.2 ч.3 is the textual basis for the "Ukrainian-era title formally preserved, practically stripped via the ownerless registry" argument.
  - denis-pushilin.ru: <https://denis-pushilin.ru/doc/zakony/zII459.pdf>
  - Raw store: sha256 `9a134303c2b7dd20c692fdcd2d60bb09b857b5d0a2f4927d1a9a4aef4986916f`; text-native, no OCR needed; found via `scripts/247` archive survey, 2026-07-05

**Закон ДНР №14-РЗ от 13.10.2023** «О порядке управления и распоряжения собственностью Донецкой Народной Республики» — general disposal-procedure statute for DNR-owned property; likely enabling statute under the individual no-tender developer-lease распоряжения.
  - denis-pushilin.ru: <https://denis-pushilin.ru/doc/zakony/14rz.pdf>
  - Raw store: sha256 `a26757263c5435fbe7012e3c0e23688ed1344c0b97f31c9dd3e20d5dd9f4f4be`; text-native, no OCR needed; found via `scripts/247` archive survey, 2026-07-05
  - Federal publication mirror: <http://publication.pravo.gov.ru/document/8000202403220001>

**Federal Constitutional Law ФКЗ-4** №4-ФКЗ от 15.12.2025 — abolishes the court stage of the ownerless-property pipeline in the "new regions"; registry inclusion replaces court judgment as the title-conferring act. Mariupol was the Roskadastr pilot; court filings dropped to zero by mid-2026.
  - Official federal portal (full text): <http://publication.pravo.gov.ru/Document/View/0001202512150024>

**Federal Constitutional Law ФКЗ-5** №5-ФКЗ от 04.10.2022 «О принятии в Российскую Федерацию Донецкой Народной Республики…» — constitutional channel for annexation; the predicate enabling ЕГРН application to Mariupol.
  - Official federal portal (full text): <http://publication.pravo.gov.ru/document/0001202210050005>

**Постановление Правительства РФ №2565 от 31.12.2022** «Об утверждении Правил предоставления субсидий из федерального бюджета акционерному обществу "ДОМ.РФ"…» — the «льготная ипотека 2%» decree: DOM.РФ-administered subsidy covering the gap between market rates and a ≤2%/year mortgage for buying/building housing in DNR/LNR/Zaporizhzhia/Kherson, open to any RF citizen. In force from 1 Jan 2023.
  - Official federal portal (landing): <http://publication.pravo.gov.ru/Document/View/0001202301030011>
  - Official federal portal (signed PDF, 46pp, image-only scan): <http://publication.pravo.gov.ru/file/pdf?eoNumber=0001202301030011>
  - Raw store: OCR'd via `.venv312`/pytesseract, `data/parsed/decree_2565_ipoteka_ocr.txt`; captured `scripts/246` (2026-07-04)

**Постановление Правительства РФ №2166 от 15.12.2023** — amends the DOM.РФ mortgage-subsidy decree family (incl. №2565); per secondary reporting mainly retools Far-Eastern/Arctic mortgage limits — not yet confirmed whether it touches the DNR/LNR/Zaporizhzhia/Kherson provisions specifically. Landing page captured only; full text not yet read.
  - Official federal portal (landing): <http://publication.pravo.gov.ru/document/0001202312150019>

### Primary legislation — two-property-systems and court-docket exhibits

**Указ Президента РФ №26 от 09.01.2011** — base decree prohibiting foreign nationals and foreign-controlled entities from owning land in designated border territories.
  - Official Kremlin: <http://www.kremlin.ru/acts/bank/32451>

**Указ Президента РФ №201 от 20.03.2020** — extends the №26 border-territory list to include 11 Crimean districts and 8 Sevastopol urban districts; the Crimea proving-ground instrument.
  - Official Kremlin: <http://www.kremlin.ru/acts/bank/45294>

**Федеральный закон №218-ФЗ «О государственной регистрации недвижимости»** — принят Государственной Думой 03.07.2015, одобрен Советом Федерации 08.07.2015. Устанавливает ЕГРН как единственный государственный реестр недвижимости; основание формулы «запись в ЕГРН исключает признание объекта бесхозяйным». Предикат Шага 2 правовой генеалогии в экспонате two-property-systems.
  - Официальная публикация (PDF, government.ru): <http://static.government.ru/media/acts/files/0001201507140007.pdf>
  - Страница акта: <http://government.ru/docs/all/102812/>
  - Raw store: `data/raw/464bbcecb948e00cfbb539251517bd3189ba049c08a12fa7c8bf9a897032f3de.pdf` (SHA-256: 464bbcec…32f3de, захвачено 2026-06-30)

**Указ Главы ДНР №290 от 16.08.2023** «Об особенностях внесения в ЕГРН сведений… и выполнения комплексных кадастровых работ…» — DNR-level mandate transferring cadastral records into ЕГРН; the operative instrument for Step 2 of the legal genealogy.
  - DNR state normative-acts portal: <https://gisnpa-dnr.ru/npa/0001-290-20230816/>

**Информационное сообщение администрации Мариуполя** «Вниманию владельцев недвижимого имущества» — city portal news item containing the key passage: ЕГРН record forecloses ownerless declaration. Informational notice, not a formal normative act.
  - Mariupol gosuslugi (primary URL): <https://mariupol.gosuslugi.ru/dlya-zhiteley/novosti_990.html>

**Указ Президента РФ №1103 от 24.12.2024** «Об особенностях осуществления государственной регистрации юридических лиц, имеющих место нахождения на территориях Донецкой Народной Республики, Луганской Народной Республики, Запорожской области и Херсонской области, и прав таких юридических лиц на недвижимое имущество» — restricts (until 1 Jan 2026, extended to 2028 by №145) state registration of: (a) legal entities in DNR/LNR/Zaporizhzhia/Kherson whose founders/controllers are linked to "unfriendly" (sanctioning) foreign states; (b) such entities' real property rights in Rosreestr — without special permission from a regional collegial body (appointed by the head of each occupied oblast). Permission refused if registration threatens "defense or state security." Note: the original text (this PDF) covers only legal entities; Указ №145 (below) expanded the same base decree to ban individual "unfriendly-state" citizens' property-rights registration — all three form one escalating chain.
  - Official publication (pravo.gov.ru): <https://publication.pravo.gov.ru/document/0001202412240001>
  - Captured: `data/raw/54bb13ed3a51fa75b4561b87446e442300806c5fcd02fe0362a36199d28ccb49.pdf` (SHA-256 verified, 4 pp.)

**Указ Президента РФ №145 от 14.03.2025** — extends the №1103 prohibition to 01.01.2028.
  - Official Kremlin: <http://www.kremlin.ru/acts/bank/51725>

**Указ Президента РФ №1006 от 29.12.2025** — prohibits notarial certification of powers of attorney for the same group; closes the POA escape-hatch. Kremlin/pravo.gov.ru URL not confirmed in this pass; GARANT mirror: <https://base.garant.ru/413383874/>

**Закон ДНР №134-РЗ от 05.12.2024** «Об особенностях регулирования жилищных отношений… в переходный период» — first ФКЗ-4 implementing act.
  - Federal portal: <http://publication.pravo.gov.ru/document/8000202412060002> (card/metadata; full-text PDF not recovered in this pass)

**Закон ДНР №240-РЗ от 22.12.2025** «О внесении изменений в статьи 1 и 2 Закона ДНР «Об особенностях регулирования жилищных отношений в ДНР в переходный период»» — amends Law №134-РЗ; extends social-tenancy (социальный найм) protections for tenants who lost housing to hostilities until 1.1.2028; bypasses RF Housing Code Arts. 49/57 means-test/queue requirements; **not part of the bezkhoz/ownerless pipeline** (governs municipal social-tenancy track, not private ownership) — not cited in the two-property-systems exhibit. Signed Пушилиным 22.12.2025; in force from date of official publication.
  - DNR Народный Совет laws index (confirmed 2026-06-30): <https://xn--80ahqgjaddr.xn--p1ai/zakony-narodnogo-soveta-dnr-rf/>
  - Raw store: `data/raw/ccb850f1c8f3f932ca0ef9fdfea02b4d40ca805259215cff41b4caa8ff42dc53.pdf` (3 pp., 380 983 bytes, SHA-256 verified)

**Закон ДНР №275-РЗ от 17.04.2026** — extends Law №134-РЗ (amends Arts. 1–2); full text on DNR legislative portal.
  - DNR legislative portal: <https://xn--80azg.xn--80ahqgjaddr.xn--p1ai/2026-04-17/275-rz-o-vnesenii-izmenenij-v-stati-1-i-2-zakona-donetskoj-narodnoj-respubliki-ob-osobennostyakh-regulirovaniya-zhilishchnykh-otnoshenij-v-donetskoj-narodnoj-respublike-v-perekhodnyj-period/>

**Закон Украины №417-VIII «Об особенностях осуществления права собственности в многоквартирном доме»** — Ukrainian co-ownership framework; Article 4 (shared property) + Land Code Article 42(5) (land beneath building = shared).
  - Verkhovna Rada register (confirmed 2026-06-30): <https://zakon.rada.gov.ua/laws/show/417-19#Text>

**ГПК РФ, Глава 33** «Признание движимой вещи бесхозяйной и признание права собственности на бесхозяйную недвижимую вещь» — the особое производство procedural chapter applied in all 2,694 Mariupol court cases. Official pravo.gov.ru URL not confirmed; legal mirror: <https://legalacts.ru/kodeks/GPK-RF/razdel-ii/podrazdel-iv/glava-33/>

**Федеральный закон №262-ФЗ от 22.12.2008** «Об обеспечении доступа к информации о деятельности судов в Российской Федерации» — mandates depersonalization of published court records (removal of street addresses); explains the `<адрес>` redaction in all 2,694 case cards.
  - Official Kremlin: <http://www.kremlin.ru/acts/bank/28599>

**Дела №2-4974/2025 и №2-239/2026, Жовтневский районный суд Мариуполя** — worked-case examples cited in the court-docket exhibit. Case cards geoblocked outside Russia; do not fetch directly. Queue for VPS capture:
  - Case c33e847b: <https://mar-zhovt--dnr.sudrf.ru/modules.php?name=sud_delo&srv_num=1&name_op=case&case_uid=c33e847b-2167-4ecd-b0d6-471090c7efd3>
  - Case aed20aff: <https://mar-zhovt--dnr.sudrf.ru/modules.php?name=sud_delo&srv_num=1&name_op=case&case_uid=aed20aff-85c4-4069-90ec-8c1c453164c0>

**Закон ДНР №272-РЗ** (17 April 2026) «О признаках бесхозяйного имущества в отношении жилых помещений...» — repeals and replaces №66-РЗ; eliminates the court-petition requirement entirely for housing bezkhoz designation. Municipal title now arises automatically ("в силу закона") on the day a unit enters the municipal property registry — explicitly framed as "во внесудебном порядке" (extrajudicial). Verified word-for-word (три признака test, 10-day/30-day/door-notice timeline, forced entry with police, Статья 8 ч.1/ч.3 reversal-and-reimbursement clauses, 2030 sunset, ЕГРН carve-out, outbuildings list, №52-РЗ cross-reference) against a user-supplied Telegram summary (@mrpl_besxozxata/7910/94267). Likely the specific implementing statute for the court-conveyor shutdown this project has tracked only as an inferred data signature. Source: <https://glavadnr.ru/doc/zakony/272rz.pdf>. **[CAPTURED] + READ** — `scripts/285`, sha256 `284cb8d5c7da86...`. Cited in `docs/legal_mechanisms_review.md`.

**Закон ДНР №66-РЗ** (21 March 2024) «Об особенностях выявления, использования и признания права муниципальной собственности... на жилые помещения, имеющие признаки бесхозяйного имущества...» — REPEALED by №272-РЗ (24.04.2026 per user-supplied claim). Primary text now captured for the first time despite extensive prior citation throughout this project; confirms the predecessor procedure required the authorized body to petition a **court** for a decision recognizing municipal ownership — the key structural difference from its court-free replacement. Source: <https://glavadnr.ru/doc/zakony/66rz.pdf>. **[CAPTURED] + READ** — `scripts/285`, sha256 `d6d96362ae9cc1...`. Cited in `docs/legal_mechanisms_review.md`.

**Закон ДНР №269-РЗ** (03 April 2026) «Об особенностях распоряжения жилыми помещениями, имевшими признаки бесхозяйного имущества... а также условиях и порядке предоставления компенсации гражданам Российской Федерации...» — the distribution/compensation-eligibility law downstream of №272-РЗ. Compensation is gated to RF citizens only; 3-year filing deadline; incomplete paperwork is grounds for denial; "equivalent housing" is same-locality-preferential, not same-district; fractional/доля co-owners who don't jointly file lose their share of compensation; служебное жилье (official housing) can be carved from the same bezkhoz stock for federal/local officials until 1 January 2028; amends and confirms the exact title/date of the previously citation-only Закон №141-РЗ (18.12.2024), adding a 3-year anti-resale ban on compensation housing. Source: <https://glavadnr.ru/doc/zakony/269rz.pdf>. **[CAPTURED] + READ** — `scripts/285`, sha256 `0424524d235dfb...`. Cited in `docs/legal_mechanisms_review.md`.

**Закон ДНР №141-РЗ** (18 December 2024) «О поддержке граждан, жилые помещения которых утрачены в результате боевых действий на территории Донецкой Народной Республики» — the base compensation-housing law amended by №269-РЗ above. Gates compensation to RF citizens who have written-renounced any other DNR-era support measure; Art. 2 §4 makes the choice explicitly mutually exclusive — receiving this law's housing benefit forfeits eligibility for any other DNR support measure (e.g. a cash payout), and vice versa; requires the applicant to sign a formal "обязательство об отчуждении" surrendering the lost unit and its land to municipal ownership as a precondition of compensation; caps eligible unit size at 33m² (single)/42m² (couple)/18m² per person for 3+ families, +9m² max variance, regardless of the lost dwelling's actual size; identifies the underlying federal accession statute as №5-ФКЗ (4 October 2022); transfers the compensation unit via the general Russian privatization mechanism (Закон РФ №1541-I); includes a false-information clawback clause. Source: <https://glavadnr.ru/doc/zakony/141rz.pdf>. **[CAPTURED] + READ 2026-07-09** — `scripts/285`, sha256 `dfa458c4a9965b...`. **Independently re-captured 23.07.2026** from `publication.pravo.gov.ru` (official federal legal-publication portal, not geoblocked, fetched directly), sha256 `7f436096b6c35bba4935ce034314424e002e946a4d88373ed74a8fc1b8e494b4` — cross-source corroboration, different hash/rendering, same text; this copy had already independently entered the raw store years earlier via an unrelated Telegram-media OCR capture. This is the "закон 141" residents call predatory (грабительский) in the third Levoberezhny-quarter Putin-appeal video (`t.me`/YouTube `c1nmNcv5FRw`, 28.02.2025) as the law withdrawn/amended by №161-РЗ (below). Cited in `docs/legal_mechanisms_review.md` and `docs/case_studies/levoberezhny_quarter_demolish_and_abandon.md`.

**Закон ДНР №161-РЗ** (21 February 2025) «О внесении изменений в Закон Донецкой Народной Республики "О поддержке граждан..."» — the first amendment to №141-РЗ above, signed Д.В. Пушилин. Rewrites Art. 2 §1/§3 of the base law but keeps its core exclusivity mechanism intact; republishes the compensation-decision appendix forms including the formal written renunciation-of-cash-payout form (Приложение 2) and the obligation-to-transfer-ownership form (Приложение 3). This is the "закон 161" the same video describes as the replacement law under which residents must apply for a cash payout first and forfeit housing eligibility once it lands — confirmed accurate against the primary text. Source: `publication.pravo.gov.ru`, not geoblocked, fetched directly 23.07.2026, sha256 `c78a3a1d18c46f9df085566a1527f1df8f00af6aee983f9acc3521172b396fad`. A second, later amendment (24 October 2025, minor technical extension of coverage to individual houses/жилые дома, not the mechanism residents describe) also captured, sha256 `e729dc63e9d332eabc6ecc19d0e3f34e5fb37fc17c227b9c71cb8a4bd314e5b5`. Cited in `docs/case_studies/levoberezhny_quarter_demolish_and_abandon.md`.

**Закон ДНР №137-РЗ** (13 December 2024) — amendment to №66-РЗ Статья 8, establishing priority allocation of bezkhoz-designated housing to a named list of Russian federal security, military, and law-enforcement agencies (Defense Ministry, MVD, FSB, EMERCOM, Rosgvardia, Foreign Intelligence Service, Federal Protective Service, Customs, Justice Ministry, Bailiffs, FSIN, Prosecutor's Office, Investigative Committee, Rosfinmonitoring, Judicial Department), with explicit permission to deviate from normal housing-space allocation norms for this group. The most direct primary-source textual finding for a Rome Statute art. 8(2)(b)(viii) argument in this project to date. Source: <https://glavadnr.ru/doc/zakony/137rz.pdf>. **[CAPTURED] + READ** — `scripts/285`, sha256 `3d96600ae824ac...`. Cited in `docs/legal_mechanisms_review.md`.

---

## 9. Academic and Analytical Literature

**Arendt, Hannah** — *Eichmann in Jerusalem: A Report on the Banality of Evil* (1963). Bureaucratic procedure enabling mass atrocity — theoretical frame for the dossier.

**Derrida, Jacques** — *Archive Fever: A Freudian Impression* (1996). Compulsive documentation as self-incrimination — "archive fever" frame.

**Bauman, Zygmunt** — *Liquid Modernity* (2000). Moral distance through bureaucratic procedure.

**Agamben, Giorgio** — *State of Exception* (2005). Occupation law creating zones outside ordinary legal protection.

**CEPA (Centre for European Policy Analysis)** — toponymy/renaming analysis, December 2024. Cited in the de-Ukrainianisation panel of the master dossier.

**SOC ACE / RIFO Database** — "Looting Mariupol" report (RP35). Named in the §13 sources section of the master dossier.

**ARTnews** — museum looting documentation, Mariupol. Cited in de-Ukrainianisation panel.

**UK Ministry of Defence** — open-source intelligence update, 18 July 2025. Cited for education / language-replacement dimension in de-Ukrainianisation panel.

**HRW "Education under Occupation"** (June 2024) — Order №467 (curriculum replacement). Cited in de-Ukrainianisation panel.

**Leibniz-IfL / KonKoop VisLab** — geocoding the Mariupol ownerless lists; flagged as potential collaboration/data-exchange partner.

**Dossier Center** — beneficiary-matching research; flagged as potential collaboration.

**Alexey Kovalev (Medium)** — the project author's own essay on the settler-colonial framing of the invasion; cited in the master dossier's "about" section.
  - <https://medium.com/@alexey__kovalev/russias-invasion-of-ukraine-is-an-ultraviolent-settler-colonial-project-a2f3c1ff5873>

---

## 10. Street and Legal Reference

**uk.wikipedia.org** — "проспект Будівельників" (street history; 1970s Left-Bank workers' avenue).
  - <https://uk.wikipedia.org/wiki/%D0%9F%D1%80%D0%BE%D1%81%D0%BF%D0%B5%D0%BA%D1%82_%D0%91%D1%83%D0%B4%D1%96%D0%B2%D0%B5%D0%BB%D1%8C%D0%BD%D0%B8%D0%BA%D1%96%D0%B2_(%D0%9C%D0%B0%D1%80%D1%96%D1%83%D0%BF%D0%BE%D0%BB%D1%8C)>

**uk.wikipedia.org** — "Масові вбивства в Маріуполі."
  - <https://uk.wikipedia.org/wiki/%D0%9C%D0%B0%D1%81%D0%BE%D0%B2%D1%96_%D0%B2%D0%B1%D0%B8%D0%B2%D1%81%D1%82%D0%B2%D0%B0_%D0%B2_%D0%9C%D0%B0%D1%80%D1%96%D1%83%D0%BF%D0%BE%D0%BB%D1%96>

**base.garant.ru** — mirrored occupation decree texts (ГКО №56, №172).

**ЕГРЮЛ / egrul.nalog.ru** — Russian legal-entity register; INN/OGRN lookups for developer SPVs (СЗ-1 ПОРФИР ИНН 9310009271; ООО «РКС-НР»; МК ГРУПП; and others). **Open gap (2026-06-30):** no working rusprofile/checko/EGRUL deep-link for СЗ-1 ПОРФИР found from this environment (rusprofile search 404s); the Stroiteley case study's citation of this entity is unlinked pending a verified URL.

**opensanctions.org** — structured sanctions/ownership database, sourced from EGRUL for Russian entities. Used 2026-07-20 to confirm ФСБ России listed as owner of ФГКУ «Войсковая часть 1297» (ИНН 9310007740), the recipient unit in the Чёрноморская 18 / Ленина 101 case study (MUP-CS-011). Directly accessible from this environment (unlike rupep.org/rusprofile.ru below).
  - <https://www.opensanctions.org/entities/ru-inn-9310007740/>

**rupep.org** — Ukrainian corporate/PEP-ownership database; user-cited as a second source for the FSB-ownership finding above, but returns a Cloudflare challenge to this project's fetch environment and could not be independently re-read. Cite opensanctions.org as the verified basis; note this one as user-supplied-but-unconfirmed.
  - <https://rupep.org/ru/company/47035>

**rusprofile.ru / checko.ru / egrul-base.ru** — Russian corporate-registry aggregators. rusprofile.ru returns 403 from this environment; checko.ru and egrul-base.ru are accessible and confirm ФГКУ «Войсковая часть 1297»'s registration particulars (registered 22.05.2023, ОКВЭД 84.22) but list the founder/учредитель field as access-restricted under 129-ФЗ rather than stating FSB explicitly in retrievable page content.
  - <https://checko.ru/company/fgku-v-ch-1297-1239300004866>
  - <https://www.egrul-base.ru/company/1239300004866/>
  - <https://www.rusprofile.ru/id/1239300004866> (403, unverified)

**mariupol.gosuslugi.ru — Мариупольский городской совет «Решение» documents** — the city-council decision family (distinct from Администрация постановление decrees elsewhere in this catalogue), 339 documents 2024–2026, systematically captured `scripts/383`, classified by subject `scripts/387`, and read through in full (2026-07-20). The bulk is routine governance (budgets, statutes, appointments, awards, ТОС boundaries); the property-dispositive minority — the subject of MUP-CS-011 rung [F2] — splits into: transfers of specific ex-bezkhoz real estate to named military/security units (в/ч 1297/76835), bulk residential transfers to the federal treasury via Росимущество (I/13-7, I/14-4), transfers of already-municipal non-residential/land to DNR-republican bodies, and «включение в Перечень компенсационных» inclusions operationalizing Закон ДНР №141-РЗ (see `docs/legal_mechanisms_review.md` rungs [F2]/[G]). The enabling instrument is Решение №I/8-1 (19.03.2024).
  - Listing root: <https://mariupol.gosuslugi.ru/glavnoe/gorodskoy-sovet/?cur_cc=6980>
  - Named-unit transfer (Решение №I/5-5, 12.03.2026): <https://mariupol.gosuslugi.ru/netcat_files/multifile/252/1721/Reshenie_I_5_5_ot_12.03.2026.pdf>
  - Federal-treasury bulk transfer (Решение №I/13-7, 10.06.2026, 11 apts): <https://mariupol.gosuslugi.ru/netcat_files/multifile/252/1912/Reshenie_ot_10.06.2026_1_13_7.pdf>
  - Federal-treasury bulk transfer (Решение №I/14-4, 23.10.2025, 11 apts): <https://mariupol.gosuslugi.ru/netcat_files/multifile/252/1533/Reshenie_I_14_4_ot_23.10.2025.pdf>

**mariupol.gosuslugi.ru — АГО Мариуполь compensation-housing distribution & queue lists** — the Администрация городского округа Мариуполь official record of the 2026 compensation-housing mass-distribution campaign (rung [G]): which municipal apartments were distributed, plus the standing квартирная очередь. Located 2026-07-21 on the "Квартирная очередь" page; capture script `scripts/392` (user-run, Russia-routed). The primary-source counterpart to the crowd-sourced reallocation ledger (`scripts/391`).
  - Queue page: <https://mariupol.gosuslugi.ru/dlya-zhiteley/poleznye-materialy/kvartirnaya-ochered/>
  - Распределение жилья от 21.07.2026: <https://mariupol.gosuslugi.ru/netcat_files/602/8217/Raspredelenie_zhil_ya_ot_21.07.2026.xlsx>
  - Распределение жилья от 27.05.2026 (stage 1): <https://mariupol.gosuslugi.ru/netcat_files/602/8696/Raspredelenie_zhil_ya_ot_27.05.2026.pdf>
  - Квартирная очередь 27.05.2026: <https://mariupol.gosuslugi.ru/netcat_files/602/7469/Ochered_Sayt_27.05.2026.xlsx>

**наш.дом.рф object records 65280, 69427, 69749, 69751, 70142, 70147** (Резиденция Селект / Резиденция II, проспект Строителей 74–88) — **open gap (2026-06-30):** the portal's per-object pages/API return HTTP 403 (WAF block) from this environment; only the registry root (<https://наш.дом.рф>) is linked in the Stroiteley case study pending a working per-object URL.

**наш.дом.рф object 54284** («Дом на Нахимова» / Chernomorsky 1B) — resolves directly with a browser user-agent (unlike the 403-blocked objects above): <https://xn--80az8a.xn--d1aqf.xn--p1ai/сервисы/каталог-новостроек/объект/54284>. Live sold-out % and marketing renders. Cited in Exhibit A (Nakhimova 82).

**Постановление Правительства РФ №2565** (31 December 2022) — federal 2% subsidized-mortgage decree for DNR/LNR/Zaporizhzhia/Kherson; confirms no residency restriction. Source: <http://publication.pravo.gov.ru/Document/View/0001202301030011> (landing), <http://publication.pravo.gov.ru/file/pdf?eoNumber=0001202301030011> (signed PDF, OCR'd `scripts/246`, 2026-07-04). Cited in Exhibit A (Nakhimova 82).

---

## 11. Testimony and Witness Records (primary, cited in exhibits)

**Oleg Tsarov Telegram (t.me/olegtsarov/9754)** — 27 December 2023 post, resident testimony regarding Нахимова 82: demolition-to-mortgage-sale pattern. SHA-256: 9a2264f7…891691. (Leg 0 in Exhibit A.)

**@nmrpl/39594** (3 October 2025) — Mariupol occupation city-district administration channel post: the replacement building on the Nakhimova 82 / Chernomorsky 1B site wins a bronze diploma at an architecture competition; head of city-planning and architecture Наталья Клочкова praises the redevelopment on the record, naming the address "Нахимова". Source: <https://t.me/nmrpl/39594>. Cited in Exhibit A (Nakhimova 82, award leg).

**Mariupol 24 TV Telegram (t.me/mariupol24tv/104461)** — 3 October 2025 post, Klochkova / ARKHITAVR award citation, occupation administration naming "Нахимова, 82" and describing the ambition to transform Mariupol into "a modern comfortable Russian city." SHA-256: 8b8b6834…86fbb2. (Leg 6 in Exhibit A.)

**@mariupol_nash/42486** (19 July 2023) — official DNR social-support explainer, forwarded on the channel, naming Нахимова 82 residents by address among those whose "property rights… are strictly observed" and directing them to district УТСЗН offices for Постановление №175 compensation (compensational housing on-site, or 35,000 RUB/m² cash). Source: <https://t.me/mariupol_nash/42486>. Cited in Exhibit A (Nakhimova 82, arithmetic section).

**@morgun_ov/3474** (29 September 2023) — Mariupol occupation administration head Oleg Morgun's own account of a meeting with Нахимова 82 residents: confirms the demolished building's replacement is under construction for mortgage sale ("не для них"), acknowledges residents' fear of being left without compensational housing, and promises compensational housing "in other new developments" — i.e. off-site, contrary to Постановление №175 §5.3's own on-site requirement. Source: <https://t.me/morgun_ov/3474>. Cited in Exhibit A (Nakhimova 82, arithmetic section).

**ssaniaworld Telegram (t.me/ssaniaworld/3348)** — resident testimony: 73-year-old Russian-passport-holder whose apartment (Ленина 133, кв.19) was sealed despite utility payments; daughter (owner, in Minsk) had granted power of attorney; apartment declared "ownerless" after 2024 ruling on apts 2/19/20/33.

**Erashova family (AP Special Projects, December 2022)** — buried two children aged 5 and 7 (killed 9 March 2022) in a courtyard; returned July 2022 to find bodies already removed to a warehouse.

**Yaroslav Dema** — gravedigger, Meduza 10 June 2022; named in burial records at пр. Победы 32/42 and проспект Строителей 160.

**«МАРИУПОЛЬ! КРАШМАШ СНОСИТ ЗНАМЕНИТУЮ МНОГОЭТАЖКУ НА МЕТАЛЛУРГОВ!»** (YouTube, <https://www.youtube.com/watch?v=RutXOUDzP_s>, uploader Игорь Семенов, uploaded 14.12.2022) — independent third-party footage, on-screen text names both the demolition contractor (KrashMash) and the address (Металлургов, 47) in the same frame; description dates start of works to 10.12.2022. SHA-256: `05d4297e1c7d43a5bc69089a2fe104cd99f8ea98d21840958d39499ad3aad7bb`. Cited in `case-study-troianda-metallurgov.html` / `-ru.html`.

**Mariupol Destruction and Victims Map** (<https://www.mariupoldestruction.com>) — published citywide victims spreadsheet («Поименный список жертв» / "List of victims by name", Google Sheets TSV export, 4,515 rows), captured 03.07.2026, SHA-256: `3b10d33f56cd47496a6f9a095ff487c818418f3acc724e61901f9cd009149ff5`. Eight named residents of Металлургов, 47 recorded killed Feb–Mar 2022, cross-referenced against Telegram `t.me/mariupolRIP` (posts 19075, 19202, 25434, 30852, 44164, 44185, each individually captured, SHA-256 `6411cecc61dc…` through `28c6f781abe2…`) and `memorial.ua/obituaries/civilians/kfedorova-nadiia-12510` (SHA-256 `4c533ad8d4dc…`). Two courtyard burial sites documented: Фёдорова Надежда (buried beside the building in a rug, reburial status unknown) and Харакоз Наталья Георгиевна (common grave in the courtyard, later exhumed and reburied at Starokrymske cemetery). Full table in `docs/case_studies/troianda_m_demolition_challenge.md`, cited in `case-study-troianda-metallurgov.html` / `-ru.html`. Captured via `scripts/239_capture_metallurgov47_casualty_record.py`; loaded to `corroboration` (kind `civilian_casualty`, property_id 4529) via `scripts/240_load_metallurgov47_casualty_record.py` (run by the user, not Claude, per project convention). Re-pulled citywide, directly from the live Google Sheet, 2026-07-12 (`scripts/299`, 4,517 rows, SHA-256 `17e0dd2c821dfecd01d1f11a499eb4f72cdf585cf9eb1e4520eb4efeaa9dc7a8`) and classified for informal-burial language (`scripts/300`) as the base layer of the citywide three-source sweep in the death-sites case study (MUP-CS-010) — 275 confirmed informal burials, cross-referenced against every seizure event on the property spine, not just new-build objects.

**"Как р-н 'Стадион' встречает Новый 2025 год на своих котлованах от домов. Мариуполь"** (rutube.ru, video id `a2b592ea8c3a6b60c71c7a103fc2b804`, <https://rutube.ru/video/a2b592ea8c3a6b60c71c7a103fc2b804/>, uploader "Hear Mariupol", 74 subscribers, published 31.12.2024, duration 3:43) — resident group video-appeal to Putin recorded on their own building foundations. Not geoblocked (yt-dlp fetch succeeded directly). Captured via `scripts/418_capture_stadion_district_newyear_video.py` (user-run, RUN=U); Whisper-transcribed (medium, ru) via `scripts/332` against `source_type=osint_rutube_video`, transcript SHA-256 `2f04e21f2dee17633f8b3f598ecf67f811054f185ab1aebbdb4dc0e66d9736d6`. States "48 домов, два детских сада, школа и реабилитационный центр для детей инвалидов" demolished 2022; names Ломизова 9, Азовстальская кв.59, Комсомольский 20; states residents denied housing-queue placement over fire-lost documents; gives residents' own reading of the Азовстальская→Тульский renaming as intended to "лишить нас жилья на старом месте." Cited in `docs/case_studies/levoberezhny_quarter_demolish_and_abandon.md`.

**"БОМЖИ СО СТАДИОНА ОБРАТИЛИСЬ К ПУТИНУ. МАРИУПОЛЬ. НАШИ ДНИ"** (YouTube, video id `JsGi1qQ1C9w`, <https://www.youtube.com/watch?v=JsGi1qQ1C9w>, uploader "Просто Треш", published 19.01.2025, duration 82s, 52 views at capture) — resident video-appeal to Putin: building demolished, residents made homeless, new-build apartments reported going to mortgage sale rather than displaced-resident allocation. Description explicitly names "район Стадион, бульвар Меотиды, бульвар 50 лет Октября" — independent confirmation the "Стадион" district name refers to this quarter (two of its four boundary streets named directly). Not geoblocked. Captured via `scripts/420_capture_stadion_bomzhi_putin_appeal.py` (user-run, RUN=U; also captures the full yt-dlp metadata JSON as a second primary artifact, since the description text itself is evidence). Whisper-transcribed (medium, ru) via `scripts/332`, transcript lineage `osint_video_transcript` → `1ad5c3a3bb45…`, text copy `data/reports/video_transcripts/1ad5c3a3bb45.txt`. States "48 многоквартирных домов, три детских сада и школа" demolished; quotes mayor Моргун О.В. ("Олег Валерьевич") directly telling residents compensation housing will not be built and they will instead be issued "бесхозные" (ownerless-registry) apartments. Cited in `docs/case_studies/levoberezhny_quarter_demolish_and_abandon.md`.

**"Обращение жильцов района 'Стадион', г. Мариуполя к президенту РФ В.В. Путину 28.02.2025"** (YouTube, video id `c1nmNcv5FRw`, <https://www.youtube.com/watch?v=c1nmNcv5FRw>, uploader "Mariupol_journal", published 28.02.2025, duration 146s, 13 views at capture) — third independent "Стадион" resident appeal. Not geoblocked. Captured via `scripts/422_capture_stadion_third_putin_appeal.py` (user-run, RUN=U). Whisper-transcribed (medium, ru) via `scripts/332`, sha256 `67e46060a078db50d717c2a4c461981b8bc7605e71b61db3a6fe9802d2c303cb` (video) → `55c5a06ab0957973f55ab75147259d241d4d2e4e799bc20399b5e95775e991b4` (transcript). States citywide figures (362 buildings demolished / 71 rebuilt citywide, 18,000 homeless citywide — not quarter-specific, uncorroborated elsewhere); references an uncaptured prior presidential decree ordering a 1 April housing-provision report; names "закон 141" (withdrawn) and its replacement "закон 161" (a cash-payout-first mechanism that forfeits housing eligibility once accepted — neither law independently verified/captured). Cited in `docs/case_studies/levoberezhny_quarter_demolish_and_abandon.md`.

**"Жители города Мариуполь, проживающие на Левом берегу, район Стадион"** (YouTube, video id `18iOWPkcs9I`, <https://www.youtube.com/watch?v=18iOWPkcs9I>, uploader "ДАША СЕРЫЙ КАРДИНАЛ", published 20.06.2024 — earliest of the four "Стадион" appeals captured, duration 198s, 32 views at capture) — fourth independent resident appeal; title itself names "Левый берег" (left bank) directly. Not geoblocked. Captured via `scripts/422_capture_stadion_third_putin_appeal.py` (user-run, RUN=U). Whisper-transcribed (medium, ru) via `scripts/332`, sha256 `3921dc70691955d137e200a962461abcd2321c1ebb681ac2e315ce375ad19771` (video) → `143a83ec165c38c53926a8f02cb921bf13918cd53ceef9516459aa0e7f4b761d` (transcript). States all 48 buildings were demolished without the required structural-damage assessment being provided to residents on request; states land was transferred to municipal ownership as of 11.08.2023 with no stated legal basis (uncorroborated, genuine gap); cites Постановление 175 and 61.1 setting compensation at 45,000 RUB/m² against a stated 120,000 RUB/m² market rate — both decree numbers independently corroborated by the unrelated monitored-channel scan in `memory/monitored_scan_findings_2026-07-21.md` (Решение №61-1, Mariupol city council compensation-distribution procedure, adopted 13.02.2026). Cited in `docs/case_studies/levoberezhny_quarter_demolish_and_abandon.md`.

**@mariupol_left Telegram channel** (left-bank/Левобережный район district channel, <https://t.me/mariupol_left>) — captured via `scripts/50_crawl_telegram_channels.py` (user-run, MTProto/Telethon, per project convention), scanned via `scripts/419_scan_mariupol_left_channel.py` against the general seizure-lifecycle term bank plus a quarter-specific street filter (213/1033 flagged messages matched one of this quarter's four boundary streets). Three individual posts cited directly in `docs/case_studies/levoberezhny_quarter_demolish_and_abandon.md`:
- [t.me/mariupol_left/56029](https://t.me/mariupol_left/56029) (06.08.2024) — activist Сания Денисова relays a Moscow/Mariupol prosecutor review of "Стадион" district land allocation for mortgage construction.
- [t.me/mariupol_left/62424](https://t.me/mariupol_left/62424) (05.09.2025) — magistral highway project (Приказ №186-од, Минстрой ДНР, 14.08.2025) through the quarter's SE corner; names all four boundary streets; claims Azovstal stadium demolition (origin of the "Стадион" district name) — **not corroborated in the primary decree's extractable text** (checked 23.07.2026, see below); still open.
- [t.me/mariupol_left/62038](https://t.me/mariupol_left/62038) (07.08.2025) — plaintiff's own account of the final first-instance court rejection in the Азовстальская-renaming case (14 hearings across 3 courts; Mariupol prosecutor's office reversed its supporting position at the final hearing).

**t.me/russkiy_mariupol/10245** (<https://t.me/russkiy_mariupol/10245>) — "Гавань"/"Слободка" mixed-use redevelopment master-plan visualizations, linked from @mariupol_left/62424 as the project the №186-од highway supports. Checked via public preview (`?embed=1`, resolves directly, not geoblocked) but not yet independently mirrored into the raw store as its own primary artifact.

**Приказ №186-од (Минстрой ДНР, 14.08.2025)** — magistral highway/interchange decree, "Об утверждении документации по планировке территории, предусматривающей размещение линейного объекта «Участок улично-дорожной сети — планируемая улица общегородского значения, проходящая по территории МК «Азовсталь» с примыканием к бульвару 50 лет Октября и формированием транспортной развязки вблизи Таганрогского залива»" (<https://minstroy-dpr.gosuslugi.ru/doc/prikaz-minstroya-dnr-ot-14-08-2025-%E2%84%96-186-od-ob-utverzhdenii-dokumentaczii-po-planirovke-territorii-po-planirovke-territorii-predusmatrivayushhuyu-razmeshhenie-linejnogo-obekta-uchastok-ul/>). Independent corroboration in Ukrainian press (Telegraf.com.ua, 05.09.2025, <https://news.telegraf.com.ua/ukraina/2025-09-05/5919988-mariupol>, confirms decree number/date/route verbatim). Минстрой ДНР's own portal (minstroy-dpr.gosuslugi.ru) is **geoblocked** (connection failure, tested directly 23.07.2026) — the document PAGE itself was read via ad hoc `WebFetch` (allowed directly, not geoblocked for page reads); the 6 file bodies (decree + 4 ППТ/ПМТ volumes, ~63 MB total) required the user's Russia-routed VPN. **Captured 23.07.2026** via `scripts/421_capture_minstroy_186od_highway_decree.py` (user-run):
- Document page: SHA-256 `661b7acee6ac07ffd5d82735de187358ec5e7fa13dfd8715c9fc4c2d4a479d62`.
- Decree PDF (image-based, OCR'd, signed Министр В.Н. Дубовка): SHA-256 `6e56ba53fac326cedae00b3a1050cfd88e1562914d78304712f862901444785c`.
- Том 1 (ППТ, утверждаемая часть, text-layer): SHA-256 `da8494143ca13fd284c86f0cae2a36be7584a9a2247a7a48a05ea09ef211358e`.
- Том 2 (ППТ, обосновывающие материалы, text-layer): SHA-256 `02d49ef05e6f243b8cad334fd0a5247da7f2e070ae0db5614fcf22b374f2233e`.
- Том 3 (ПМТ, утверждаемая часть, text-layer): SHA-256 `e429ffa08e36d514f24cdb36d7b70553832a4ecd12e426b33156cfac7e23d900`.
- Том 4 (ПМТ, обосновывающие материалы, text-layer): SHA-256 `4bf639a32fb7a6904a26a646ddfb0a09a43a7b3e6b8ac129e32287de150bbe49`.

Developed by ФАУ «Единый научно-исследовательский и проектный институт пространственного планирования Российской Федерации», commissioned by the federal Министерство строительства и ЖКХ Российской Федерации, tracing to распоряжение Правительства РФ от 21.04.2023 №1019-р and постановление Правительства РФ от 22.12.2023 №2255 — federal, not just DNR-local, planning authority. Full findings in `docs/case_studies/levoberezhny_quarter_demolish_and_abandon.md` §2.

**"Мариуполь , Ломизова 15"** (YouTube, video id `KtkZFcUcEKQ`, <https://www.youtube.com/watch?v=KtkZFcUcEKQ>, uploader "Серёга" (small personal channel, 819 views at capture), published 26.05.2022, duration 421s/~7min) — pre-demolition walkthrough of the still-standing-but-destroyed quarter; title names Ломизова 15 (roster building STREET:ломизова|15) directly. Not geoblocked. Captured via `scripts/430_capture_lomizova15_and_meotidy_demolition_videos.py` (user-run, RUN=U; also captures the full yt-dlp metadata JSON and ffmpeg stills every 30s). Ломизова 15 is independently confirmed as the filming location of the 1988 Soviet film **"Little Vera"** (Маленькая Вера, <https://en.wikipedia.org/wiki/Little_Vera>) per kp.ua, "Для съемок 'Маленькой Веры' выбрали мариупольскую хрущевку," Артём Маслаков и Елена Шинкаренко, 09.11.2012, <https://kp.ua/culture/365363-dlia-semok-malenkoi-very-vybraly-maryupolskuui-khruschevku> (checked resolves 23.07.2026) — names "пятиэтажка на улице Ломизова, 15" (then-Zhdanov outskirts) directly as the film crew's rented-apartment set. Cited in `docs/case_studies/levoberezhny_quarter_demolish_and_abandon.md`.

**"Мариуполь. Б-р Меотиды. Снесённый квартал. Магазин "Мариуполь", 2023г."** (YouTube, video id `cjlmLUJ4NX4`, <https://www.youtube.com/watch?v=cjlmLUJ4NX4>, uploader "Destruction in Ukraine on the map" / @MariupolDestruction, published 05.10.2023, duration 65s) — post-demolition ground-view walkthrough of the same razed block, naming the "Магазин Мариуполь" landmark already independently referenced in the building-chat corpus. Not geoblocked. Captured via `scripts/430_capture_lomizova15_and_meotidy_demolition_videos.py` (user-run, RUN=U; ffmpeg stills every 10s). Cited in `docs/case_studies/levoberezhny_quarter_demolish_and_abandon.md`.

**mariupol.yaspravka.com — School №56 address confirmation** (<https://mariupol.yaspravka.com/shkola-56>, checked resolves 24.07.2026) — Mariupol business directory listing giving Школа №56's address as "Комсомольский бульвар, 8." Used to correct a roster-misclassification: this is the SAME building_id as the roster's existing (residential-tagged) BOULEVARD:комсомольский|8, not a distinct un-inserted building — the property was a school, misclassified `residential_spine` by `scripts/417`'s polygon sweep, same failure mode as the quarter's other two kindergartens. Corrected via `scripts/431_load_quarter_nonresidential_and_new_leads.py`. Cited in `docs/case_studies/levoberezhny_quarter_demolish_and_abandon.md`.

**domophoto.ru** (<https://domophoto.ru/cities/32/>, Mariupol city index, checked resolves) — Russian building-photography database with structured per-building metadata (address, Soviet standard-design series/project code, floor count, approximate construction date, demolished/standing status); mirrors photobuildings.com. robots.txt disallows `/list` (the per-street listing pages) for all user-agents, not a bot-specific carve-out — captured from the user's own terminal, throttled, descriptive UA string (see `scripts/427_crawl_domophoto_mariupol.py` header for the full reasoning). Citywide crawl: 128 streets, 809 building-detail pages. For the Levoberezhny quarter specifically: 11 in-roster matches confirm 4 Soviet standard-design series codes (1-464Д-83 at Ломизова 9/11/13, 1-437 at 50 лет Октября 20, 1-439А-41 at Комсомольский 30/36) plus floor counts at Ломизова 17 (14, a 3rd independent confirmation) and 50 лет Октября 4/6/8 + Комсомольский 34 (5 each). Folded into `scripts/412_build_reconstruction_data.py`'s `MANUAL_FLOOR_OVERRIDES`. Cited in `docs/case_studies/levoberezhny_quarter_demolish_and_abandon.md`.

**@astrapress/108112** (ASTRA, independent exiled Russian outlet, <https://t.me/astrapress/108112>, dated 26.03.2026, checked resolves) — "Жители оккупированного Мариуполя почтили память погибших соседей в котловане, который остался на месте их дома": residents of the "Стадион" district (Levoberezhny quarter, MUP-CS-012) memorialize 16 people who died in a single building entrance/stairwell in March 2022, filmed at the foundation pit where the building stood; cross-references this project's own already-captured January 2025 Putin-appeal video and the Азовстальская → «Проспект Тульский» renaming. Captured via `scripts/432_capture_astrapress_108112_memorial_video.py` (user-run, RUN=U) — message metadata JSON, 14.7s video, 2 ffmpeg stills. Building/entrance not yet identified from the video; not merged into any casualty tally. Cited in `docs/case_studies/levoberezhny_quarter_demolish_and_abandon.md`.

**«Обращение к Президенту» VK video** (post `-211186281_167139`, video `-211186281_456247432`, dated 1–2 January 2025) — direct video appeal to Vladimir Putin from displaced Mariupol residents standing at the foundations of demolished buildings (Куприна 3/5/19/21/33, пр. Ленина 127/129, Карла Либкнехта 90/92/90Б, Зелинского 17А/19А/21/21А, Строителей 72А/76/80, 60 лет СССР 14, Шевченко 91/93/361, Солнечная 1, Котляревская 6/8). States directly that displaced residents are to be resettled into apartments seized via the bezkhoz ("ownerless") registry — asserted to have identifiable owners and heirs — and quantifies the compensation-housing shortfall (362 buildings demolished citywide, only 71 compensation units built, no further compensation construction, a below-market 45,000 RUB/m² cash-out for those who fall off the queue). Captured 2026-07-16 (`osint_vk_flagged_post_video`, sha `188ddb5f2ac83f2b…`); transcribed via Whisper the same session (two passes — the first, sha `5de28e044ff13c73…`, is the more reliable transcription of the key "бесхозные квартиры" sentence; the second "corrected" pass, sha `cd763cfb13760def…`, introduced a transcription regression on that line and should not be relied on for that sentence). Cited in `docs/legal_mechanisms_review.md` §[A3].

---

*Export generated June 2026. This file covers all sources referenced in the project's exhibits, case studies, and research catalogues. Occupation-administration and Russian-state sources are labelled as such; they are used for cross-reference or self-incrimination evidence, not as authoritative independent sources.*
