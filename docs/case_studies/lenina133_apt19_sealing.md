# Case Study — prosp. Lenina, 133, apt. 19: Registry Inclusion → Physical Sealing & Eviction

**The project's first dated, photographic evidence of the on-the-ground
enforcement step that follows an "ownerless" registry entry — a sealed
apartment door, a handwritten vacate deadline, and a still-resident occupant
with documents the occupation administration is disregarding.**

Unlike the address-laundering case (`nakhimova_82_chernomorsky_1b.md`, a
demolish→rebuild footprint) or the mass-resale case
(`mass_registry_to_resale.md`, registry→market), this case documents the
**enforcement act itself**: a Telegram post and photo, dated 23 Oct 2025,
showing apartment 19 of prosp. Lenina, 133 physically sealed
("OPECHATANO" — "sealed") by the occupation's Department of Property and
Land Relations (Управление имущественных и земельных отношений), days after
a 2024 court ruling on "ownerlessness" — while a 73-year-old registered
resident, holding a power of attorney from the absent owner, is told to
vacate.

---

## The building

| Field | Value |
|---|---|
| property.id | **4442** |
| prewar_address | prosp. Myru, 133 |
| occupation_address | prosp. Lenina, 133 |
| building_id | `AVENUE:ленина\|133` |
| RD4U category | A3.1, A3.6 |
| District | Zhovtnevy |

**Already on the spine before this post:**
- 5 apartments in `registry_inclusion` (seizure_event, "signs of
  ownerlessness"): **2, 9, 14, 15, 19** (ids 37358–37362).
- `unosat_damage` corroboration (id 4867): Moderate Damage, 12 May 2022,
  14.8m from property point, confidence Very High.
- `mirror_source` corroboration (id 1412): Russian federal
  damage/reconstruction tracker lists this building at **100% destruction,
  Phase II**, contractor GK Transstroiinvest, executor state development
  company (PPK) «Edinyi zakazchik».

That last point is worth holding onto: the occupation's *own* federal
tracker describes this building as 100% destroyed and slated for full
reconstruction — yet the post below describes named residents, with current
utility accounts, still physically present in October 2025. Either the
"100% destruction" entry is aspirational/planned rather than as-built, or
demolition has proceeded unevenly across the block while individual
apartments are being cleared unit-by-unit ahead of it. Either way, it
sharpens rather than weakens the seizure narrative: residents are being
evicted from units in a building the federal government has already
earmarked for redevelopment.

---

## The post: t.me/ssaniaworld/3348 (23 Oct 2025, 19.3K views)

Channel: "Saniya Denisova's Ministry of Happiness. Movement — the Power of
Good" (Министерство Счастья Сании Денисовой. Движение - СИЛА ДОБРА; an
occupation-critical Russian-language channel relaying resident complaints).
Captured via `scripts/60_fetch_lenina133_sealing_notice.py`, SHA-256
`01adb154…e80b49`.

**Title:** "Lenin Avenue 133: people are being thrown out of their
apartments onto the street" («Проспект Ленина, 133: людей выкидывают из
своих квартир на улицу»).

> Суды по квартирам **2, 19, 20, 33** в доме по проспекту **Ленина, 133**
> прошли еще в 2024 году. Некоторые собственники не успели поставить в
> Росреестр, кто-то не смог вернуться из Беларуси, другие — не успели
> оформить наследство из-за очередей и затягивания со стороны нотариусов. А
> теперь людей С ПРОПИСКОЙ выкуривают из квартир.

> *"Court [rulings] for apartments 2, 19, 20, 33 in the building at Lenin
> Avenue 133 already happened back in 2024. Some owners didn't manage to
> register with Rosreestr in time, some couldn't return from Belarus,
> others didn't manage to complete inheritance paperwork because of queues
> and notary delays. And now people WITH RESIDENCY REGISTRATION are being
> smoked out of their apartments."*

The post then quotes a subscriber's first-person account of apartment 19
specifically:

> У нас тоже квартира в списке. Мама проживает и прописана, но собственник
> в Беларуси. Есть доверенность, но это во внимание не берут. Опечатали
> квартиру и попросили съехать. В квартире проживает мама 73 года. Все
> коммунальные оплачены, даже во всех жкх составлены договора по
> доверенности. Мама с РФ паспортом. А дочь её является собственником,
> написала в Минске доверенность на маму. Опечатали квартиру и просят
> освободить. По закону в Росреестр квартиру можно поставить до 2028
> года. В администрации заявили, что было решение суда по бесхозу в 2024
> году и она принадлежит муниципальной собственности.

> *"We have an apartment on the list too. Mom lives there and is
> registered, but the owner is in Belarus. There's a power of attorney, but
> they don't take that into account. They sealed the apartment and asked
> [us] to leave. A 73-year-old mother lives in the apartment. All utilities
> are paid, and every utility company has agreements on file under the power
> of attorney. Mom has an RF passport. Her daughter is the owner, and wrote
> a power of attorney in Minsk naming Mom. They sealed the apartment and are
> asking [us] to vacate. By law the apartment can be registered with
> Rosreestr up until 2028. The administration said there was a court ruling
> on бесхоз [ownerlessness] in 2024 and it belongs to the municipality."*

> В том же доме 133 по проспекту Ленина проживают люди в квартирах 2, 19,
> 20, 33. Все они напрямую связаны с собственниками, но всем сказали
> выселяться. Это чиновничий беспредел.

> *"In the same building 133 on Lenin Avenue, people live in apartments 2,
> 19, 20, 33. All of them are directly connected to the owners, but all were
> told to vacate. This is bureaucratic lawlessness."*

---

## The photo: two "ОПЕЧАТАНО" notices on apt 19's door

Captured as SHA-256 `8b354c87…07f6ae7` (`data/raw/8b354c87…07f6ae7.jpg`).
Two near-identical printed notices, stacked, each with a different
handwritten vacate date:

> Объект является муниципальной собственностью городского округа Мариуполь
> [handwritten:] **пр. Ленина д. 133 кв. 19**. [handwritten:] **Освободить до
> 25.10.2025** [top notice] / **22.10.2025** [bottom notice]
>
> ВХОД СТРОГО ВОСПРЕЩЁН!
>
> **ОПЕЧАТАНО**
>
> Без представителя собственника в лице Управления имущественных и
> земельных отношений не вскрывать.
>
> Повреждение запорных устройств, дверей, окон, инженерных систем объекта, а
> также несанкционированное проникновение повлекут ответственность, в том
> числе статьями 139, 168 Уголовного кодекса Российской Федерации.
>
> Телефон для связи с представителем собственника: **+7 (949) 814-63-64**

> *"This property is the municipal property of Mariupol urban district —
> [handwritten] Lenin Ave. 133, apt 19. [handwritten] Vacate by 25.10.2025 /
> 22.10.2025. ENTRY STRICTLY FORBIDDEN! SEALED. Do not open without a
> representative of the owner, i.e. the Department of Property and Land
> Relations. Damage to locks, doors, windows, or building systems, as well
> as unauthorized entry, will result in liability, including under Articles
> 139 [violation of the inviolability of the home] and 168 [intentional
> destruction/damage of property not amounting to arson] of the Russian
> Criminal Code. Contact phone for the owner's representative: +7 (949)
> 814-63-64."*

Two notices with two different deadlines for the same apartment most likely
reflect either a re-posting after the first deadline lapsed, or two separate
sealed openings (e.g. door + window/balcony) sealed on different visits.
Either reading places active enforcement squarely in the week of
20–25 October 2025.

---

## What this closes

| Stage | Date | Source |
|---|---|---|
| `registry_inclusion` ("signs of ownerlessness") | undated, ownerless registry export | seizure_event id 37362 (existing) |
| Court ruling on ownerlessness | 2024 (per post; not yet in `court_case`) | t.me/ssaniaworld/3348 (testimony) |
| Physical sealing + vacate notice | 22–25 Oct 2025 | corroboration id 5417 (`testimony_ref`, this session) |

This is the first time the project has a **dated, photographed, on-the-ground
enforcement act** for an apartment already on the registry spine — closing
the gap between an administrative paper designation and the lived
consequence (a sealed door, a 73-year-old told to leave, criminal-code
threats against anyone who breaks the seal). For RD4U **A3.6** (loss of
access to property in occupied territory), this converts "the registry says
this unit was designated ownerless" into "as of October 2025, the occupant
was physically barred from entry under threat of prosecution."

---

## Addendum (2026-06-13): the "100% destruction" entry resolved — a 2022 demolish-rebuild plan that was never executed

The tension flagged above ("Either the 'destruction' entry is aspirational... or
demolition has proceeded unevenly") is now resolved. `scripts/62_crawl_lenina133_chat.py`
scraped the @Lenina133 resident-chat forum (1311 messages / 487 media,
21 Nov 2022 – 4 Jun 2026, 6 topics), and a dated read of the first weeks gives
a clean explanation.

**The official record (corroboration id 1412) is real, but it's a plan, not
an as-built fact.** On **9 Dec 2022**, residents photographed an official
"ПАСПОРТ ОБЪЕКТА" sign posted on the building itself (t.me/Lenina133/91):

| Field | Value |
|---|---|
| Multi-apartment building | g. Mariupol, prosp. Myru, d. 133 |
| Developer | Ministry of Construction of the Russian Federation |
| Client | public-law company (PPK) «Edinyi zakazchik v sfere stroitelstva» |
| General contractor | LLC (OOO) «RKS-NR» |
| Total area | 4440 m² |
| Floors | 9 |
| Construction start | Q4 2022 |
| Construction end | Q3 2023 |

A sister passport for the neighboring **prosp. Myra, 135** (5-story, 1900 m²,
same scheme, t.me/Lenina133/92) was posted the same day. Both list the
project as **STROITELSTVO** ("construction" — new construction, i.e.
demolish-and-rebuild) — this is the source of the "group=4 (demolish),
destruction_pct=100, priority_phase=II, GK Transstroiinvest / PPK «Edinyi
zakazchik»" entry in the federal damage tracker (corroboration id 1412).

**But the building was never demolished — and residents had already moved
back in and repaired it before the passport was even posted:**

| Date | Evidence |
|---|---|
| 9 May 2022 | Building standing intact (Google Earth, user-provided) |
| spring 2022 | Severe fire damage to part of the facade/balconies (photographed later) |
| **21–28 Nov 2022** | Chat opens — "Welcome home!!!" ("Добро пожаловать домой!!!"); temp roof patches, building-wide window replacement, electrical/plumbing restored by MK GRUPP / FKRMO (ФКРМО — Moscow Region Capital Repair Fund) |
| **25 Nov 2022** | Photo: "glazing on the burned-balcony side" ("Остекление со стороны сгоревших балконов") — reglazing of the fire-damaged side actively underway (t.me/Lenina133/51) |
| **9 Dec 2022** | "PASPORT OBEKTA" ("object passport") demolish-rebuild signs posted for 133 and 135 (above). Residents immediately ask: "new construction, or repair-and-restoration work? Those are two very different things" ("Начало строительства или ремонтно-восстановительных работ? Ведь две большие разницы") |
| **10 Dec 2022** | Photo: repaired exterior, new windows + renewed entrance canopy (t.me/Lenina133/99-100) |
| **21 Dec 2022** | Residents conclude the passport really does say "construction," not "kapremont" (capital repair), and allege a "commission from Moscow" cited weak floor slabs as the reason — but no resident meeting or notification preceded the designation (t.me/Lenina133/149-150) |
| 2024–2026 | Ongoing structural-defect complaints (crack floors 5–9); building "transferred to the city's books" ("сдан на баланс города"); **individual apartments** 2, 19, 33 sealed as "ownerless" Oct 2025 (id 5417) — piecemeal seizure, not wholesale reconstruction |

**Conclusion:** corroboration id 1412 is not a wrong-building mismatch — it
accurately reflects a real, dated Dec-2022 demolish-rebuild *designation* for
this exact building. But that designation was an unexecuted plan: residents
document reoccupation and repair both before and after it was posted, the
same structure stands today (2026), and the occupation pursued
individual-apartment "ownerless" seizure instead of the announced
reconstruction. Loaded as **corroboration id 5418**
(`testimony_ref`, **verdict='refutes'**, confidence 0.85, observed
2022-11-21 to 2022-12-21) via
`scripts/63_load_lenina133_demolition_plan_refute.py` — refutes the
demolition/100%-destruction *outcome* implied by id 1412 while explaining its
documentary origin.

---

## Open leads (not loaded)

- **Apartments 20 and 33** are named in the post alongside 2 and 19 as
  having had 2024 court rulings, but are **not** in property 4442's
  `registry_inclusion` rows (which cover only 2, 9, 14, 15, 19). Either the
  registry export used for loading doesn't cover these two, or they were
  processed through a different administrative track not yet captured.
  Worth a targeted registry re-check for "Lenina (Myra), 133, 20" / "...,
  33".
- **ul. Chernomorskaya, 10** — the same post separately quotes a subscriber
  describing active door-to-door inventory/inspection ("inventarizatsiya")
  at this address, the pre-petition stage. No property on the spine has
  occupation_address exactly "ulitsa Chernomorskaya, 10" (closest:
  Chernomorskaya 1 = id 6048, Chernomorskaya 22/10 = id 6058). Not merged —
  flagged as a fresh address to watch for in the next registry/
  ownerless-decree update.

---

## Provenance

| Artifact | SHA-256 | Captured |
|---|---|---|
| Post HTML (t.me/ssaniaworld/3348, `?embed=1`) | `01adb154…e80b49` | 2026-06-13 |
| Photo (two OPECHATANO "sealed" notices) | `8b354c87…07f6ae7` | 2026-06-13 |

Both via `scripts/60_fetch_lenina133_sealing_notice.py` (public Telegram
embed widget + cdn4.telesco.pe photo URL, non-geoblocked, same precedent as
scripts 52/54-59); manifest at
`data/parsed/lenina133_apt19_sealing_manifest.json`. Loaded as
`corroboration` id 5417 (kind=`testimony_ref`, verdict=`confirms`,
confidence=0.90, observed 2025-10-23) by
`scripts/61_load_lenina133_apt19_corroboration.py` — the project's first
loaded S5 (testimony_ref) row per `docs/tier3_corroboration_design.md`.

*As with all Telegram-sourced material: this is a primary-source dated
photo of an official document plus first-person testimony, not an
independently audited fact — but it directly names the same building,
apartment, and administrative designation ("ownerless", 2024) already
present in the registry-derived spine record, which is why it is loaded as
corroboration rather than left as a bare reference.*
