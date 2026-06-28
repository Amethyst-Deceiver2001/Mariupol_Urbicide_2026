# Case Study — prosp. Lenina (Myru), 104/106/108/110 — Restoration Without Restitution

**Four contiguous war-damaged buildings, all four named in one demolition
decree, with WILDLY DIFFERENT physical fates — 106 restored in place,
scaffolded and re-plastered with the original residents physically barred
from the site; 108 only partially demolished (one entrance/section torn
down, the rest of the tower left standing); 104/110 not confirmed razed at
all — yet hundreds of apartments across ALL FOUR are individually stripped
via the ownerless registry regardless of which of these very different
physical realities actually applies.**

A visual + documentary evidence package is at
`data/exports/designer_package/lenina_104_106_108_110/` — see its
`manifest.csv` for every file's SHA-256, date, and caption. **30 files as of
2026-06-19**, after ten rounds of manual correction and addition (see
Provenance below for the full inventory). Every cited artifact is included
as actual visual material, not just a reference — multi-page PDFs have a
rendered first-page JPEG thumbnail alongside the original (`pdftoppm`,
poppler) so a designer/reviewer never has to open a PDF to see what it is.

The package contains: confirmed wartime-destruction imagery for 104
(street-facade AND courtyard angles, March/May 2022 + 2023), 106
(former ATB supermarket + burnt balconies, May/June 2022, plus a less-severe
courtyard view consistent with its later restoration), and 108's partial
demolition; a distant restoration-in-progress frame for 108; a 1979 prewar
baseline photo for 110 (Pastvu); resale-listing evidence for 106, 108, and
110; an on-camera resident-testimony video (all four buildings, naming the
same contractor chain as the documents below and alleging halted work,
altered apartment layouts, and ground-floor commercial space let to
businesses while residents are locked out); and a fenced-but-idle
stalled-reconstruction walkthrough that visually corroborates that halted-
work claim. One candidate video was EXCLUDED despite a title mentioning
house numbers 104/106: it turned out to be prosp. Pobedy (Victory Avenue), a
different street entirely that coincidentally shares house numbers — real
siege damage, wrong building; see
`memory/lifecycle_classifier_unreliable_siege_damage.md` for the full record
of caption/title-trust failures found across this case study's media review,
including a Telegram resale listing originally misattributed to 108 by
inference before its content was actually seen — it was 110.
Non-chat corroboration on spine also includes `unosat_damage` rows for 104
and 108, and a resident's own testimony text for 106 ("The building was
damaged, after the fighting..." — `Lenina106_Mariupol/42`).

Unlike the demolish→rebuild→resell pattern documented for prosp. Nakhimova 82
(`docs/case_studies/nakhimova_82_chernomorsky_1b.md`), **106** was never
physically destroyed in the way its own paper trail says it was: the
occupation's own demolition register lists a decree ordering it razed; the
occupation's own residents' chat (and now confirmed YouTube siege footage
from 2022, predating the restoration) shows it standing, scaffolded, and
being re-plastered a year later. **108**, however, genuinely WAS partially
demolished — confirmed on video, excavator actively tearing down one
entrance/section while the rest of the tower stands. Three different
buildings, three different physical outcomes (restored / partially razed /
unconfirmed), but **all processed identically through the registry** — the
ownerless-designation pipeline does not appear to track, or care about,
which of these very different fates actually applied to which units. Both
records are the occupier's; they contradict each other and the buildings'
actual mixed condition; neither asked the original owners. This is the
project's reference example of a second, distinct seizure modality:
**administrative erasure that outruns and ignores physical reality — even
when that reality itself varies building-to-building within the same
decree.**

---

## The four properties

All four are named individually in **State Defense Committee (GKO) DNR
Directive No. 56, 29.09.2022** (each as a separate line item, "Zdanie
zhilogo doma" — residential-building entry) and collectively in the
residents' joint letter (below). District: Zhovtnevy for all four.

| Address | property_id | building_id | RD4U | Registry-inclusion events | Demolition decree line | Geocode | Confirmed physical fate |
|---|---|---|---|---|---|---|---|
| prosp. Lenina 104 | **4417** | `AVENUE:ленина\|104` | A3.1, A3.6 | 71 | "g. Mariupol, prosp. Lenina, d. 104 (Zdanie zhilogo doma)" | 47.0981236, 37.5225087 | Siege damage confirmed (2022, video); demolition NOT confirmed |
| prosp. Lenina 106 | **4419** | `AVENUE:ленина\|106` | A3.1, A3.6 | 72 | "g. Mariupol, prosp. Lenina, d. 106 (Zdanie zhilogo doma)" | 47.0982211, 37.5211384 | Siege damage confirmed (2022, video); restored in place, never razed |
| prosp. Lenina 108 | **4421** | `AVENUE:ленина\|108` | A3.1, A3.6 | 76 | "g. Mariupol, prosp. Lenina, d. 108 (Zdanie zhilogo doma)" | 47.098342, 37.5193585 | **Partially demolished** (1 entrance/section, video-confirmed) — NOT fully razed |
| prosp. Lenina 110 | **4423** | `AVENUE:ленина\|110` | A3.1, A3.6 | 64 | "g. Mariupol, prosp. Lenina, d. 110 (Zdanie zhilogo doma)" | 47.0984355, 37.5180284 | No visual evidence yet |

**283 registry_inclusion events across the four buildings** (apartments
individually processed as "ownerless"), each backed by a `demolition`
seizure_event dated **2022-09-29** citing the same decree number (56) — i.e.
the same administrative contradiction documented for 106 below applies to
all four: a demolition order on file, apartments still being individually
stripped via the registry, and (per the joint letter) the buildings
demonstrably still standing and under renovation more than a year later.

106 has the deepest evidence (the only chat dedicated to a single building in
this group; 125 apartment-level disappearances independently matched against
its spine demolition event via script 150's temporal differential — see
below). 104/108/110 are corroborated by the same joint letter, the same
decree, their own registry_inclusion counts, and house-number-specific chat
mentions (see the visual evidence package) — full per-apartment differential
analysis for 104/108/110 is the natural next step (gap register methodology
already exists, just needs re-running scoped to these three building_ids).

---

## The contradiction at the center of the case

### Track 1 — On paper, demolished
**State Defense Committee (GKO) DNR Directive No. 56, 29.09.2022** lists "g.
Mariupol, prosp. Lenina, d. 106 (Zdanie zhilogo doma)" for demolition.
- **Source:** DNR MinStroy open-data demolition register (snapshot 16.03.2026).
- **Artifact:** `minstroy-dpr.gosuslugi.ru/.../reestr-snosa_16_03_2026.csv` ·
  SHA-256 `d431a530…42ea37` · captured 2026-06-09.
- **DB:** `seizure_event` 54064, stage `demolition`, date **2022-09-29**, confidence 0.90.

### Track 2 — On the ground, restored, not razed
The building's own residents' Telegram chat (`@Lenina106_Mariupol`) shows
restoration work in progress thirteen months after the demolition decree —
**not** a cleared lot, **not** a new construction site:

> 2023-10-05: *"Строители говорят закончат тепловой контур к концу года. Уже
> в некоторых квартирах ведутся штукатурные работы. В сам дом никого не
> впускают."* ("Builders say they'll finish the thermal envelope by year's
> end. Plastering is already underway in some apartments. Nobody is let into
> the building itself.")
> — chat msg, SHA-256 `61be44fe…` (photo), 2023-10-05

> 2023-10-18: *"Мы подходили к дому, действительно, ни то, что в дом, даже во
> двор не пускают. Фотографировать не разрешают."* ("We went up to the
> building — indeed, they don't let you into even the yard, let alone the
> building. Photography isn't allowed.")
> — chat msg, SHA-256 `3aa8d569…`, 2023-10-18

> 2023-10-05, a resident directly rebuts the demolition premise: *"Почему вам
> не вернут вашу квартиру? Если вы собственник и есть документы.... дом то не
> сносили..."* ("Why won't they give you back your apartment? If you're the
> owner and have the documents... the building wasn't even demolished...")
> — chat msg, SHA-256 `b20d2bf2…`, 2023-10-05

*(Methodological note: an earlier automated keyword pass mis-tagged this last
message as "demolition" evidence — the regex matched the verb stem `снос-`
inside "не **снос**или" without detecting the negation. Manually verified
before citing here; flagged in `memory/` so future automated lifecycle
classification is cross-checked against caption sense, not just keyword
presence, before being used in a case study.)*

### Track 3 — On paper again, 91 apartments individually erased anyway
Independent of which of Tracks 1/2 is physically true, the ownerless registry
mechanism processed **91 distinct apartments** in this building as
"ownerless" across four dated snapshots, all while residents were
demonstrably alive, organized, and petitioning for their homes:

- **72 apartments**: `registry_inclusion` events already on the spine
  (source: Zhovtnevy-district ownerless registry XLSX,
  `mariupol-r897.gosweb.gosuslugi.ru/.../Zhovtnevyi_r_n.xlsx`,
  SHA-256 `add72b41…85cfeae`).
- **125 apartment-level entries** appear in the 2024-09-02 / 2025-01-13 /
  2025-11-09 / 2025-11-15 dated snapshots (script 150's temporal
  differential) with **no disposition marker and no owner-return record** —
  classified `seized_court` because they match this building's spine
  `demolition` event, i.e., the registry continued processing apartments in
  a building its own demolition order claims no longer exists.
  Apartments affected (by number): 3,4,5,6,7,9,10,11,12,13,14,15,16,19,20,21,
  24,25,26,27,28,29,30,31,32,34,42,44,47,48,49,51,52,54,56,58,60,62,63,64,65,
  66,67,68,71,72,73,76,78,79,80,82,83,84,85,88,89,92,93,94,95,96,97,99,100,
  101,102,103,105,110,111,113,114,116,121,124,125,126,128,129,132,133,137,
  138,140,143,145,148,149,150,153,157 — 91 unique apartment numbers across
  both tracks combined.

---

## Track 4 — the human cost

Independent of any of the paper tracks above, residents of these buildings
died during the siege and in the months after, while the buildings' legal
status was being contested on paper. A 6-person casualty record — titled
"Погибшие 6ч. Мира, 110" and attributed to mariupoldestruction.com — was
supplied 2026-06-19 and corroborated against the named individuals' own
memorial posts:

1. **Anatoly Glushko** (Глушко Анатолий Петрович, 01.07.1937–17.03.2022) —
   died in a basement from a blast head injury; the body was moved to the
   apartment but could not be buried due to ongoing shelling.
   (`t.me/mariupolRIP/36979`)
2. **Yevgeny Khildunin** (Хильдунин Евгений Александрович, b. 17.05.1985) —
   died in the building; body moved to a shoe shop, collected by emergency
   services before Easter. (`t.me/mariupolRIP/37382`)
3. **Anatoly Malyukha** (Малюха Анатолий, b. 1943, disabled) — "burned
   alive," per a neighbor's account; no independent source link supplied
   beyond the user-relayed quote.
4. An unnamed sister of **Inga Kovalenko** (Коваленко Инга Евг., b. 1975) —
   sniper-killed near the 3rd entrance on 24.03.2022; body lay in place for
   three days; her identity documents and phone were later sold and used
   (16.04.2022) to fraudulently obtain humanitarian aid in her name.
5–6. **Pyotr Afonin** and **Klavdiya Afonina** (Афонин Пётр, Афонина
   Клавдия) — residents of prosp. Lenina 110, apt. 127.

A makeshift grave was separately documented in **106's courtyard**, and a
not-yet-located video reportedly shows bodies wrapped in blankets in
**108's courtyard** — kept on record as an unverified lead
(`youtube.com/watch?v=AmPu1gRLh-M`), not cited as evidence, until the
original source is found.

Given that the document title and most named individuals point to building
110 specifically, but the grave is at 106 and the bodies-video lead is at
108, this record is loaded as a **shared finding across all four
buildings** (`corroboration.kind = 'civilian_casualty'`, property_ids
4417/4419/4421/4423) rather than pinned to one — see
`scripts/163_load_lenina_casualty_record.py`. This is not subject to the
project's living-owner privacy minimization rule; these are named deceased
civilians from a public memorial dataset, and naming them is the
documentary point.

---

## The residents' own collective record — a letter to Putin

A joint petition, captured verbatim from the chat (`Письмо в инстанции.pdf`,
SHA-256 `fe670bca…77f8f36`, 2023-10-18), addressed to:

> President of the Russian Federation Vladimir Putin (Путину В.В.) · RF
> Minister of Construction Irek Faizullin (Файзулину Э.Ф.) · DNR Minister of
> Construction N.M. Tsyganov (Циганову Н.М.) · Mariupol City Prosecutor A.V.
> Polishchuk (Полищук А.В.) · Mariupol Mayor O.V. Morgun (Моргуну О.В.)
> — signed "Residents of buildings 104, 106, 108, 110, Mariupol, prospekt
> Lenina" ("Жильцы дома 104, 106, 108, 110, Мариуполь, проспект Ленина")

names the responsible parties directly:

> Developer: **Ministry of Construction of the Russian Federation**
> Client: **public-law company (PPK) «Edinyi zakazchik v sfere
> stroitelstva»**
> General contractor: **LLC (OOO) «RKS-NR»**

and documents, in residents' own words, nine months of renovation with no
resident access and no quality oversight: facades and roofs redone while the
burned-out interior remains untouched ("внутри квартир все также обгорелые
остатки конструкций"); makeshift worker latrines installed inside apartments
and kitchens; a fire on site; a 10cm heating riser replaced with thinner pipe;
windows installed with gaps "such that no amount of foam sealant will fix it";
a leaking roof in the rainy season.

This is the same federal contractor chain (OOO RKS-NR / PPK «Edinyi
zakazchik») already named in this project's stakeholder network
(`memory/stakeholder_network.md`) — independent confirmation, from the
residents' side, of the same actors this project has tracked through
official decrees.

An on-camera video (YouTube `CHrEXXI8CK0`, captured 2026-06-19) shows
residents repeating this same complaint directly to camera over a year
later: work halted with no explanation, repeated new subcontractors who do
nothing, ground-floor commercial space already let to a bank/flower shop/
pelmennaya while residents still can't access their own apartments, and —
a claim not in the written letter — apartment square footage/wall layout
altered during the works ("the floor area has changed" — "квадратура
изменилась"), potentially relevant to
RD4U unit-boundary valuation if independently corroborated. A separate,
fenced-but-idle walkthrough video (`pmb7BIl-Atw`, cropped to the relevant
1:09–6:42 segment) visually confirms the "halted" claim — rusty perimeter
fencing around the whole stretch, an idle construction hoist mounted on one
facade with no workers or material staging visible.

A second document, **Resolution No. I/3-3, 13.02.2026** (Решение №I/3-3 от
13.02.2026; filename `Reshenie_I_3_3_ot_13.02.2026.pdf`, SHA-256
`02048976…6889e215bd`, captured from the `@invite_ooUT61cOOFZjMDcy`
official-info channel) was previously flagged as a scanned ruling with no
extractable text layer. **Now legible (2026-06-19)** via a first-page render
(`pdftoppm`) plus a full 23-page OCR pass: it is the **Mariupol City Council
(DNR)'s decision to include specific municipally-owned residential units
into the "List of Residential Premises That May Be Provided as
Compensation"** («Перечень жилых помещений, которые могут быть предоставлены
в качестве компенсационных» — the list of housing units that may be issued
as *compensation* — i.e. given to OTHER displaced claimants, not returned to
these units' original owners), citing **DNR Law No. 141-RZ, 18.12.2024**, "On
Supporting Citizens Whose Housing Was Lost as a Result of Combat Operations"
(О поддержке граждан, жилые помещения которых утрачены в результате боевых
действий). OCR across the full appendix
found roughly **10 units at 104, 8 at 106, and 8 at 108** (cadastral numbers
recovered per-row) — **this count is from raw OCR on a dense multi-column
table and has NOT been manually verified row-by-row; treat as a strong lead,
not a confirmed figure**, per this project's standing rule never to cite
automated extraction without verification (see
`memory/lifecycle_classifier_unreliable_siege_damage.md` and
`memory/negation_blind_classifier_caveat.md` for why). 110 did not show a
clean match in this OCR pass.

**If confirmed, this is the missing reallocation/endpoint stage for 104/106/
108** — the apartments these buildings' own residents were registry-stripped
from are being redirected into a compensation pool for a *different*
population of claimants, dated barely four months before this find. This
would directly support the Rome Statute art. 8(2)(b)(viii) population-
transfer reading already argued below, with a specific dated instrument
rather than an inferred pattern. **Next step: a structured per-row
re-extraction (not raw `tesseract --psm 6` on a scanned table) to confirm
exact apartment/cadastral numbers before citing this count as evidence-grade.**

---

## Why this matters — a second seizure modality

Where Nakhimova 82 shows the occupation **physically erasing** a building and
laundering its address to a new development, Lenina 106 shows the occupation
**administratively erasing ownership while the building still stands** —
running a demolition decree, a restoration project, and an individual,
apartment-by-apartment "ownerless" registry process simultaneously, none of
which is reconciled with either of the others or with the residents who are
still there, still organized, and still petitioning the very officials who
authorized the contractor doing the (poor-quality) work.

- **RD4U restitution:** A3.1 (damage) is established by the siege/demolition
  decree; **A3.6** (loss of access) is independently established by the
  documented physical exclusion ("nobody is let into the building itself" —
  "в сам дом никого не впускают") plus the 91
  apartment-level registry actions — residents cannot get inside, let alone
  reassert title, regardless of which paper track is "true."
- **Rome Statute:** The combination of (a) a demolition order that names a
  specific residential building, (b) federal-ministry-funded restoration
  work proceeding without the building's legal owners, using a named
  contractor, and (c) parallel administrative dispossession of 91 named
  apartments, maps to unlawful **appropriation of property** (art.
  8(2)(a)(iv)) and to the broader pattern of population transfer once the
  restored units are reallocated. The reallocation stage is now PARTIALLY
  documented: individual resale listings for 106/108/110 (demand-side,
  ordinary market activity) AND — if the OCR lead above is confirmed — a
  formal municipal decision (Решение №I/3-3, 13.02.2026) redirecting ~26
  specific units at 104/106/108 into a compensation-housing pool for a
  different population, which is the more direct **art. 8(2)(b)(viii)**
  evidence (transfer of the occupier's own population into property taken
  from the protected population) this case study has lacked so far.
- **Civilian harm, independent of either paper track:** six residents of
  this building group are documented as having died during the siege and
  its aftermath (Track 4 above) while the buildings' legal status was being
  contested on paper across the conflicting demolition/restoration/registry
  tracks. This does not change the property-law analysis above, but it is
  the human cost underlying it, and the case study records it as such.

---

## Provenance (chain of custody)

| Claim | DB ref | Source artifact | SHA-256 | Captured |
|---|---|---|---|---|
| Demolition decree №56 | event 54064 | minstroy reestr-snosa_16_03_2026.csv | `d431a530…42ea37` | 2026-06-09 |
| 72 registry_inclusion events | events 37077+ | Zhovtnevyi_r_n.xlsx (gosweb.gosuslugi.ru) | `add72b41…85cfeae` | (loaded pre-session) |
| Residents barred from entry, restoration in progress | corroboration (script 152, kind=lifecycle_media) | `@Lenina106_Mariupol` chat photos/video, msgs 35/36/77 | `61be44fe…`, `89a70c96…`, `3aa8d569…` | 2023-10-05 / 2023-10-18 |
| "дом то не сносили" (rebuts demolition) | corroboration (lifecycle_media, manually re-verified) | same chat, msg 37 | `b20d2bf2…` | 2023-10-05 |
| Joint letter to Putin / RF & DNR construction ministries / prosecutor / mayor | chat_document_inventory (script 149) | `Письмо в инстанции.pdf` | `fe670bca…77f8f36` | captured from chat, dated 2023-10-18 |
| 125 apartment-level disappearances matched to the demolition event | corroboration (script 152, kind=ownerless_disposition), classification=seized_court | ownerless snapshots 2024-09-02/2025-01-13/2025-11-09/2025-11-15 | per-row, see `data/parsed/ownerless_differential_records.jsonl` | 2026-06 |
| FKRMO abandoned 106's repairs after repeated delays from Aug 2024 | corroboration pending (manually verified, not yet loaded) | `@Lenina106_Mariupol` msg 986, handwritten complaint to prosecutor | `74b97bb3…8997bde05` | 2025-06-02 |
| Directive No. 619 (12.10.2023) enforced at 106 specifically | corroboration pending (manually verified, not yet loaded) | `@Lenina106_Mariupol` msg 269, door notice ("На каждой двери") | `1ca8ed3d…361627e05` | 2024-03-27 |
| Siege damage at 104 (ground-floor storefront) | corroboration pending (manually verified, not yet loaded) | YouTube "2022.03.04 - prosp. Myru, d. 104" (Near You) | `3215e47c…04ce604d8f5` | 2022-03-04 |
| Siege damage at 104 (full facade, multi-floor) | corroboration pending (manually verified, not yet loaded) | YouTube shorts/5fuqt-M5S6I | `b1313dae…69fc9822` | 2022-05 |
| Siege damage at 106 (former ATB supermarket) | corroboration pending (manually verified, not yet loaded) | YouTube "Myra, 106, byvshyi ATB" (@MARIUPOLNOW) | `b32d1544…109506a2c` | 2022-06-25 |
| Siege damage at 106 (burnt balconies) | corroboration pending (manually verified, not yet loaded) | YouTube "Prosp. Myra, 106. May 2022." | `c7ffa6b0…1ba8d18c` | 2022-05 |
| **108 partially demolished** (1 entrance/section, rest of tower standing) | corroboration pending (manually verified, not yet loaded) | YouTube shorts/Bzq5QnarNAo "snos doma" (building demolition) | `ea535398…2bb3ccab` | undated |
| 108 distant restoration-in-progress view (courtyard, fenced off) | corroboration pending | YouTube "Mariupol. A ghost town!? prosp. Lenina, 108." (Korzhov Vlog), single frame extracted | `4cb9fe0f…f961173` | 2023-08-23 |
| 108 resale listing (61.3 m², 4/9 floor, 4.5 million rub) | corroboration pending | dnr.red listing, manually saved by user (Save-As zip, anti-bot site) | `53a2850b…550f628b` | listed 2026-06-08, captured 2026-06-19 |
| 108 resale listing (dnr.domick.ru) | **NOT YET captured** — geoblocked, must run from VPS (`scripts/158_*.py`) | dnr.domick.ru, "3-room, prosp. Lenina 108" | pending | cited 2026-06-19 |
| Resale listing, prosp. Lenina 106 (2-room w/ "pereход"/connecting room, 5 million rub) | corroboration pending | `t.me/Mariupol_house/84850` (widget metadata-only; content from user's screenshot) | `2537366d…8bef8c45c` | listed 2024-01-24 |
| Resale listing, prosp. Lenina 110 (3-room, 63.4 m², 3 million rub) | corroboration pending — **CORRECTED 2026-06-19, originally misattributed to 108** | `t.me/Mariupol_house/676643` (widget metadata-only; content from user's screenshot) | `5a9171bd…0b764d550f628b` | listed 2025-12-29 |
| 1979 prewar baseline photo, prosp. Lenina 110 | corroboration pending | Pastvu p/1167758, geotagged ~25m from property 4423 | `10d33e28…313dc821` | 1979, captured 2026-06-19 |
| On-camera resident testimony (all 4 buildings): work halted, altered layouts, ground-floor units let to businesses | corroboration pending | YouTube CHrEXXI8CK0 | `a8e0e253…1ecf4934` | cited/captured 2026-06-19 |
| Fenced-but-idle stalled-reconstruction walkthrough (visually corroborates the testimony above) | corroboration pending | YouTube pmb7BIl-Atw, cropped 1:09-6:42 | `8867e667…38bad019e5e9b117` | cited/captured 2026-06-19 |
| Courtyard-side siege damage, 104 (2nd independent source, 3 frames) | corroboration pending | YouTube fzN0pI8alEY | `867ab498…398749ae7` | cited/captured 2026-06-19 |
| Courtyard-side view, 106 (less severe than 104 — consistent with restoration) | corroboration pending | YouTube fzN0pI8alEY | `867ab498…398749ae7` | cited/captured 2026-06-19 |
| **Civilian casualty record, 6 named deceased** (shared, all 4 buildings) | `corroboration` rows, kind=`civilian_casualty`, loaded 2026-06-19 | mariupolRIP/36979, /37382 + mariupoldestruction.com Google My Maps "Pogibshie" ("the dead") layer | `5c018486…f69d`, `40fec819…d54de`, `c1f20d23…aa17f6` | events 2022, captured 2026-06-19 |
| **Reshenie №I/3-3 (13.02.2026) — compensation-housing list, ~10/8/8 units at 104/106/108** (OCR lead, NOT manually verified) | chat_document_inventory | `Reshenie_I_3_3_ot_13.02.2026.pdf` + first-page thumbnail | `02048976…6889e215bd` | 2026-02-14, OCR'd 2026-06-19 |

*Reproducible from raw → DB. Occupation registrations/rulings/demolition
decrees are evidence of the seizure act, NOT valid title; Ukraine does not
recognize them, and neither do we.*

---

## Open items / follow-up

- **Sister buildings 104, 108, 110**: now documented above (property_ids
  4417/4421/4423, decree line items, registry_inclusion counts, geocodes,
  visual evidence package). Still open: a full apartment-level temporal
  differential for these three (script 150's methodology, applied to 106,
  found 125 individually-corroborated disappearances) hasn't been re-run
  scoped to these three building_ids yet.
- **Reallocation/resale stage — NOW DOCUMENTED for 106/108/110 (2026-06-19)**:
  resale listings captured for 106 (`@Mariupol_house/84850`), 108 (dnr.red,
  manually saved by the user), and 110 (`@Mariupol_house/676643` — corrected
  from an earlier 108 misattribution, plus a 1979 Pastvu prewar-baseline
  photo). **Still outstanding: the dnr.domick.ru listing for 108**
  (`scripts/158_capture_lenina108_resale_listings.py` is ready but must run
  from the Russia-routed VPS, not Claude) — the archive the user saved only
  contained the dnr.red page. **104 still has no identified resale
  activity.** Separately, the OCR'd `Reshenie №I/3-3` decision (above) may
  represent a DIFFERENT, more consequential reallocation channel than
  individual resale — a formal compensation-housing-list designation — for
  104/106/108; this needs the same row-level verification flagged above
  before being treated as confirmed.
- A full apartment-level temporal differential for 104/108/110 (script 150's
  methodology, applied to 106, found 125 individually-corroborated
  disappearances) still hasn't been re-run scoped to these three
  building_ids.
- **OCR gap closed (2026-06-19)**: tesseract + rus.traineddata + poppler +
  pytesseract/pdf2image are now installed (`.venv312`, `pyproject.toml`'s
  `ocr` extra) — used this session to read `Reshenie_I_3_3_ot_13.02.2026.pdf`
  for the first time (see Track 4.5 above). Nakhimova 82's РнВ permit is
  still un-OCR'd.
- **7th YouTube video disposition resolved**: `pmb7BIl-Atw` is the
  fenced-but-idle stalled-reconstruction walkthrough, now in the package.
- **Classifier caution**: see [[lifecycle_classifier_unreliable_siege_damage]]
  if using Claude Code — script 151's automated lifecycle classifier proved
  wrong across every stage tried for this chat (siege_damage, construction,
  house_specific, resident_presence), and even mis-*associated* a caption
  with the wrong file entirely (msg 269, see below), over five manual-review
  rounds. No stage label or caption should be cited without opening the
  actual file AND its raw `.meta.json` sidecar.
- **RESOLVED (2026-06-19)** — the two artifacts above were already
  forensically captured (`@Lenina106_Mariupol/986` and `/269`); they just
  hadn't surfaced through the lossy classifier pipeline. Both now have their
  own `106/key_artifacts/` folder in the visual package:
  - `2025-06-02_prosecutor_complaint_fkrmo.jpg` — a resident's handwritten
    complaint to prosecutor D.V. Gnezdilov (Гнездилов Д.В.) about FKRMO
    (ФКРМО — Fond kapitalnogo remonta Moskovskoi oblasti, "Moscow Region
    Capital Repair Fund") repeatedly pushing back 106's repair deadline
    since August 2024 before the site was abandoned outright (sha256
    `74b97bb3…8997bde05`, msg `Lenina106_Mariupol/986`, dated 2025-06-02).
    This message had no caption at all and never matched any classifier
    rule — pure manual discovery.
  - `2024-03-27_decree619_door_notice.jpg` — the photographed notice
    ("Uvedomlenie") citing **Mariupol City Administration Head's Directive
    No. 619 (12.10.2023)** (new [A]-rung entry in
    `docs/legal_mechanisms_review.md`) requiring 106's Zhovtnevy-district
    residents to submit title documents by 01.03.2024 (sha256
    `1ca8ed3d…361627e05`, msg `Lenina106_Mariupol/269`, dated 2024-03-27).
    **This one had been actively miscaptured by script 151's manifest** —
    it inherited an unrelated, off-topic caption from a different message
    entirely (the real caption, recovered from the raw `.meta.json`
    sidecar, is "on every door" — "На каждой двери" — exactly as expected)
    and was wrongly excluded as off-topic chatter in correction pass 3.
    Restored via a new `MANUAL_INCLUDES` mechanism in `scripts/156_*.py`
    that bypasses the classifier/caption pipeline entirely for
    hand-verified items. The standing lesson is now broader than "verify
    captions" — **even a caption's *association* with a given file can be
    wrong; check the raw `.meta.json`, not the manifest excerpt.**
