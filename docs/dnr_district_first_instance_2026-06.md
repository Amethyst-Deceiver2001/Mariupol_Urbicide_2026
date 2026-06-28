# DNR first-instance “ownerless property” seizures — base-rate analysis

*Analysis date: 2026-06-28. Population: 8,271 unique first-instance (бесхозяйная недвижимость, особое производство) petitions across the 26 DNR district/city courts that returned records. Capture: full-population district crawl (2026-06-27/28, `crawl/courts.py`). Parse: `scripts/182`. Source: `data/parsed/dnr_district_bezkhoz.json`; raw: `data/raw/<sha>.html`.*

## Why this layer matters

The ВС ДНР appellate analysis ([dnr_bezkhoz_appellate_outcomes_2026-06](dnr_bezkhoz_appellate_outcomes_2026-06.md)) is self-selected to cases *someone contested*, so it shows a WIN-heavy distribution — the cases worth appealing. **This is the layer beneath it: the base rate.** It is what happens to an ownerless-property petition by default, before and absent any appeal — and the default is grant.

## Headline: the first-instance grant rate

**Of 8,098 decided first-instance petitions, 7,052 were granted — a 87.1% grant rate.** The administration asks a court to vest a war-emptied home in municipal ownership, and ~6 times in 7 the court says yes at first instance.

| Owner-side outcome | n | share |
|---|---|---|
| LOSE (seizure granted) | 7,052 | 85.3% |
| WIN (refused/bounced) | 744 | 9.0% |
| WITHDRAWN/terminated | 235 | 2.8% |
| UNKNOWN/UNCLASSIFIED | 173 | 2.1% |
| NEUTRAL (procedural, refileable) | 67 | 0.8% |

The dominant WIN sub-type is `оставлено без рассмотрения` — a *спор о праве* bounce that, exactly as in the appellate layer, is procedural and refileable, not a ruling that the seizure is unlawful.

## Per-municipality

| Court / municipality | cases | granted / decided | grant rate |
|---|---|---|---|
| mar-zhovt--dnr | 1,382 | 1161/1377 | 84.3% |
| harc--dnr | 1,070 | 979/1069 | 91.6% |
| mar-prim--dnr | 685 | 526/680 | 77.4% |
| mng--dnr | 611 | 479/611 | 78.4% |
| vr--dnr | 503 | 418/469 | 89.1% |
| enak--dnr | 478 | 437/473 | 92.4% |
| cg-gorl--dnr | 451 | 425/446 | 95.3% |
| gorn--dnr | 398 | 360/385 | 93.5% |
| mar-ordzh--dnr | 353 | 314/353 | 89.0% |
| vln--dnr | 349 | 241/289 | 83.4% |
| centralno-gorodskoy--dnr | 340 | 293/318 | 92.1% |
| mar-ilich--dnr | 253 | 227/253 | 89.7% |
| amv--dnr | 228 | 167/217 | 77.0% |
| tlm--dnr | 208 | 180/208 | 86.5% |
| yasin--dnr | 192 | 182/191 | 95.3% |
| kir--dnr | 184 | 165/176 | 93.8% |
| star--dnr | 174 | 154/174 | 88.5% |
| bud--dnr | 162 | 142/161 | 88.2% |
| nva--dnr | 97 | 83/97 | 85.6% |
| vld--dnr | 64 | 55/63 | 87.3% |
| dok--dnr | 53 | 38/53 | 71.7% |
| deb--dnr | 30 | 21/30 | 70.0% |
| marin--dnr | 5 | 4/4 | 100.0% |
| krasn--dnr | 1 | 1/1 | 100.0% |

## Mariupol vs. rest of DNR — at first instance

- **Mariupol:** 2248/2684 granted = **83.8%**
- **Rest of DNR:** 4804/5414 granted = **88.7%**

Note the inversion from the appellate finding: at **first instance** the grant rate is uniformly high *everywhere* — Mariupol is not harsher here, the rubber-stamp is region-wide. The Mariupol-specific harshness documented in [dnr_bezkhoz_citizenship_doctrine_2026-06](dnr_bezkhoz_citizenship_doctrine_2026-06.md) is a feature of how *contested* cases resolve on appeal, not of the base grant rate. Both readings coexist: near-universal first-instance granting, plus a harsher appellate posture toward the displaced Mariupol owners who manage to contest.

## Knowing dispossession — the court grants even when it knows an owner exists

- Petitions where a living owner **was named** as `заинтересованное лицо`: granted **85.5%** (2,289/2,677 decided).
- Petitions with **no named owner**: granted **87.9%** (4,763/5,421).
- Of **7,052** granted seizures, **2,289** (32.5%) had a living owner named in the case file.

Naming an owner barely moves the outcome — the court vests the home in the municipality at nearly the same rate whether or not it has a living owner on the record in front of it. About a third of all granted seizures were entered with an identified owner present in the file. This is the base-rate counterpart to the appellate [citizenship doctrine](dnr_bezkhoz_citizenship_doctrine_2026-06.md): the doctrine is the *reasoning* the court reaches for when a named owner actually contests; this is how often it dispossesses a known owner without one contesting at all. (Owners are counted, never named — CLAUDE.md.)

## Tempo — and the Mariupol court shutdown

| Month | Mariupol | rest of DNR |
|---|---|---|
| 2025-06 | 275 | 348 |
| 2025-07 | 223 | 391 |
| 2025-08 | 260 | 226 |
| 2025-09 | 185 | 458 |
| 2025-10 | 192 | 403 |
| 2025-11 | 91 | 310 |
| 2025-12 | 81 | 350 |
| 2026-01 | 23 | 270 |
| 2026-02 | 16 | 279 |
| 2026-03 | 4 | 208 |
| 2026-04 | 3 | 193 |
| 2026-05 | 1 | 139 |
| 2026-06 | 0 | 74 |
| 2026-07 | 0 | 1 |

The two columns diverge sharply. Mariupol first-instance bezkhoz decisions **collapse to zero** through early 2026 (and filings collapse the same way, so this is the conveyor stopping, not a backlog of undecided cases), while the rest of DNR keeps running. Read against the **1 July 2026** ownerless re-registration deadline and ФКЗ-4 (Dec 2025) abolishing the court stage (`CLAUDE.md`): Mariupol — the Roskadastr НСПД pilot — finished its court conveyor **first** and handed off to direct registry inclusion ahead of the rest of the occupied oblast. The court data carries the signature of the legal pivot, dated and municipality-specific.

## Who petitions

| Petitioner type | n |
|---|---|
| municipal_administration | 7,834 |
| ministry | 217 |
| none_listed | 103 |
| state_property_fund | 82 |
| other_state_body | 35 |

Petitioner organisations and the judges below are occupation officials acting in official capacity — named, not minimised (CLAUDE.md). The owners are living private individuals and are only counted, never named: **2,711** cases list at least one natural-person owner as the `заинтересованное лицо` — i.e. the court knew an owner existed and vested the property in the municipality anyway.

## Most prolific first-instance grant-signers (named officials)

| Judge | grants | total bezkhoz cases |
|---|---|---|
| Попова Инна Константиновна | 401 | 504 |
| Романов Дмитрий Сергеевич | 264 | 291 |
| Мяконькая Татьяна Александровна | 170 | 195 |
| Кралинина Наталья Геннадьевна | 167 | 178 |
| Разинко Ольга Олеговна | 161 | 180 |
| Кириченко Елена Сергеевна | 160 | 168 |
| Гревцова Виктория Алексеевна | 153 | 188 |
| Бойко Николай Иванович | 129 | 144 |
| Струнов Никита Иванович | 123 | 140 |
| Тлеужанова Ботагоз Елеусизовна | 119 | 145 |
| Леонов Александр Юрьевич | 117 | 137 |
| Белоусов Павел Валериевич | 110 | 170 |
| Лежнева Яна Михайловна | 104 | 105 |
| Нидзиева Наталья Николаевна | 99 | 129 |
| Тащилин Роман Игоревич | 93 | 98 |
| Мухаметшин Рафик Алимович | 91 | 162 |
| Гурова Анастасия Александровна | 89 | 98 |
| Резниченко Владимир Алексеевич | 89 | 139 |
| Сазонова Юлия Юрьевна | 88 | 125 |
| Добридень Анна Юрьевна | 88 | 93 |

## Property-identity recovery — and the redaction wall

- Cards with embedded ruling text: **1,552** of 8,271 (18.8%).
- Of those, the street address is redacted to `<адрес>` on **100.0%** of cards.
- A **cadastral number** (a unique property identifier that links directly to the spine / Rosreestr) survived on **35** cards — the only reliable property-identity recovery here, and 4 of them exact-match existing spine properties (`scripts/184`).
- The street-address extractor fired on 232 cards but is **unreliable** — spot-checking shows mostly utility-narrative false positives, not addresses. With the street redacted on 100% of rulings, the cadastral number is the linkage target; the loose street field should not be treated as claim-grade.

This redaction is **not occupation-specific** — it is standard depersonalization practice under Russian Federal Law No. 262-FZ, applied by the GAS «Правосудие» system the same way at any Russian court nationwide. It masks owners as ФИО1/ФИО2 and the address as `<адрес>` uniformly. What is specific to this dataset is the practical effect, not the rule: the court-islands address gap persists not because the record wasn’t captured but because a generic depersonalization rule, applied here as everywhere, redacts the address in the published ruling. The cadastral numbers that survive are the highest-value linkage targets recovered here.

## Scope and caveats

- **Base rate of the contested-or-not first-instance layer**, across the 26 productive courts only. Of the 15 enabled courts that returned zero under their OWN domain, a ВС ДНР venue notice (vs--dnr.sudrf.ru, name=information&rid=5, captured 2026-06-28) shows 10 are not actually “zero” — their jurisdiction was formally transferred to an absorbing court already in this dataset (Авдеевский→Ясиноватский; Александровский/Добропольский/Новогродовский/Селидовский→Ворошиловский; Великоновоселковский→Кировский; Дзержинский/Краснолиманский→Енакиевский; Дружковский/Константиновский→Горловский). `scripts/186` recovers cases attributable to the absorbed town from the ruling text where it names the origin — confirmed for **Avdiivka (8 cases)** inside Yasynuvata’s docket; no confirmed hits yet for the other 9 absorbed towns (absence of a textual hit is inconclusive, not proof of zero). The remaining 5 courts are genuine **building-only relocations with no jurisdiction transfer** — the court nominally exists but its own domain produced no or near-no cases, split between cities Russia holds but has destroyed (Артемовский/Bakhmut, Угледарский/Vuhledar) and “ghost” courts for Donetsk-oblast territory Russia claims but has never controlled (Славянский/Sloviansk, Краматорский/Kramatorsk, Красноармейский/Pokrovsk).
- A first-instance “grant” is the seizure consummated unless and until appealed; most are never appealed (see the appellate layer’s self-selection caveat).
- `UNKNOWN/UNCLASSIFIED` = pending cases with no result code yet, plus a few rare result codes outside the mapped vocabulary.
- Reproducible end-to-end from `data/raw/` via `scripts/182` → `scripts/183`.
