# Case Study — Death Sites, Ad-Hoc Graves and New Construction

**Accession:** MUP-CS-010 · Modality X — cross-cutting (victim overlay) · [REGISTRY.md](REGISTRY.md)

**Update, 2026-07-12:** Extended from a single-source, new-build-only cross-
reference to a three-source, spine-wide sweep. See "Case 8 — Citywide
systematic sweep" below for the new methodology and findings; Cases 1–7
(the original EISZhS-specific deep dives) are unchanged and gained
independent corroborating addresses on several of their streets in the
process (noted inline where relevant).

**Update, 2026-07-12 (cont.):** Further extended to treat collapse-
entombment (bodies never recovered from beneath a collapsed building) as
the same category of unexhumed-remains evidence as courtyard/yard burial —
Case 8's classifier had explicitly excluded this language as a distinct,
untracked category. See "Case 9 — Collapse-entombment" below.

**Cross-referencing named-victim burial/death and collapse-entombment
records against (a) the 91 EISZhS (nash.dom.rf) new-construction objects
[Cases 1–7, original method], (b) every seizure_event on the property
spine — demolition, registry inclusion, ownerless designation, reclaim,
reallocation, expropriation [Case 8, 2026-07-12 sweep], and (c) that same
seizure_event spine again for collapse-entombment specifically [Case 9,
2026-07-12 sweep].**

**Source file (Cases 1–7):** `Погибшие и Пропавшие на Карте Разрушений_Deceased and
Missing on the Damage Map.xlsx` (4,506 records, 4,256 with parseable
address; 641 with grave-location addresses after filtering formal
cemeteries/hospitals).

**Method (Cases 1–7):** keyword+house-number matching against
`data/parsed/eisghs_mariupol_objects.jsonl` (91 objects). Two passes:
(A) "death_place" / "residence" of victim vs eisghs address; (B)
burial location (explicit or inferred-courtyard) vs eisghs address.

---

## Case 1 — prosp. Stroiteley 70 → "Rezidentsiya II" d.70B
**Exact address match: two deaths recorded at the predecessor building**

| Attribute | Detail |
|---|---|
| ЕИСЖС id | 65280 |
| New-build name | "Резиденция II" |
| New-build address | г. Мариуполь, пр-кт Строителей, д.70Б |
| Status | **Commissioned** (occupied) |
| Developer | СЗ-1 ПОРФИР (ИНН 9310009271) |
| Land order | №125, 24.04.2026, signed Д.В.Пушилин, cadastral 93:37:0010406:5954 |

**Recorded deaths at пр-кт Строителей, д.70:**

1. **Олейникова Раиса Степановна** — "Угорела в подвале дома"
   (died of CO/smoke inhalation sheltering in the building's basement).
   No burial recorded.
   Source: https://t.me/mariupolRIP/26710

2. **"Михаил" (surname unknown)** — "добровольно ушел из жизни"
   (suicide). Resident of пр. Строителей 70 кв. 47.
   Body removed by occupation service "Орфей".
   Source: https://t.me/mariupolRIP/12460

The new building "Резиденция II" at д.**70Б** is the standard
occupation notation for a new structure on the cleared lot of the
predecessor at д.70. The same cadastral block (Черемушки microdistrict,
41,678 m²) is also the development zone for eisghs objects 66544 and
66594 (same land order №125).

Separately, at **Строителей 66** (same developer zone), a person was
buried "в садике рядом с домом", cause: авиаудар (airstrike). At
**Строителей 138**, two family members died ("у себя дома от попадания
снаряда", the second dying later from the trauma), courtyard burial.

---

## Case 2 — ul. Zelinskogo: ZhK "Nakhimovsky" and ZhK (PORFIR) construction zone

**New-build objects on ул. Зелинского** (8 objects, all
`under_construction`):

| eisghs id | Developer | RPD |
|---|---|---|
| 66986–66989 | СЗ КОРПОРАЦИЯ СМУ-5 (ИНН 9310017508) | №93-000049 |
| 71399, 71400 | СЗ КОРПОРАЦИЯ СМУ-5 | №93-000083 |
| 71846, 71848, 71850 | СЗ-1 ПОРФИР (ИНН 9310009271) | №93-000086/087/088 |

СМУ-5's declaration №93-000049 (the 121-page RPD read in this session)
declares 4 МКД ("ЖК Нахимовский") on cadastral parcel 93:37:0010101:1959
(15,865 m²), allocated by **Договор аренды земельного участка №138**
(27.06.2025, DNR as public-owner lessor — a lease mechanism not present
in `dnr_land_orders.jsonl`, which is decree-based only).

### Deaths and graves recorded on ул. Зелинского

**д.98 — shell hit the basement, multiple fatalities:**

| Name | Cause | Notes |
|---|---|---|
| Бондарев Даниил Артемович | "снаряд залетел в подвал" | "возможно похоронены во дворе" |
| Коляда Антонина Сергеевна | "снаряд залетел в подвал" | "возможно похоронены во дворе" |
| Жильцова Светлана Витальевна | "прилёта снаряда в подвал" | — |
| Лукьянов Александр Владимирович | "прилёта снаряда в подвал" | — |
| Бельченко Элла Владимировна | cardiac arrest (учитель школа 18) | lived/died д.98 кв.19 |
| Марченко Татьяна Константиновна | — | д.98А кв.8 |

Sources: t.me/mariupolRIP/1334, /36581, /9918; t.me/mariupolRIP/50909

A separate victims.memorial entry (**Барабуль Гаврила**, from Сартана,
died "в подвале многоэтажки на улице Зелинского") states: **"15 марта
в 13:00 попал танк в подвал, погибло 10 человек"** — a tank shell
struck a basement shelter on Зелинского on 15 March [2022] killing 10
people, including Sartana evacuees who had fled there. This may be the
same incident at д.98.
Source: https://www.victims.memorial/people/havrylo-barabul

**д.110 — building collapse, family killed:**

| Name | Cause | Status |
|---|---|---|
| Кашиев Муслим Эльханович | building collapse | buried Мангуш cemetery |
| Кашиева Вероника Муслимовна | building collapse | unknown |
| Кашиева Мария Муслимовна | building collapse | unknown |
| Кашиева Наталья Александровна | building collapse | unknown |
| Панькина Валентина Петровна | cardiac arrest | buried in courtyard of д.110 |
| Толстокоров Павел Игоревич | building collapse | "тела не найдены" |
| Толстокорова Анастасия Павловна | building collapse | "тела не найдены" |
| Толстокорова Ольга Владимировна | building collapse | "тела не найдены" |

The Кашиев family — four members — died in one apartment (кв.45, д.110).
Three members of the Толстокоров family are still listed as missing with
bodies not found. Pankin'a cardiac arrest victim is buried in the building's
own courtyard.
Sources: t.me/Mariypol22/181, t.me/mariupolnow/33596, t.me/mariupolRIP/8057; map

**д.15 — fire deaths:**

| Name | Cause | Burial |
|---|---|---|
| Серафимова Раиса Георгиевна | "при пожаре ул. Зелинского 15" | "возле дома по ул. Зелинского 15" |
| Котилевская Нина Ивановна | — | "Похоронена за домом в зелёной зоне" (кв.40) |

Sources: t.me/mariupolRIP/3631, /1303

**Summary for Зелинского construction zone:** at minimum 14 named
individuals died on this street, including a confirmed multi-fatality
basement shelter event (10+ killed, per victims.memorial) and 3 persons
with bodies still not recovered. Three others are buried in the courtyard
or green zone behind buildings slated for the new-construction district.

### Demolition–reallocation chain: CONFIRMED CLOSED

**Зелинского д.15:**
- Deaths recorded: Серафимова (fire), Котилевская (buried in green zone
  behind building, кв.40).
- **Demolition ordered: Распоряжение ГКО ДНР №56, 29.09.2022** — six
  months after the invasion. Authority: ГКО ДНР, district: Жовтневый.
  Source SHA-256: `d431a53…`.
- Land cleared; ул. Зелинского is now in the СЗ-1 ПОРФИР development
  zone (eisghs 71846/71848/71850, RPD №93-000086/087/088,
  `under_construction`).

**Зелинского д.110:**
- Deaths recorded: Кашиев family (4 members, кв.45, same apartment);
  Толстокоров family (3 members, building collapse, **bodies not found**);
  Панькина Валентина Петровна (cardiac arrest, buried in building's
  own courtyard). Plus the 15 March 2022 multi-fatality basement event
  on this street (10+ killed per victims.memorial — may overlap with
  д.98 event).
- **Demolition ordered: Распоряжение администрации г.Мариуполя №144,
  12.12.2022** — nine months after deaths. Authority: Администрация
  г.Мариуполя, Жовтневый district. Source SHA-256: `d431a53…`.
- Land cleared; ул. Зелинского is now the СЗ КОРПОРАЦИЯ СМУ-5
  development zone (eisghs 66986–66989, 71399/71400, ЖК "Нахимовский",
  RPD №93-000049/083, `under_construction`). Land allocated to
  developer by Договор аренды земельного участка №138 (27.06.2025,
  DNR as public-owner lessor, cadastral 93:37:0010101:1959).

**Зелинского д.17А, 17Б, 19Б + Бахчиванджи д.25, 27 — predecessor addresses
CONFIRMED by decree text (2026-07-15):**

Which specific buildings ЖК «Нахимовский» (eisghs 66986–66989, 71399/71400)
actually replaced was unresolved until an official pro-occupation Telegram
post surfaced quoting the land-grant decree directly:

> «ЖК «Нахимовский» застройщика «Корпорация СМУ-5». Первый случай передачи
> земельных участков целыми зонами... Сегодня Денис Владимирович подписал
> распоряжение №178 о выделении двух земельных участков застройщику
> «Корпорация СМУ-5»... Он развернется на месте бывших домов №17А, 17Б,
> 19Б по ул. Зелинского, №25, 27, по ул. Бахчиванджи.»
> — t.me/russkiy_mariupol/13451

("ЖК Nakhimovsky by developer Korporatsiya SMU-5. The first case of
transferring land parcels as whole zones... Today Denis Vladimirovich
[Pushilin] signed directive No. 178 allocating two land parcels to developer
Korporatsiya SMU-5... It will be built on the site of former buildings
No. 17A, 17B, 19B on ul. Zelinskogo, No. 25, 27, on ul. Bakhchivandzhi.")

Every eisghs object in this cluster carries `decree_number: '178'` in its
own record — an independent match confirming the post. Pairing individual
new corpuses to individual predecessors required more than the decree text
(which names addresses but not which tower goes where): precise coordinates
read directly off damage photos and pre-war maps, cross-checked against this
project's own geocoding (all five paired within 1–11m for the four
Зелинского/Бахчиванджи-27 matches, 8m for Бахчиванджи-25), plus
foundation-pit photo perspective (visible neighboring buildings identify
which corpus sits where):

| Demolished | property_id | → New corpus | Confirmed by | Sentinel-2 crop sequence |
|---|---|---|---|---|
| Зелинского 17А | 4837 | eisghs 66986 | corpus parallel to Zelinskogo street (single-family homes visible across the street); DMS coords 11.4m from spine | ✓ 4 windows |
| Зелинского 19Б | 4841 | eisghs 66987 | flank facing L-shaped Зелинского 15's courtyard; DMS coords 7.7m from spine | ✓ 4 windows |
| Зелинского 17Б | 4838 | eisghs 66989 | by elimination; DMS coords 1.2m from spine — tightest match in this whole case study | ✓ 4 windows |
| Бахчиванджи 27 | 10640 | eisghs 71399 | foundation-pit photo (June 2026) showing the other 3 corpuses nearby; 91m from spine | ✓ 4 windows |
| Бахчиванджи 25 | 4778 | eisghs 71400 ("Нахимовский, 2 очередь") | decree_number match + 8m from spine | ✓ 4 windows |

Decree text says this will be a **six-building complex**; only five
predecessor addresses are named and five new corpuses currently exist on
the spine — the sixth building is either not yet reflected in ЕИСЖС or the
decree's building count doesn't map 1:1 to named addresses (cf. the
Металлургов 89А case, one new building spanning three old plots). Not
resolved; flagged for later.

**Independent visual corroboration — Sentinel-2 AOI-cropped imagery (Microsoft
Planetary Computer, `planetary_computer.py`, 10m/pixel, all crops <0.01% cloud
cover) — captured for all five addresses 2026-07-16/17**, one crop per address
per date window (2022-07-07 pre-demolition / 2023-08-06 / 2024-09-29 /
2026-05-22 post-rebuild): all five show the same signature — scattered built
structure in the 2022 crop, a bright bare-ground/rubble patch appearing by the
2023 window and persisting through 2024, then additional built structure by
2026 consistent with the ЖК «Нахимовский» rebuild. At 10m/pixel this is a
corroborating visual signal, not proof of individual-building identity (that
comes from the coordinate/photo matches in the table above) — same evidentiary
weight class as the project's existing Wayback-tile/UNOSAT layers. sha256
lineage for the crops added this session: Зелинского 19Б —
`1660869d4f46`/`162d576767e7`/`c3b553fa0389`/`19cc9d7e4906` (2022/2023/2024/2026);
Зелинского 17Б — `ef936383004e`/`fb577ec2e926`/`c5c0a372f570`/`27e122c723f6`;
Бахчиванджи 27 — `776e4865283d`/`fa1ea384c881`/`b2a6971c9571`/`fd02dfc5a241`.
Зелинского 17А + Бахчиванджи 25 crops were captured in the prior session
(2026-07-16); their shas are in `data/reports/osint/4837_*/planetary_computer.json`
and `4778_street-bakhchivandzhi-25/planetary_computer.json` respectively —
not re-quoted here since they weren't re-verified in this pass. Captured
`source_type=osint_planetary_computer_crop`, full metadata per address in
`data/reports/osint/<slug>/planetary_computer.json`.

**New deaths confirmed at these specific addresses (Mariupol Destruction
and Victims Map TSV + own-channel corroboration, checked 2026-07-15):**

- **Зелинского 17А** (→66986): Иванов Виктор Евгеньевич, d. 13.03.2022, died
  in the building's basement (his own family's memorial post,
  t.me/mariupolRIP/11748, actually reads "Зелинского 17а" — the TSV's own
  address field for this row drops the letter, an extraction gap, not a
  second address). Ахтырский Максим Сергеевич, 12 y/o, killed by airstrike
  18.03.2022 (t.me/mariupolRIP, corroborating post t.me/[private]/4824). A
  missing-person search post for Горпенко Владимир Иванович (b. 1949), apt.
  14 or 22, never resolved to a confirmed death
  (t.me/stroiteley_175_177_163_171_166_152/4349 — filed under an unrelated
  chat's title-stripping track, cross-street mention).
- **Зелинского 19Б** (→66987): Микикечко Максим Игоревич, killed by
  shrapnel 04.03.2022 in what this message identifies as a **railway-
  workers' dormitory** ("ж/д общежитие"), not an ordinary apartment
  building — body collected by the "Орфей" removal service, burial location
  unknown (t.me/mariupolRIP/32958).

**Additional artifacts flagged, not yet captured into the evidence base**
(2026-07-15): a video (t.me/kadryVoynyMariypol2022/854, timestamp 2:44–4:25)
showing this Зелинского/Хмельницкого corridor, including "Зелинского 15,
19б"; two further mariupolnow posts on 17Б (t.me/mariupolnow/8354) and 17А
demolition-in-progress (t.me/mariupolnow/25517). **@kadryVoynyMariypol2022**
itself is flagged as a channel warranting a full scan — not yet covered by
this project's existing chat corpus.

**YouTube walkthrough/flyover corroboration (2026-07-15).** Two videos
reviewed on this street, both hashed into the raw store (scripts/321,
source_type `youtube_video`) with whisper transcripts, address/timecode
indexes, and derived still frames (scripts/322):

*wO7FXXmKV7Y* (walkthrough, 2023-09-20,
https://www.youtube.com/watch?v=wO7FXXmKV7Y) — the narrator states on
camera, standing at the 17А fence line (still at 01:58, showing the green
site fence and an active crane): *"За этим забором был дом номер 17А. Его
снесли."* ("Behind this fence was building No. 17А. It was demolished.")
— direct on-camera confirmation of the demolition already documented via
decree №178. The same walkthrough surfaces demolition/restoration language
for three addresses on this street **not yet in the crosswalk**, all
independently consistent with heavy registry activity already on the
spine:

| Address | pid | On-camera description | Spine seizure_event |
|---|---|---|---|
| д.87 | 7231 | "тоже частично демонтирован, и ведутся восстановительные работы" (also partially dismantled, restoration under way) | 79× registry_inclusion |
| д.19 | 4839 | "часть дома снесли до фундамента, и уже восстанавливают" (part of the building demolished to the foundation, now being rebuilt) | 50× registry_inclusion |
| д.33 | 4847 | "дом в процессе восстановления" (building under restoration) | 105× registry_inclusion — heaviest on this street |
| д.106А | 4831 | narrator reads an on-building "паспорт объекта" placard (completion date, likely misheard/mis-OCR'd on the audio as "1923" — near-certainly Q4 2023) describing new windows, a cleaned stairwell, replaced radiators, motion-sensor lighting — i.e. **renovated, not demolished** | **0 events on spine** — an evidentiary gap, flagged, not yet explained |

д.87 and д.19 in particular echo the д.106 restoration-without-restitution
pattern (a demolition/decree record on file while the building is
partially or wholly standing and being rebuilt) rather than the clean
demolish-and-replace pattern documented for the decree-№178 cluster above
— worth a closer look as additional M4 candidates, not yet added to the
crosswalk (no eisghs newbuild object corresponds to any of them; they
remain standing, renovated buildings, not replaced footprints).

*lQ_Xyu2WWjg* (contemporary flyover, 2022-05,
https://www.youtube.com/watch?v=lQ_Xyu2WWjg) — stills extracted at the
user's annotated timecodes corroborate the DMS-based pairings above by
direct visual inspection: 00:32 (corner of 17А) shows extensive fire/blast
scorching consistent with the siege-damage narrative; 00:38 (collapsed
corner of 19Б) shows a fully collapsed structural corner, independently
corroborating pid 4841's crosswalk entry.

**Critical note — two parallel tracks on the same street:**
The ownerless registry contains **582 entries** across 20 Зелинского
buildings (`data/parsed/ownerless_registry.jsonl`) — д.1, 3, 13, 19,
30, 33, 45, 47, 67, 73, 87, 92, 94, 96, 98А, 100, 102, 104, 106, 108
— covering hundreds of individual apartments still in standing buildings.
Buildings **д.15, д.98, д.110** are conspicuously **absent** from the
ownerless registry: they were processed via the *demolition* track
(physical clearance + land reallocation to developer), not the *title-
stripping* track. The two mechanisms converge on Зелинского as follows:

| Track | Buildings | Mechanism | Endpoint |
|---|---|---|---|
| Demolition | д.15, 17, 19, 21, 23, 27, 30, 51, 110 | GKO №53/56; Admin. decrees №144/104/149/172 | Land cleared → developer land-grant → new ЖК |
| Title-stripping | д.1, 3, 13, 19, 30, 33, 87, 94, 96, 98А, 100–108 | Ownerless registry (582 apts); Кольцов decrees №96/1806 | Flat-by-flat «бесхозяйность» → title transfer |

Most recent ownerless decrees on this street: Кольцов decree №1806
(04.12.2025) designating 16 flats at д.108 ownerless; decree №96
(05.02.2026) designating 8 flats at д.13 — occurring *while* the new
ЖК is under active construction metres away.

**Additional corroboration, 2026-07-12 sweep** (scripts/300–308; full
detail in `data/reports/grave_sites_master_evidence.csv`) — independently
confirms д.15 (both named deaths) and д.110 (Панькина) above, and adds
seven new addresses on the same street not previously in this case:

| Address | Stage(s) | Named / evidence |
|---|---|---|
| д.13 | ownerless_designation;registry_inclusion | Пархоменко Игорь Борисович, killed by shrapnel 15.03.2022 |
| д.19 | registry_inclusion | corroborating channel post |
| д.19б | demolition | Кононенко Виталий, d. 25.03.2022 |
| д.21 | demolition | Шабанова Ольга Анатольевна (bedridden, killed at this address) |
| д.21а | demolition | Мищенко Эдуард Семенович |
| д.47 | registry_inclusion | Костин Виктор Викторович |
| д.106 | reclaim;registry_inclusion | burial recorded near this address |

---

## Case 3 — ul. Kuprina 9A "by the heat-distribution substation": documented mass ad-hoc burial site

**eisghs objects on ул. Куприна:**
- 66293: ул. Куприна, д.77Б — СЗ ОЛИМПСТРОЙ НР (ИНН 9309027678), `under_construction`
- 66292: ул. Куприна (no house number in ЕИСЖС's own field) — СЗ СИРИУС БИЛД
  (ИНН 9310014320), `under_construction` — **confirmed 2026-07-15** (map
  crosswalk work) as the replacement for demolished **д.69** (property_id
  4947), renumbered **69Б**; see the demolition→rebuild crosswalk in
  `scripts/164_export_map_layers.py`
- 69766: ул. Куприна (no house number) — СЗ АНТАРЕС, under construction —
  **confirmed 2026-07-15** as a single new building spanning the combined
  footprint of demolished **д.63** (property_id 4945) AND **д.65** (property_id
  4946); final house number not yet assigned (foundation stage as of the
  latest construction photo, June 2026)

**The burial site — Куприна 9А, at the heat-distribution substation
("у Теплосетей")** — is a named, photographed communal burial site
documented in the mariupolRIP Telegram channel. 13 individuals are
recorded as buried here:

| Name | Residence | Cause |
|---|---|---|
| Беленец Владимир Яковлевич | — | — |
| Гайдай Людмила Федоровна | ул. Куприна | авиаудар, killed in apartment |
| Дьякова (Вазианова) Валентина Борисовна | пр.Мира, 143-74 | cardiac arrest |
| Карляни Ольга Ивановна | — | — |
| Кутовой Михаил Алексеевич | гражданин РФ | — |
| Михайлова Любовь Петровна | пр.Мира, 127-36 | — |
| Подолян Фиона Васильевна | — | — |
| Соберляк Алла Михайловна | пр.Мира 127 кв.47 | — |
| Тарасенко Олег Станиславович | — | — |
| Терещенкова Евгения Степановна | Куприна, 3-45 | — |
| Уютова | ул.Куприна 13 кв.26 | — |
| Шумилов Владислав Васильевич | Куприна 5-117 | — |
| + 1 additional record | — | — |

Sources: t.me/mariupolRIP/21445, /12472, /16165, /16970, /21434, /21438,
/21441, /21444

**Photographic and video evidence** of the grave site is referenced in
multiple records ("фото видео могил", "фото/видео могил"). The site is
identified by a named landmark (the heat-distribution substation —
Теплосети/Теплосеть facility at Куприна 9А), making it precisely
locatable.

At **Куприна 19**, an airstrike killed a father, son, and grandmother
together ("авиаудар, погиб вместе с отцом Сергей Владимирович, и
бабушкой"), all buried in the courtyard. At **Куприна 77** (directly
matching the ОЛИМПСТРОЙ НР new-build address), one person is recorded as
having "сгорел под обломками дома" (burned under rubble) — proximity
to, or at, the new-build site.

**Additional corroboration, 2026-07-12 sweep** — independently confirms
д.19 (both named deaths) above, and adds seven more addresses on the same
street:

| Address | Stage(s) | Named / evidence |
|---|---|---|
| д.5 | demolition | Поддубная Майя Олеговна |
| д.7 | registry_inclusion | Капралов Сергей Николаевич (1936) + Балахчи…, multi-name post |
| д.11 | ownerless_designation;registry_inclusion | Ермилова Зинаида Викторовна |
| д.37 | registry_inclusion | Кудрявцев Александр |
| д.39 | registry_inclusion | Стремоухов Александр Петрович |
| д.41 | demolition | Поликарова В. М. |
| д.65 | demolition | **4 named, same building fire** (upgraded 2026-07-15 from the single name below via Mariupol Destruction and Victims Map TSV): Гапонов Сергей Витальевич (kv.132, jumped from the 6th floor); Гримани Татьяна Ивановна (kv.132, buried "во дворе около дома по проспекту Строителей, 140" — cross-references the Строителей courtyard-burial cluster, Case 1); Овчаренко Раиса (4th entrance, kv.123); Овчинникова Нелля (kv.120, 80 y/o, jumped from the burning apartment, d. 14.03.2022, per this TSV — the case study's original single-name entry gave 15.03.2022) |
| д.73 | ownerless_designation;reclaim;registry_inclusion | first-person loss testimony, unnamed |

---

## Case 4 — bul. Shevchenko: roadside burial strip

**eisghs objects:**
- 66545: б-р Шевченко, д.276а — СЗ ОЛИМПСТРОЙ НР, `under_construction`
- 70024: б-р Шевченко, д.71 — СЗ СК ВОЗРОЖДЕНИЕ (ИНН 9308026880), `under_construction`

The boulevard has a documented pattern of bodies buried in the **green
median strip** ("зеленка на дороге"):

| Location | Records | Notes |
|---|---|---|
| **напротив д.270 (зеленка)** | **6 graves** | Roadside, in the green strip — explicit coordinates |
| **д.252** | **5 graves** | Explicit address, one Telegram post (mariupolRIP/21425) lists multiple names |
| напротив д.307 (зеленка) | 1 grave | Same green-strip modality |
| д.301 | 3 graves | At/near house 301 |
| д.305 | 1 — direct shell hit to apartment | |
| д.311 | 1 — killed by shrapnel in courtyard | "погиб у себя во дворе" |
| д.274 | 1 — wounded 9 March by shell in courtyard | courtyard burial |
| д.289 | 1 | courtyard burial |

The new-build at **д.276а** (ОЛИМПСТРОЙ НР) sits between the two
heaviest roadside burial clusters at д.270 and д.307. The green strip
burials are a distinctive feature of the Шевченко boulevard siege — made
necessary because residents could not travel to formal cemeteries.

Five of the д.252 burials are documented in a single mariupolRIP post
(id/21425): Рожков Александр Геннадиевич, Рубина Мария, Ластовиненко
Клавдия Федоровна, Березанцева А.А., and one unnamed person described
as "была не в себе, где-то с ул. Куприна" (mentally incapacitated,
found near Куприна).

**Additional corroboration, 2026-07-12 sweep** — independently confirms
д.74 above (registry_inclusion — the building was not demolished, unlike
this case's original framing of the boulevard as a demolition/green-strip
site; it entered the title-stripping track instead) and adds three more
addresses:

| Address | Stage(s) | Named / evidence |
|---|---|---|
| д.64а | registry_inclusion | Галстян Грач Ашотович, Ногаш Владимир Алексеевич (2 named, 2 independent sources) |
| д.289 | registry_inclusion | Филиппова Надежда Николаевна |
| д.311 | registry_inclusion | Трубников Максим Анатольевич, killed in his own courtyard |
| д.331 | registry_inclusion | unresolved inquiry post, 13.03.2022 |

---

## Case 5 — ul. Latysheva: death-without-medicine cluster

**eisghs object:** 71674 — ул. Латышева — СЗ-1 ПОРФИР, `under_construction` (RPD №93-000084)

At **Латышева 35**, at least two people died specifically from lack of
medicine during the siege:

| Name | Cause | Burial |
|---|---|---|
| Кваско Дарья Дмитриевна | **"умерла без инсулина"** | Латышева 35 |
| Олейник Дмитрий Владимирович | **"умер без инсулина"** | Латышева 35 |

Both lived and died at Латышева 35 and are buried there (or adjacent to
the "Новая почта" branch at Латышева 35а, which served as an informal
landmark for the site):

Additional burials near the same location:
- Семейко Нина Ивановна — died in basement of д.31 (pneumonia/COVID),
  buried "за новой почтой Латышева 35а"
- Шимко Екатерина Николаевна — burial estimated "вероятно: Новая почта
  17, Латышева, 35а"
- Кратенко — "Новая почта 17, Латышева, 35а"

The two insulin-deprivation deaths are directly attributable to the
siege blockade cutting off medication supply — a distinct harm category
from artillery/airstrike deaths.

**Additional corroboration, 2026-07-12 sweep** — one new address on this
street: **д.27** (demolition), a two-year memorial post for a death "в
своей квартире по ул. Латышева, 27."

---

## Case 6 — Meduza "Gravedigger" article (10.06.2022): eyewitness cross-section of five streets

**Source:** Meduza feature "«Каждый день просыпаешься и ты кто-то новый. Сегодня ты
могильщик»" (10 June 2022) — independent Russian-language journalism, published outside
Russia; archived at meduza.io. The article documents Yaroslav Dema (Ярослав Дема), a
Mariupol resident, who dug graves for neighbours and strangers in courtyards and
street-side patches throughout the siege. The piece was published while Russian forces
were still consolidating control — making it one of the earliest independent records of
civilian deaths at specific named addresses.

Addresses appearing in the article and their current evidentiary status:

### пр. Победы, 32/42 — Dema's home ("банковский дом")

- **Ownerless registry:** 1 apartment (кв.21) registered ownerless.
- Demolition register: пр. Победы buildings affected include д.18/5, 22/16, 27, 30,
  31, 37, 39, 55, 61, 69, 71, 106, 127 (ГКО №56 + Admin №144). д.32/42 is not in the
  demolition register — it is standing and entering the title-stripping track.
- EISGHS new builds: none at this specific address.

Dema was living in this building during the siege and left from it to dig graves across
the city. The article documents that the building was sheltering numerous residents who
could not leave — directly contradicting any "ownerless" classification.

### пр. Строителей, 160 — burial site, courtyard and green zone

- **Ownerless registry: 47 apartments** stripped of title.
- Demolition register: пр. Строителей д.70, 72, 72А, 74, 76, 78, 80, 88, 93, 101,
  107, 112, 117 ordered demolished (various ГКО/Admin decrees 2022–2023). д.160 is
  not in the demolition register — standing, being title-stripped.
- EISGHS: ПОРФИР has active new-build projects on Строителей (commissioned д.70Б
  "Резиденция II" = Case 1 above; second project eisghs 65916 `under_construction`,
  address "пр-кт Строителей" without house). The avenue is an active construction zone.

The Meduza article places Dema at Строителей 160 burying residents who died during the
siege. The subsequent 47-apartment ownerless registration at the same building is direct
evidence the occupation is processing a building its own records show was sheltering
civilians who could not leave.

### ул. Солнечная, 8 — burial site

- **Ownerless decree:** Кольцов decree records ownerless flats on Солнечная (decree hit
  confirmed in `ownerless_decrees.jsonl`).
- Demolition register: ул. Солнечная д.1 and д.3 demolished (ГКО ДНР №26, 09.08.2022).
  д.8 is not in the demolition register — standing, entering title-stripping track.
- EISGHS: eisghs 67223 — "СЗ СОЛНЕЧНАЯ" (`under_construction`, address "ул Солнечная",
  no specific house — the project may share the d.3 cleared lot).

### пр. Металлургов, 96/98 — **most significant hit: 121 ownerless apts + new ЖК**

- **Ownerless registry: 121 apartments** at д.96 and д.98 registered ownerless.
- Demolition register: 15 Металлургов buildings ordered demolished (ГКО №56 + Admin
  №1/35/58/172), ranging from д.25 to д.235. д.96 and д.98 are **not** in the demolition
  register — they are being processed via the title-stripping track, not physical clearance.
- EISGHS: **ЖК "Ленинградский квартал"** (СЗ СУ-2007, ИНН 9310008599) — **15 МКД on
  пр. Металлургов**; RPD №93-000003; cadastral 93:37:0010110:259; 8 buildings
  `commissioned`, 7 `under_construction`. This is one of the largest new-build
  complexes in the ЕИСЖС dataset. The "литера" address format (Литер 1–25) means the
  buildings are identified by plot-internal letters rather than street numbers; cadastral
  map review is needed to confirm whether д.96/98 falls within cadastral parcel
  93:37:0010110:259.
- Also on Металлургов: eisghs 54271 "Дом с часами" at д.54А (СЗ РКС-ДЕВЕЛОПМЕНТ,
  `commissioned`).

**Cadastral confirmation result (2026-06-16):** PKK is geoblocked from outside Russia.
Geocoding via OSM + interpolation from confirmed anchor points (д.79 at 47.10602/37.55216,
д.93 at 47.10655/37.55297, д.94 at 47.10686/37.55142, д.108 at 47.11307/37.55692)
establishes:

| Address | Estimated position | Track |
|---|---|---|
| д.96 (even side) | ~47.10775, 37.55221 | **Ownerless registry** (121 apts) |
| д.98 (even side) | ~47.10863, 37.55299 | **Ownerless registry** (121 apts) |
| ЖК "Ленинградский квартал" Литера 17 | 47.10600, 37.55220 | **Commissioned** new build |
| ЖК "Ленинградский квартал" Литера 15 | 47.10620, 37.55430 | **Commissioned** new build |
| Demolished д.79–91 (odd side) | 47.10602–47.10647 | ГКО №56, demolished 2022 |

**Finding:** ЖК "Ленинградский квартал" Литера 13–18/25 is **NOT** on the cadastral
parcel of д.96/98. д.96/98 (even side) are being processed via the *title-stripping*
track. The new ЖК buildings are ~50–130m away on the **odd side**, built on the cleared
plots of demolished д.79, 81, 85, 87, 89, 91 — six buildings on the opposite side of
the street that were ordered demolished under ГКО №56 (29.09.2022).

**This is the same dual-track pattern confirmed on ул. Зелинского:**

| Track | Buildings | Status |
|---|---|---|
| Demolition | д.79, 81, 85, 87, 89, 91 (odd side) | Cleared → ЖК "Ленинградский квартал" (15 МКД, 8 commissioned) |
| Title-stripping | д.96, 98 (even side, standing) | 121 apts in ownerless registry |

**Evidentiary significance:** The Meduza article (10 June 2022) documents named individuals
who died at пр. Металлургов 96/98 and were buried in the building's courtyard by Dema —
persons named include Леонид Сошенко and family members. д.96/98 subsequently had
**121 apartments** registered as ownerless. The new ЖК across the street is built on
cleared plots of the demolished buildings from the same block. The occupation is
simultaneously constructing on cleared lots (odd side) and stripping title from
surviving buildings (even side) on the same 200-metre stretch of Металлургов — while
the occupants who never left those buildings were being buried in their own courtyards.

### ул. Пашковского area — Больница №4 zone

- Demolition register: Пашковского д.10, 21/46, 35/38, 42, 44, 50, 52, 81 (various
  orders 2022–2023). Пашковского 65 is not in the demolition register.
- The article mentions Больница №4 on Пашковского — the hospital area was a reference
  point for Dema's burial routes; no EISGHS object currently on Пашковского.

### ул. Азовстальская — largest ownerless concentration in the dataset

While not named as a direct burial site in the Meduza article (Dema operated primarily
in the Левый берег district), the pipeline data shows ул. Азовстальская has:

- **Ownerless registry: 537 apartments** — the highest single-street count in the
  entire dataset.
- Demolition register: 15 buildings demolished (ГКО №54 + Admin №157 + Admin №234),
  д.7 through д.55.
- No EISGHS new-build object yet on Азовстальская.

**Named grave-site corroboration, 2026-07-12 sweep** — seven addresses on this
street now carry named-victim burial evidence, one of which is a distinct
finding worth flagging on its own:

| Address | Stage(s) | Named / evidence |
|---|---|---|
| д.7 | demolition | Карпенко Дмитрий; Коваленко Виктор Викторович (24.09.1985–27.03.2022) |
| д.9 | demolition | Христофоров Игорь Владимирович; Ткачёв Антон + mother Ткачева Евгения |
| д.19 | demolition | Коваленко Валентина Ивановна |
| д.22 | demolition | Гуменюк Анатолий Максимович |
| д.95 | ownerless_designation;registry_inclusion | Тонкодубова (Кувалдина) Виктория Александровна; Тулинова Вера Дмитриевна |
| д.164 | registry_inclusion | Звягинцев Владимир Васильевич (residence) — see below |
| д.170 | registry_inclusion | Золотарёв Анатолий Яковлевич |

**д.164 — residence of Звягинцев Владимир Васильевич; a likely second
account of his death exists, uncorroborated to this address.** Correcting
an over-attribution caught in review: the mariupolRIP post that matched
this property (t.me/mariupolRIP/28678, 24.02.1953 г.р., "Проживал
Азовстальская 164 кв. 23") gives his *residence*, not a burial location —
he was killed 22.03.2022 by shelling while cooking food with others "На
стадионе Азовсталь. На Левом Берегу" (at the Azovstal stadium, Left Bank),
away from this address; the post has no burial information at all, and
appeals for word of his missing son. **A separate memorial.ua obituary**
(`memorial.ua/obituaries/civilians/zviahintsev-volodymyr-757`, "Володимир
Звягінцев," died 22.03.2022, age 69 — consistent with a 24.02.1953 birth
date turning 69 on invasion day) describes a different, harrowing account:
one of five bodies buried together in a shell crater with a hand-written
nameplate, and **after Russian forces occupied the city, the bodies
disappeared from that site** ("Тіла п'ятьох загиблих поховали у вирві…
Однак після того, як російські військові окупували місто, тіла вбитих
звідти зникли") — his family, on returning, could not find the body or
any reburial location. The matching name, death date, and birth-year math
make these very likely the same person, but that is this project's
inference, not a formally confirmed identity match — and **the memorial.ua
account gives no address for the crater grave**, so it cannot be pinned to
Азовстальская 164 or to any specific property on the spine. If the two are
the same person, this would be the project's clearest case of the
occupying authority interfering with an informal grave site itself, not
just the property around it — but it needs a named-address anchor before
it can be used as more than a documented allegation. Property д.164 is on
the `registry_inclusion` track — no demolition or reallocation on file.

### Source reliability note

The Meduza article is a primary testimonial source with corroboration value under the
Berkeley Protocol. Key characteristics:
- Published 10 June 2022, during the occupation, before any administrative seizure proceedings.
- Named author (journalist); named subject (Ярослав Дема, full name given).
- Specific addresses with narrative context; not a list but a reported account with dates.
- Archived at meduza.io (independent, registered outside Russia); permanent URL.
- Cross-check against mariupolRIP Telegram channel for named individuals is possible.

For RD4U/ICC purposes: the article establishes that properties now in the ownerless
registry were **actively occupied by identifiable residents** during the siege period —
directly undermining the legal predicate for "бесхозяйность" (ownerlessness) under
ГПК РФ гл. 33 / ФКЗ-4.

---

## Case 7 — prosp. Stroiteley 74–88: the five-building block

**The clearest case in the dataset: five consecutive residential buildings, all with
documented courtyard graves, all demolished under coordinated occupation orders, all
replaced by a single branded development under five consecutive land-grant decrees
from the same official.**

### The block

| Address | pid | Demolition order | Demolition date | New build (ЕИСЖС) | Brand | Flats | Land decree | Cadastral |
|---|---|---|---|---|---|---|---|---|
| пр. Строителей, 74 | 4641 | ГКО ДНР №56 → Admin. Мариуполя | 2022-12-12 | 69427 "Резиденция Селект" | СЗ-1 ПОРФИР | 180 | №394 / Пушилин | 93:37:0010101:6160 |
| пр. Строителей, 76 | 4642 | ГКО ДНР №56 → Admin. Мариуполя | 2022-12-12 | 69749 "Резиденция Селект" | СЗ-1 ПОРФИР | 180 | №393 / Пушилин | 93:37:0010101:6162 |
| пр. Строителей, 78 | 4643 | Распоряжение ГКО ДНР №56 | 2022-09-29 | 69751 "Резиденция Селект" | СЗ-1 ПОРФИР | 108 | №392 / Пушилин | 93:37:0010101:6161 |
| пр. Строителей, 80 | 6248 | Распоряжение ГКО ДНР №56 | 2022-09-29 | 70147 "Резиденция Селект" | СЗ-1 ПОРФИР | 126 | №391 / Пушилин | 93:37:0010101:6088 |
| пр. Строителей, 88 | 4647 | Распоряжение ГКО ДНР №56 | 2022-09-29 | 70142 "Резиденция Селект" | СЗ-1 ПОРФИР | 234 | №390 / Пушилин | 93:37:0010101:6089 |

Developer: **ИНН 9310009271** (СЗ-1 ПОРФИР). All five reallocation events:
2025-12-17 (д.74) and 2026-01-13 / 2026-02-03 (remainder), all `under_construction`
as of June 2026. Combined new-build footprint: **828 apartments**.

### The graves

Five separate entries in the documentation source ("Погибшие и Пропавшие на Карте
Разрушений") record courtyard burials specifically at the addresses of these five
buildings during the 2022 siege. The source is a Telegram-based civilian documentation
channel (mariupolRIP) that logged deaths and burials street-by-street as they occurred,
published before any administrative seizure proceedings were underway.

All five entries are classified as grave-site records (type: "grave"), not merely
deaths-at-address — meaning burial in place is explicitly recorded, not inferred.

### The demolition sequence

UNOSAT satellite damage assessment (WorldView-3 imagery, analyst: SU, confidence:
Very High) assessed all five buildings as **"Moderate Damage"** as of **12 May 2022**
— weeks after the siege ended. The buildings were damaged but standing. Residents
sheltering in the basements were burying their dead in the surrounding courtyards at
exactly this time.

Russian/DNR demolition orders came later, in two waves:

- **29 September 2022** — Распоряжение ГКО ДНР №56: д.78, д.80, д.88 ordered
  demolished. District: Жовтневый (д.78/80) and Приморский (д.88).
- **12 December 2022** — Распоряжение администрации г.Мариуполя: д.74, д.76
  ordered demolished. District: Жовтневый.

The Russian federal reconstruction tracker separately records all five buildings as
"100% destruction, phase II reconstruction," contractor **ГК Трансстройинвест**.

### The coordinated land seizure

Пушилин's land-grant decrees for the five plots are numbered **390, 391, 392, 393,
394** — five consecutive decree numbers, issued as a single administrative operation.
Each decree grants the cleared plot to the same legal entity, СЗ-1 ПОРФИР
(ИНН 9310009271), for construction of the same branded residential development:
**"Резиденция Селект."**

This is not incidental. Decrees 390–394 represent a pre-planned, coordinated seizure
of an entire residential block. The demolition of the five buildings, and the
registration of five separate cadastral parcels for the same developer, was executed
as a single administrative package — not as five independent decisions triggered by
building condition.

The parcels are: 93:37:0010101:6088, :6089, :6160, :6161, :6162 — four of which
(6088, 6089, 6160, 6161, 6162) appear to be newly registered sub-divisions of the
original block cadastral, created specifically to carry the individual developer grants.

Displacement confirmed: 27 households across the five buildings appear on the
occupation's own housing-distribution list for Zhovtnevy district —
confirming the buildings had residents who were tracked as displaced, not abandoned.

### Evidentiary chain (per building)

```
[Siege, Mar–Apr 2022]
Residents shelter in basements
→ Dead buried in courtyards
   (documented: mariupolRIP records, type=grave, 5 addresses)
→ UNOSAT: Moderate Damage, 12 May 2022
   (WorldView-3, Very High confidence; buildings standing, not destroyed)

[Occupation administrative phase]
→ Demolition orders: ГКО №56, 29.09.2022 (д.78/80/88)
                     Admin. №_, 12.12.2022 (д.74/76)
   (Source: DNR MinStroy demolition register CSV, SHA-256: d431a53…)
→ Federal tracker: "100% destruction", contractor ГК Трансстройинвест
   (Russian Минстрой open data)

[Developer allocation]
→ Land-grant decrees 390–394 (Пушилин, D.V.) to СЗ-1 ПОРФИР ИНН 9310009271
   (Source: dnr_land_orders.jsonl, method=inn_exact)
→ ЕИСЖС RPD filings: 93-000070/72/73/79/80 (ФГИС ЖКХ / наш.дом.рф)
→ New buildings: "Резиденция Селект", under construction Dec 2025 – Feb 2026
```

No forensic investigation, no formal exhumation, and no notification to Ukrainian
authorities took place at any step. Ukraine has not recognised any of the
administrative acts in this chain.

### What this case establishes

1. **Occupied buildings demolished.** UNOSAT "Moderate Damage" (not "Destroyed") at
   the time of the siege means residents were present and active in these buildings
   during the period graves were being dug. The demolition was an administrative
   decision, not a consequence of structural collapse.

2. **Graves on-site.** Five separate grave-site records placed burial at these exact
   addresses. Courtyard burials were universal during the siege due to the impossibility
   of reaching formal cemeteries; the pattern matches the documentary record on every
   other street in this dataset.

3. **Coordinated seizure, not individual determinations.** Decrees 390–394 as a
   sequential batch demonstrate pre-planned block-level seizure of the footprints.
   The demolition orders preceded the developer allocation by months, but both were
   issued by the same state apparatus (GKO ДНР / DNR administration → Пушилин).

4. **828 new apartments, zero exhumations.** The new "Резиденция Селект" buildings
   (828 combined flats, under construction as of June 2026) are on the cadastral
   footprints of the demolished predecessor buildings where burials are documented.
   No Ukrainian or international forensic body has had access to these sites.

**RD4U category:** A3.1 (deprivation of ownership by unlawful demolition + seizure),
A3.3 (forced displacement — 27 households documented), A3.6 (loss of access to
property in occupied territory). All five properties are categorised accordingly in
the spine.

**Rome Statute relevance (Art. 8(2)(b)(viii)):** The coordinated allocation of five
residential blocks to a single private developer — preceded by demolition orders
issued by an occupying power's administrative apparatus and followed by settlement
construction — is consistent with the transfer-of-population element. The pre-planned
sequential decree structure (390–394) is direct documentary evidence of intent at the
administrative level.

---

## Case 8 — Citywide systematic sweep (2026-07-12): three-source cross-reference

**Cases 1–7 above were found by working outward from the 91 EISZhS new-build
objects — a narrow, construction-anchored search. This case inverts the
method: start from every documented informal/ad-hoc burial citywide, in any
of three independent sources, and check each one against every seizure
event on the spine — not just new construction.**

### Method

1. **`data/raw/17e0dd2c…csv`** — the full mariupoldestruction.com
   named-victims sheet (the same source as Cases 1–7's original xlsx, now
   re-pulled directly from the live Google Sheet, 4,517 rows). Classified
   for informal-burial language (во дворе/за домом/в подвале/etc., with a
   negation check so "тело лежит, не захоронен" — remains left in place,
   never buried — is tracked separately, not counted as a grave) and for
   address-echo (burial-place field repeats the same street+house as the
   death-place field). 275 confirmed informal burials, 142 distinct
   extractable addresses. Scripts 299–300.
2. **@mariupolRIP full channel scan** — 5,961 messages (scripts/302–303),
   the channel behind most of the spreadsheet's citations, scanned as
   primary text rather than through the spreadsheet's summary cells. 284
   leads never cited as a spreadsheet source at all; 72 matched a property
   with a seizure event. Diffed against the ~1,600 message IDs the
   spreadsheet already cites, so this does not double-count spreadsheet
   rows. Scripts/304.
3. **memorial.ua obituaries** (scripts/305–307) — 3,320 civilian + children
   obituary pages crawled (robots.txt names ClaudeBot specifically, so this
   ran from the user's own machine, not Claude's), 464 confirmed Mariupol
   deaths. A different kind of source — professionally-written biography,
   not a burial registry — so its yield is narrower (7 property matches)
   but adds detail no other source has (e.g. Роман Шворінь's death account
   names просп. Перемоги 32/42 precisely, in a language — Ukrainian — the
   other two sources never use). Required a small hand-verified UA→RU
   street dictionary (10 entries, each checked against the spine before
   use) since the property spine is built from Russian-language occupation
   sources and memorial.ua writes in Ukrainian.

Address resolution used the project's real normalizer
(`normalize.address.address_to_building_key`), with one addition: free
text (spreadsheet cells, chat messages, obituary prose) usually omits the
street-type prefix (AVENUE/STREET/BOULEVARD/etc.) that `building_id` needs
— "Металлургов 47," not "проспект Металлургов, 47." Rather than guess the
class, the property table's own inventory was used to recover it: if a
bare street stem is unambiguous across the spine, the single matching
class is used; if the stem exists under more than one class (37 of 551
stems do, including "металлургов" itself — both STREET and AVENUE exist in
the spine, a pre-existing inconsistency), the row is left unmatched rather
than guessed. Zero ambiguous collisions actually occurred in this run.

Full evidence, per-property rollup, and per-source detail:
`data/reports/grave_sites_master_evidence.csv` (160 rows) and
`grave_sites_master_properties.csv` (116 rows) — gitignored, local only.

### Result: 116 properties, 11 corroborated by two independent sources

| Stage | Properties |
|---|---|
| demolition | 59 |
| registry_inclusion | 54 |
| ownerless_designation | 17 |
| reclaim | 11 |
| reallocation | 1 |
| expropriation | 1 |

Of these, **seven streets overlap with Cases 2–5 above** (Зелинского,
Куприна, Азовстальская, Шевченко, Латышева — new addresses folded into
those cases inline) and **проспект Металлургов, 47 overlaps with MUP-CS-005**
(Троянда-М — see below). The remaining properties are new territory for
this project. Eleven are corroborated by two independent sources rather
than one:

| Address | Evidence items | Sources | Stage(s) | Named |
|---|---|---|---|---|
| **просп. Металлургов, 47** | 7 | sheet + channel | demolition | Галушко Андрей, Паскаль Мария, Федорова Надежда, Харакоз Наталья Георгиевна, + Калина Сергей Сергеевич (new — see below) |
| просп. Победы, 61 | 3 | sheet + channel | demolition | Барков Виктор Николаевич |
| бул. Шевченко, 64а | 3 | sheet + channel | registry_inclusion | Галстян Грач Ашотович, Ногаш Владимир Алексеевич |
| ул. Азовстальская, 9 | 3 | sheet + channel | demolition | Христофоров Игорь Владимирович |
| просп. Строителей, 62 | 2 | sheet + channel | registry_inclusion | Борисенко (Церковная) Татьяна Евгеньевна |
| ул. Ломизова, 13 | 2 | sheet + channel | demolition | Бурцев Иван Николаевич |
| ул. Ломизова, 9 | 2 | sheet + channel | demolition | Романов Олег Евгеньевич |
| ул. Владимирская, 30 | 2 | sheet + channel | ownerless_designation;registry_inclusion | unnamed ("Пётр") |
| ул. Горловская, 6 | 2 | sheet + channel | registry_inclusion | Белорусова Любовь Афанасьевна |
| ул. Волгодонская, 3 | 2 | sheet + channel | registry_inclusion | Окроев Игорь Алексеевич |
| **просп. Металлургов, 117** | 2 | channel + memorial.ua | demolition | Каргаполов Борис Павлович, Євген Бондарев |

### The flagship new finding: просп. Ленина, 127 (пр. Мира, 127)

The single strongest new property, from memorial.ua alone —
**demolition *and* reallocation both on file**, matching the modality this
project documents most closely (site cleared, then handed to a developer),
with two named victims and a first-person account:

- **Ганна Гулінська** — sheltered in the basement with her mother and
  brother; the building took a direct airstrike hit on the morning of
  11.03.2022; her body was never recovered, only personal effects.
- **Володимир Роменський** (b. 03.03.1977, Mariupol) — ran a shop,
  "Славутич," at this address; killed the same morning, same building.

Source: https://memorial.ua/obituaries/civilians/hulinska-hanna-5417 and
https://memorial.ua/obituaries/civilians/romenskyi-volodymyr-7067
(scripts/305–307 capture). This property has no
prior mention anywhere in this project's case studies and is a strong
standalone candidate for its own case study or exhibit vignette —
demolition + reallocation + two named, independently documented victims is
the same evidentiary shape as Nakhimova 82 (MUP-CS-001) and Ленина
104–110 (MUP-CS-002).

**Update, 2026-07-12 (Case 9 collapse-entombment sweep):** a *third*,
independent source corroborates the same building on the same date — a
@mariupolRIP post names the entire **Зуй family — Назарчик, Иришка and
Серёжа** — found under the collapsed structure ("Найдены под завалами
мира-127"), estimating their deaths at 11.03.2022, the identical date
memorial.ua gives for Гулінська and Роменський. Two months of searching
followed; unlike the other named victims at this address, the Зуй family's
remains *were* recovered and the post records them being properly reburied
the same day in Makeevka, where they had lived before the war. Source:
https://t.me/mariupolRIP/21333. This raises the confirmed toll at this one
address to **five named victims across two independent sources**, and
supplies the clearest example in this project's data of the counter-case —
a family whose remains a demolition-and-reallocation site did *not* end up
burying, because they were found and moved in time.

### Cross-reference to MUP-CS-005 (Троянда-М, просп. Металлургов, 47)

The existing Троянда-М case study documents eight named victims at this
address (Фёдорова Надежда, Харакоз Наталья Георгиевна, Тёрин Александр
Евгеньевич, Тёрина Елена Александровна, Иванов Максим Владимирович,
Паскаль Мария, Галушко Андрей, Горлачова Раиса Дмитриевна). The channel
scan surfaced a **ninth name not previously in that case study: Калина
Сергей Сергеевич**, killed 24.03.2022, referenced in two separate
anniversary tribute posts (2024 and 2025) as having died "на Металлургов
47." Neither post gives further detail (cause, burial location) beyond the
address and date. **Not yet added to MUP-CS-005 or its exhibit** — flagged
here as a backport candidate; the two tribute posts alone are thinner
sourcing than the case study's existing eight names, each of which has a
dedicated capture (scripts/239–240).

### Distinct-harm finding: bodies removed from an informal grave (Азовстальская, 164 — unconfirmed address link)

See the Азовстальская section under Case 6 above — a mariupolRIP post and
a memorial.ua obituary, very likely describing the same person (matching
name, death date, and birth-year arithmetic) but the memorial.ua account's
mass-grave/bodies-disappeared detail carries no address, so it is
documented but explicitly **not** claimed as evidence for any specific
property until a named address can anchor it.

### What Case 8 adds beyond Cases 1–7

Cases 1–7 were constrained to the 91 EISZhS new-build objects — they can
only ever show what happened where a new building is now standing. Case 8
checks against *every* seizure_event stage, so it surfaces the
`registry_inclusion` and `ownerless_designation` tracks (71 of 116
properties here) that Cases 1–7's method structurally could not see: a
building where a resident was informally buried and the surviving
apartments were later stripped of title flat-by-flat, with no demolition
and no new construction to search for. This is the more common pattern in
this project's data overall (STATS.md: registry_inclusion is the largest
single stage at 12,948 events, demolition 580) — Cases 1–7's demolition-
and-new-build-anchored method was, by construction, sampling the rarer of
the two tracks.

---

## Case 9 — Collapse-entombment (2026-07-12): bodies never recovered from beneath their own buildings

**A body entombed under a collapsed building and a body informally buried
in a courtyard are the same category of harm for this project's purpose:
unexhumed human remains at a specific address, at risk of being built over
without proper exhumation and reinterment if that address is later cleared
and redeveloped.** Cases 1–8 above were scoped to courtyard/yard-style
informal burial specifically — Case 8's own classifier explicitly tracked
"tело лежит, не захоронен" (remains left in place, never buried) as a
*separate*, excluded category rather than counting it as a grave. This
case folds that excluded category back in as its own, equally-weighted
evidence class.

### Method

`scripts/313_mariupolrip_collapse_death_leads.py` re-scans the same
5,961-message @mariupolRIP parse (scripts/302–303) Case 8 used, this time
for collapse-entombment language (завалило/обвалилось/обрушилось/под
завалами/засыпало/погребен/под обломками/etc.) rather than courtyard-
burial language, address-matches each hit against the property spine the
same way scripts/304 and Case 8 do, and checks every matched property for
seizure events. Posts that also contain explicit later-exhumation/
reburial language (перезахорон*) are excluded — those are closed cases,
not at risk from future redevelopment. Full output:
`data/reports/mariupolrip_collapse_death_leads.csv`.

### Result: 104 collapse-entombment posts, 17 properties, 16 with a seizure event

| Address | Seizure stage(s) | Named victims |
|---|---|---|
| **пр. Нахимова, 101** | demolition (order 56, 29.09.2022) + **reallocation (70 flats, СЗ ТЕМП, COMMISSIONED)** | Липка Татьяна Николаевна, Липка Полина Александровна (кв.38) |
| **просп. Ленина, 127** | demolition (order 56, 29.09.2022) + reallocation (159 flats, СЗ МИРАСТРОЙ, under construction) | see flagship update above — 5 named, 2 sources |
| ул. Металлургическая, 19 | demolition (order 32, 27.08.2022) — no reallocation yet | see mass-casualty finding below |
| ул. Митрополитская, 98 | demolition (order 236, 05.05.2023) | Кристина (25 школа) + her family + younger sister |
| просп. Строителей, 109 | ownerless_designation | Прокопчук Жанна Владимировна (3rd stairwell) |
| ул. Куприна, 69 | demolition | Лукашевич Станислав Георгиевич |
| ул. Героическая, 29 | demolition | Рубец Валентина Петровна; Пешехонова Оксана (2 separate posts, same address) |
| ул. Николаевская, 43 | demolition | Терпан Людмила Николаевна |
| ул. Азовстальская, 9 | demolition | Ткачёв Антон, Ткачева Евгения |
| ул. Артёма, 130а | demolition | Урожай Владимир Александрович |
| ул. Ломизова, 11 | demolition | Недилько Виктор Павлович |
| ул. Гурьевская, 50а | registry_inclusion | Приходченко Татьяна Георгиевна |
| ул. Московская, 61 | reclaim;registry_inclusion | Амельчакова family (mother + 2 daughters + niece — building-collapse companion case to the courtyard/basement deaths already on file for this address) |

Order **№56 (29.09.2022) demolished both Нахимова 101 and Ленина 127** —
the same batch demolition order covers both of this case's two strongest
new-construction matches.

### Нахимова, 101 — an occupied building now stands on an unexhumed collapse site

The strongest single finding in this case: Липка Татьяна Николаевна and
Липка Полина Александровна died under rubble at кв.38 on 18.03.2022, "место
захоронения неизвестно, находились под завалами" — no recovery, no burial
recorded anywhere in this project's sources. The предecessor building was
demolished under order №56 (29.09.2022), and a 70-flat replacement by СЗ
ТЕМП (eisghs id 62529, RPD 93-000013) is now **commissioned** — occupied,
not merely under construction. Source: https://t.me/mariupolRIP/8607.

### Mass-casualty finding: ул. Металлургическая, 19 (basement collapse, 23.03.2022)

Thirteen separate @mariupolRIP posts (2022–2026 reposts included) describe
a single basement-shelter collapse at this address on the morning of
23.03.2022, after an airstrike. Contemporaneous and later posts give
inconsistent headcounts for the total sheltering in the basement — "40
человек" (msg 37592), "там ещё 42 человека" (msg 15720), "ещё там погибли
52 человека, 5 или 6 семей с детками" (msg 56275) — no single figure is
independently confirmed, so none is asserted here as the toll; what is
consistent across all thirteen posts is that this was a multi-family,
multi-day mass-casualty event, not an isolated death. Named victims
recovered across the thread:

- **Матвеева Елена Григорьевна** (02.09.1967–23.03.2022) — three separate
  tribute posts (msgs 15720, 44458, 51186) across three anniversaries.
- **семья Судак** — Кристина, Евгений, and daughters Софья и Аня (msg 19663).
- **семья Куцовых** (msg 20887).
- **2× семья Заднепровские** (msg 21222).
- **семья Кубай** — Ирина (Панкина), her son Миша, and mother Надежда;
  Ирина's grandmother had died at the same address a week earlier in a
  separate fire (msg 33013).
- **Маркина Светлана** (30.07.1949–23.03.2022) (msg 56275).

The property (id 6242) has a demolition order on file (№32, 27.08.2022)
but **no reallocation/new-build match yet** — unlike Нахимова 101 and
Ленина 127, this site's post-demolition fate is presently unresolved on
this project's spine. Given the scale described, this is the strongest
open candidate in this case for its own dedicated follow-up (satellite
imagery of the current lot, a targeted EISZhS/land-grant search for this
specific cadastral block) rather than a closed finding.

### The Митрополитская cluster (open lead, tied to the Жигули landmark)

Independently of this collapse-language sweep, a specific query for
**Большаков Даниил Дмитриевич** (mariupolRIP msg 7870; corroborated by
memorial.ua, https://memorial.ua/obituaries/civilians/bolshakov-danil-3968)
located his death only to "район маг. Жигули" — the "Жигули" auto-parts
shop, confirmed via Yandex Maps at **ул. Митрополитская, 110**. Two
collapse-entombment posts on the same street bracket that address almost
exactly: **Митрополитская, 98** (Кристина + family + younger sister,
demolished under order №236, 05.05.2023 — see table above) and
**Митрополитская, 108** ("обрушились этажи с 5 по 1," msg 43637 — not yet
on the spine, no property record for house 108 exists yet). Большаков's
own building is not yet pinned to a specific house number; the 98/108
cluster around the shop at 110 is the strongest available circumstantial
anchor and the first place to check once an exact address surfaces.

---

## Summary table

| Case | New-build(s) | Status | Recorded deaths at/near site | Graves |
|---|---|---|---|---|
| пр-кт Строителей 70 → Резиденция II | 65280 (ПОРФИР) | **Commissioned** | 2 (CO poisoning + suicide) | Орфей removal |
| ул. Зелинского / ЖК Нахимовский zone | 66986-66989, 71399/400, 71846-71850 | Under construction | 14+ named (incl. 10-person basement event) | 3 courtyard/green-zone graves at д.98/15/110 |
| ул. Куприна 9А Теплосети | 66293 (ОЛИМПСТРОЙ), 66292 (СИРИУС БИЛД → д.69), 69766 (АНТАРЕС → д.63+65 combined) | Under construction | 4-victim single-building fire at д.65 + 1 at д.77 + airstrike at д.19 | **13 documented graves** at named site |
| б-р Шевченко green strip | 66545 (ОЛИМПСТРОЙ), 70024 (ВОЗРОЖДЕНИЕ) | Under construction | 4+ direct deaths on boulevard | **6 roadside graves д.270, 5 at д.252**, others along strip |
| ул. Латышева | 71674 (ПОРФИР) | Under construction | 2 insulin deprivation + others | Burial site at "Новая почта Латышева 35а" |
| **Meduza gravedigger cross-section** (Победы 32/42, Строителей 160, Солнечная 8, **Металлургов 96/98**, Пашковского 65) | ЖК "Ленинградский квартал" (15 МКД, СЗ СУ-2007) on Металлургов; ПОРФИР/СОЛНЕЧНАЯ on Строит./Солн. | 8 commissioned, 7 under construction | Named deaths at all 5 streets, eyewitness (Дема); Металлургов: Сошенко family + others buried in courtyard | **121 ownerless apts** (Металлургов 96/98), 47 (Строит. 160), 537 (Азовст.); independent JN source published June 2022 |
| **пр-кт Строителей 74–88 → "Резиденция Селект" (5 МКД)** | 69427/69749/69751/70147/70142 (СЗ-1 ПОРФИР) | Under construction | 27 households displaced (occupation's own list) | **5 courtyard grave-sites** at 5 consecutive addresses; decrees 390–394 (sequential); 828 new flats planned |
| **Case 8 — citywide sweep (116 properties)** | n/a — spine-wide, not new-build-anchored | 59 demolition, 54 registry_inclusion, 17 ownerless_designation, 11 reclaim, 1 reallocation, 1 expropriation | 116 properties, 160 evidence items, 3 independent sources | 11 properties corroborated by 2 sources; flagship: **просп. Ленина 127** (demolition+reallocation, 5 named, 2 sources) |
| **Case 9 — collapse-entombment (17 properties)** | n/a — collapse-death language, not new-build-anchored | 16 with a seizure event; 2 with reallocation | 104 posts, 17 properties matched to spine | flagship: **пр. Нахимова 101** (demolition+reallocation, **commissioned/occupied**, 2 named); open lead: **Металлургическая 19** mass-casualty basement collapse (6+ named families, headcount claims 40–52 unconfirmed) |

---

## Evidence status and next steps

All death/burial records cite mariupolRIP Telegram channel posts,
victims.memorial/memorial.ua entries, or the mariupoldestruction.com
named-victims sheet — open-source, third-party provenance. They are
corroborating evidence of pre-seizure human presence and civilian harm at
these addresses, not legal title documentation.

For RD4U / Rome Statute purposes the relevance is:
- Confirms buildings were occupied (residents sheltering in basements,
  dying at home addresses) immediately before demolition/reallocation.
- Documents that new construction sites were active civilian refuge
  zones during the siege, strengthening the "forced displacement"
  element of the property-seizure chain.
- The Зелинского д.98/110 and Куприна 9А cases involve deaths of
  multiple people in basements/shelters — establishing these were
  occupied structures, not abandoned/ownerless property.
- Case 8 (2026-07-12) extends this beyond demolition/new-build sites to
  the `registry_inclusion`/`ownerless_designation` track — 71 of its 116
  properties never had a demolition order at all, meaning the informal-
  burial evidence there specifically rebuts the "ownerless" legal
  predicate for standing buildings with surviving, title-stripped
  apartments, not just cleared lots.

**Immediate follow-ups:**
1. Load the five case-study buildings into the `corroboration` table as
   `testimony_ref` or a new `victim_record` family once a loader script
   is built.
2. **DONE (2026-06-16):** Зелинского д.110 confirmed in minstroy
   demolition register (Распоряжение администрации №144, 12.12.2022).
   Зелинского д.15 confirmed (ГКО №56, 29.09.2022). д.98 absent from
   demolition register and absent from ownerless registry (except д.98А
   кв.15) — fate of this building TBD; may be partially standing.
   Chain for д.110 and д.15: death → demolition order → land cleared
   → developer reallocation → new construction. **Chain closed.**
3. Recover full text of Договор аренды №138 (Зелинского / ЖК
   Нахимовский lease) — currently only captured via RPD PDF reference.
4. Verify Куприна 9А burial site location vs cadastral map — is it
   within the footprint of any demolition-registered or land-granted parcel?
5. **DONE (2026-06-16): Металлургов 96/98 cadastral follow-up.** Cadastral parcel
   93:37:0010110:259 is NOT д.96/98's own plot — the ЖК "Ленинградский квартал"
   buildings are on the cleared odd-side plots (demolished д.79–91), ~50–130m from
   д.96/98. д.96/98 are being processed via ownerless registry (title-stripping track).
   Dual-track pattern confirmed on Металлургов, same as Зелинского. See Case 6 above.
6. Capture the Meduza article via SHA-256 to `data/raw/` for evidentiary chain of
   custody; add to corroboration table as `testimony_ref` provenance.
7. **Строителей 74–88 (Case 7):** Recover decree texts for land-grant decrees
   390–394 from the Пушилин archive (script 39 --archives-only already captured
   the PDF set; grep for these decree numbers). Confirm dates and confirm the five
   parcels (6088/6089/6160/6161/6162) are sub-divisions of the pre-war block cadastral.
   Add victim-record corroboration rows for the five grave-site entries once a loader
   is built. Obtain pre/post satellite chips via Wayback pipeline (scripts 57–58) to
   confirm demolition has occurred and new foundations are visible.
8. **Case 8 (2026-07-12):** просп. Ленина 127 — verify as a standalone
   case-study candidate (next accession MUP-CS-011): recover the land-grant
   decree and developer identity behind the `reallocation` event, satellite
   imagery for the demolition, and check for a third corroborating source.
9. Backport Калина Сергей Сергеевич (d. 24.03.2022) to MUP-CS-005
   (Троянда-М / Металлургов 47) as a ninth named victim, pending a stronger
   source than the two tribute posts currently on file.
10. Азовстальская 164 / Звягинцев: attempt to locate the specific address
    of the shell-crater grave described in the memorial.ua account (family
    contact, if traceable, or a third source) before treating the two
    accounts as confirmed to be the same person and the same property.
11. Build a `victim_record`-family loader for `grave_sites_master_evidence.csv`
    (160 rows) so this evidence enters the `corroboration` table like the
    project's other source families, rather than living only as a CSV
    report. Extend the small UA→RU street dictionary (scripts/307) as more
    Ukrainian-language sources are added — check each new entry against the
    spine before use, per the existing 10-entry table's convention.
12. **Case 9 (2026-07-12):** get satellite imagery (Wayback pipeline,
    scripts 57–58) or an EISZhS/land-grant search for the specific
    cadastral block under ул. Металлургическая, 19 — the mass-casualty
    basement collapse has a demolition order but no reallocation match yet,
    unlike Нахимова 101 and Ленина 127. Also worth a standalone effort to
    independently verify the 40/42/52 headcount claims (occupation
    emergency-services records, if any surface) rather than leaving three
    unreconciled figures on file.
13. **Case 9:** confirm Большаков Даниил Дмитриевич's exact house number on
    ул. Митрополитская (currently only "район маг. Жигули," pinned to
    Митрополитская, 110 via Yandex Maps) — the Митрополитская 98/108
    collapse cluster brackets that address and is the first place to check.
    Митрополитская, 108 has no property record on the spine at all yet and
    needs its own geocoding pass regardless of the Большаков link.
14. Fold `data/reports/mariupolrip_collapse_death_leads.csv` (scripts/313,
    104 rows) into the same future `victim_record` loader as item 11 above,
    with a `death_modality` column distinguishing courtyard burial from
    collapse-entombment — the two are one evidence class for this case
    study's purpose but worth keeping distinguishable in the data model.
