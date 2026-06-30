# Mariupol Urbicide Project — Source List

All sources used across the project's research: burial sites catalogue, case studies, stakeholder network, legal analysis, and general investigation. Grouped by source family. Occupation/Russian-state sources are labelled as such where they appear; they are used for cross-reference only.

---

## 1. Occupation Primary — Decrees and Administrative Documents

**Распоряжение ГКО ДНР №56** (29 September 2022) — demolition list naming проспект Строителей д.78, 80, 88, 112. Text mirrored at base.garant.ru. Confirmed absent from нпа.днронлайн and denis-pushilin portals (internal operational order).

**Распоряжение ГКО ДНР №172** (18 April 2023) — demolition list naming проспект Строителей д.72, 117. Text mirrored at base.garant.ru.

**DNR head land-allocation orders (Пушилин), Nos. 390–394** — sequential grants to СЗ-1 ПОРФИР (ИНН 9310009271) for проспект Строителей 74–88. Captured in project pipeline `data/raw/` with SHA-256 chain-of-custody.

- Decree portal: <https://denis-pushilin.ru/acts/>
- Normative acts portal: <https://нпа.днронлайн.рф>
- Regional law portal: <https://pravo.region80.ru>

**Mariupol ownerless-property decrees (постановления о бесхозяйном имуществе)** — 968 decrees captured from the Mariupol городское управление юстиции portal; signatories include Кольцов А.В. (652), Моргун О.В. (156), Дмитриев А.В. (55).

**Mariupol ownerless registry (ФКЗ-4 master list)** — 12,948-entry registry-as-title list across four Mariupol district courts.

**Demolition decrees (Mariupol municipal administration)** — 20 decrees captured + MinStroy register 637 rows (525 Mariupol buildings).

**Russian federal damage/reconstruction tracker (XLSX)** — 1,941 buildings, contractor + destruction-% map. Via ЕИСЖС / наш.дом.рф.
- <https://наш.дом.рф>

**ЕИСЖС new-build object register** — objects 65280, 69427, 69749, 69751, 70142, 70147 («Резиденция Селект», «Резиденция II» and related developments on проспект Строителей).

**Occupation court dockets — 4 Mariupol district courts** (Жовтневый, Приморский, Орджоникидзевский, Ильичевский). 2,694 особое производство (бесхозяйная вещь) cases captured; see `docs/STATS.md` for current event counts. Portal addresses captured at time of crawl; geoblocked for direct access.

**DNR "Supreme Court" case 33-2575/2025** (13.11.2025, reporting judge Гуридова Н.Н.) — appellate ruling upholding denial of the 60-resident Troianda-M / Metallurgov 47 collective claim; also cited re: DNR State-Committee Directive No. 56 in Case Study III (Stroiteley). Captured `scripts/223` (run from user's VPS, geoblocked portal).
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
- "Карта разрушений" (29 January 2024) — resident told her building was "sold to a private developer" and she was owed nothing; used in Case Study III and the master dossier.
  - <https://zona.media>

**Novaya Gazeta Europe** — used for context on occupation administration.
- «Доступное захваченное жильё» (22 February 2024) — resident denied compensation after her building was demolished and the lot bought by a private developer. Cited in Case Study III (Stroiteley); captured `scripts/222`.
  - <https://novayagazeta.eu/articles/2024/02/22/dostupnoe-zakhvachennoe-zhile>

---

## 3. Ukrainian and International Journalism

**Associated Press / AP Special Projects** — anchor for citywide burial scale.
- "Russia scrubs Mariupol's Ukraine identity, builds on death" (Michael Biesecker et al., December 2022). ~10,300 new graves; Starokrymske cemetery satellite analysis; "building upon a city of death" framing; Erashova family case. Cited in Case Study III (Stroiteley); captured `scripts/222`.
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

**mariupol-news.ru** — occupation city administration press service. Corporation for the Development of Donbas announcement of «Резиденция Селект» (16 January 2026).

**ТАСС / RIA Novosti / Lenta.ru** — used for cross-reference on demolition timelines; not cited as authoritative.

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

**mariupolRIP Telegram channel** ("Погибшие и Пропавшие, Мариуполь") — civilian documentation of deaths and burials street by street, 2022. Street-by-street records used for courtyard grave corroboration. Channel root captured `scripts/222`; cited generically (no message-level link pinned down) for the Stroiteley 74–88 burial records in Case Study III.
  - <https://t.me/mariupolRIP>
  - Example: post 19765 (пр. Будівельників 138 burial record).
  - <https://t.me/mariupolRIP/19765>

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

**Bellingcat** — Mariupol property registration documentation, including "[RENAMED · per Bellingcat — underlying Mariupol decree not yet captured]" for Case Study II.
  - <https://www.bellingcat.com>

**OSINT4Ukraine / Project Mariupol** (Hague-based, 70+ analysts) — collaborating organisation; no specific article cited, general corroboration.

---

## 7. Satellite and Geospatial

**Maxar Technologies** — satellite imagery of Vynohradne trench cemetery (22–29 March 2022); Manhush cemetery expansion (April 2022); Starokrymske expansion. Via Axios, NBC, NPR, Space.com.

**Planet Labs** — satellite imagery of Mariupol cemetery expansion (AP Special Projects investigation).

**Google Maps API** — geocoding pipeline for address normalisation.

**UNOSAT WorldView-3** — see §5 above.

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

**DNR Law 66-РЗ** (enabling framework for the ownerless-property pipeline).

**Federal Constitutional Law ФКЗ-4** (Russian annexation instrument conferring "DNR" law status).

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

---

## 10. Street and Legal Reference

**uk.wikipedia.org** — "проспект Будівельників" (street history; 1970s Left-Bank workers' avenue).
  - <https://uk.wikipedia.org/wiki/%D0%9F%D1%80%D0%BE%D1%81%D0%BF%D0%B5%D0%BA%D1%82_%D0%91%D1%83%D0%B4%D1%96%D0%B2%D0%B5%D0%BB%D1%8C%D0%BD%D0%B8%D0%BA%D1%96%D0%B2_(%D0%9C%D0%B0%D1%80%D1%96%D1%83%D0%BF%D0%BE%D0%BB%D1%8C)>

**uk.wikipedia.org** — "Масові вбивства в Маріуполі."
  - <https://uk.wikipedia.org/wiki/%D0%9C%D0%B0%D1%81%D0%BE%D0%B2%D1%96_%D0%B2%D0%B1%D0%B8%D0%B2%D1%81%D1%82%D0%B2%D0%B0_%D0%B2_%D0%9C%D0%B0%D1%80%D1%96%D1%83%D0%BF%D0%BE%D0%BB%D1%96>

**base.garant.ru** — mirrored occupation decree texts (ГКО №56, №172).

**ЕГРЮЛ / egrul.nalog.ru** — Russian legal-entity register; INN/OGRN lookups for developer SPVs (СЗ-1 ПОРФИР ИНН 9310009271; ООО «РКС-НР»; МК ГРУПП; and others). **Open gap (2026-06-30):** no working rusprofile/checko/EGRUL deep-link for СЗ-1 ПОРФИР found from this environment (rusprofile search 404s); Case Study III's citation of this entity is unlinked pending a verified URL.

**наш.дом.рф object records 65280, 69427, 69749, 69751, 70142, 70147** (Резиденция Селект / Резиденция II, проспект Строителей 74–88) — **open gap (2026-06-30):** the portal's per-object pages/API return HTTP 403 (WAF block) from this environment; only the registry root (<https://наш.дом.рф>) is linked in Case Study III pending a working per-object URL.

---

## 11. Testimony and Witness Records (primary, cited in exhibits)

**Oleg Tsarov Telegram (t.me/olegtsarov/9754)** — 27 December 2023 post, resident testimony regarding Нахимова 82: demolition-to-mortgage-sale pattern. SHA-256: 9a2264f7…891691. (Leg 0 in Exhibit A.)

**Mariupol 24 TV Telegram (t.me/mariupol24tv/104461)** — 3 October 2025 post, Klochkova / ARKHITAVR award citation, occupation administration naming "Нахимова, 82" and describing the ambition to transform Mariupol into "a modern comfortable Russian city." SHA-256: 8b8b6834…86fbb2. (Leg 6 in Exhibit A.)

**ssaniaworld Telegram (t.me/ssaniaworld/3348)** — resident testimony: 73-year-old Russian-passport-holder whose apartment (Ленина 133, кв.19) was sealed despite utility payments; daughter (owner, in Minsk) had granted power of attorney; apartment declared "ownerless" after 2024 ruling on apts 2/19/20/33.

**Erashova family (AP Special Projects, December 2022)** — buried two children aged 5 and 7 (killed 9 March 2022) in a courtyard; returned July 2022 to find bodies already removed to a warehouse.

**Yaroslav Dema** — gravedigger, Meduza 10 June 2022; named in burial records at пр. Победы 32/42 and проспект Строителей 160.

---

*Export generated June 2026. This file covers all sources referenced in the project's exhibits, case studies, and research catalogues. Occupation-administration and Russian-state sources are labelled as such; they are used for cross-reference or self-incrimination evidence, not as authoritative independent sources.*
