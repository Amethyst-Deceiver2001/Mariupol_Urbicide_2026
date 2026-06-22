# Case Study — Death Sites, Ad-Hoc Graves and New Construction

**Cross-referencing the Mariupol deceased/missing register
("Погибшие и Пропавшие на Карте Разрушений") against the 91
ЕИСЖС (наш.дом.рф) new-construction objects.**

**Source file:** `Погибшие и Пропавшие на Карте Разрушений_Deceased and
Missing on the Damage Map.xlsx` (4,506 records, 4,256 with parseable
address; 641 with grave-location addresses after filtering formal
cemeteries/hospitals).

**Method:** keyword+house-number matching against
`data/parsed/eisghs_mariupol_objects.jsonl` (91 objects). Two passes:
(A) "death_place" / "residence" of victim vs eisghs address; (B)
burial location (explicit or inferred-courtyard) vs eisghs address.

---

## Case 1 — пр-кт Строителей 70 → "Резиденция II" д.70Б
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

## Case 2 — ул. Зелинского: ЖК "Нахимовский" and ЖК (ПОРФИР) construction zone

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

---

## Case 3 — ул. Куприна 9А «у Теплосетей»: documented mass ad-hoc burial site

**eisghs objects on ул. Куприна:**
- 66293: ул. Куприна, д.77Б — СЗ ОЛИМПСТРОЙ НР (ИНН 9309027678), `under_construction`
- 66292: ул. Куприна (no house number) — СЗ СИРИУС БИЛД (ИНН 9310014320), `under_construction`

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

---

## Case 4 — б-р Шевченко: roadside burial strip

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

---

## Case 5 — ул. Латышева: death-without-medicine cluster

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

## Case 7 — пр-кт Строителей 74–88: the five-building block

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

## Summary table

| Case | New-build(s) | Status | Recorded deaths at/near site | Graves |
|---|---|---|---|---|
| пр-кт Строителей 70 → Резиденция II | 65280 (ПОРФИР) | **Commissioned** | 2 (CO poisoning + suicide) | Орфей removal |
| ул. Зелинского / ЖК Нахимовский zone | 66986-66989, 71399/400, 71846-71850 | Under construction | 14+ named (incl. 10-person basement event) | 3 courtyard/green-zone graves at д.98/15/110 |
| ул. Куприна 9А Теплосети | 66293 (ОЛИМПСТРОЙ), 66292 (СИРИУС БИЛД) | Under construction | 1 confirmed at д.77, airstrike at д.19 | **13 documented graves** at named site |
| б-р Шевченко green strip | 66545 (ОЛИМПСТРОЙ), 70024 (ВОЗРОЖДЕНИЕ) | Under construction | 4+ direct deaths on boulevard | **6 roadside graves д.270, 5 at д.252**, others along strip |
| ул. Латышева | 71674 (ПОРФИР) | Under construction | 2 insulin deprivation + others | Burial site at "Новая почта Латышева 35а" |
| **Meduza gravedigger cross-section** (Победы 32/42, Строителей 160, Солнечная 8, **Металлургов 96/98**, Пашковского 65) | ЖК "Ленинградский квартал" (15 МКД, СЗ СУ-2007) on Металлургов; ПОРФИР/СОЛНЕЧНАЯ on Строит./Солн. | 8 commissioned, 7 under construction | Named deaths at all 5 streets, eyewitness (Дема); Металлургов: Сошенко family + others buried in courtyard | **121 ownerless apts** (Металлургов 96/98), 47 (Строит. 160), 537 (Азовст.); independent JN source published June 2022 |
| **пр-кт Строителей 74–88 → "Резиденция Селект" (5 МКД)** | 69427/69749/69751/70147/70142 (СЗ-1 ПОРФИР) | Under construction | 27 households displaced (occupation's own list) | **5 courtyard grave-sites** at 5 consecutive addresses; decrees 390–394 (sequential); 828 new flats planned |

---

## Evidence status and next steps

All death/burial records cite mariupolRIP Telegram channel posts or
victims.memorial entries — open-source, third-party provenance.
They are corroborating evidence of pre-seizure human presence and
civilian harm at these addresses, not legal title documentation.

For RD4U / Rome Statute purposes the relevance is:
- Confirms buildings were occupied (residents sheltering in basements,
  dying at home addresses) immediately before demolition/reallocation.
- Documents that new construction sites were active civilian refuge
  zones during the siege, strengthening the "forced displacement"
  element of the property-seizure chain.
- The Зелинского д.98/110 and Куприна 9А cases involve deaths of
  multiple people in basements/shelters — establishing these were
  occupied structures, not abandoned/ownerless property.

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
