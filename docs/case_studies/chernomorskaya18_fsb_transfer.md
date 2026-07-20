# Case Study — Чёрноморская, 18 / Ленина, 101: from the bezkhoz registry into an FSB unit's hands

**Accession:** MUP-CS-011 · Modality M10 — registry sweep → transfer to a
named military/security institution · [REGISTRY.md](REGISTRY.md)

**On 12 March 2026 the Мариупольский городской совет approved handing a
54.59 m² apartment at ул. Чёрноморская, 18, кв. 24, over to «Войсковая часть
1297» — a federal state institution whose corporate registration lists the
FSB, Russia's Federal Security Service, as owner. The apartment's own record
on this project's spine shows the full chain that got it there: entered the
ownerless-candidate list, formally designated bezkhoz on 24 April 2025, then
handed over on request from the unit's acting commander seven months later.
It is not an isolated instance — the same unit received two more properties
(an apartment at пр. Ленина, 101, кв. 21, and a garage at ул. Чкалова, 23/25)
via a second decision two months earlier. Most of this project's evidence
for Rome Statute art. 8(2)(b)(viii) — transfer of the occupier's population
into occupied territory — describes civilians moving into seized housing
through resale or a subsidized mortgage. This is the first instance the
project has found of a named security-service institution, not a private
buyer, receiving specific, individually-addressed former-bezkhoz apartments
by direct municipal decision — with the recipient's own commander named in
the paperwork.**

## 1. How this was found

A systematic capture of the Мариупольский городской совет's «Решение»
document family (339 decisions, 2024–2026; `scripts/383`) was undertaken
after an incidental discovery: a resident-supplied link to Решение №I/1-2
turned out to have nothing to do with the compensation-housing decree it was
initially cited alongside — it was a property transfer to a military unit.
That single find prompted the full crawl. All 339 documents were OCR'd
(`scripts/06a`) and classified by subject via a keyword pass
(`scripts/387`), which surfaced a recurring instrument: «О согласовании
безвозмездной передачи \[движимого/недвижимого\] имущества из муниципальной
собственности… в федеральную собственность» — a council resolution
transferring municipal property to federal ownership. Most instances of this
document type move construction *materials* (see §5); a minority move
*specific, cadastral-numbered real estate*, and two of those three transfer
occupied bezkhoz apartments to the same recipient.

The classifier itself required two rounds of correction before these
findings were trustworthy — worth recording, since the corrections are part
of the evidentiary chain: the first pass's keyword for military recipients
(`войсковая часть`) was an exact nominative-case match, which silently
dropped every declined form ("войсковой части", "войсковую часть") — Russian
grammar, not a data gap. This missed even the flagship И/1-2 case entirely.
Fixed to a stem-based pattern (`войсков\w+\s+част\w+`). A separate keyword
(`бесхозяйн`) initially fired on an unrelated abandoned-*vehicle* clause in a
parking ordinance; narrowed to require housing/property context. Both fixes
are in `scripts/387_classify_gorsovet_resheniya.py`.

## 2. The clean chain: Чёрноморская, 18, кв. 24

| Date | Event | Source |
|---|---|---|
| (undated snapshot) | Listed in the ownerless-candidate registry ("Перечень… с признаками бесхозяйных") | `registry_inclusion`, property spine pid 6055 |
| **2025-04-24** | Formally designated bezkhoz — `ownerless_designation`, address_raw "ул. Черноморская, д.18, кв.24" | property spine pid 6055 |
| 2025-11-29 | ФГКУ «Войсковая часть 1297»'s временно исполняющий должность командира requests the apartment, №23/1РЦ/б-2440 | Решение №I/5-5 (12.03.2026), recital |
| **2026-03-12** | Мариупольский городской совет Решение №I/5-5: "Согласовать безвозмездную передачу… недвижимого имущества, а именно: жилое помещение, общей площадью 54,59 кв.м, с кадастровым номером 93:37:0010410:1856… ул. Черноморская, дом 18, квартира 24" — approved unanimously, signed by Кольцов А.В. (глава) and Сенин Ю.А. (председатель горсовета) | Решение №I/5-5 full text (OCR, `scripts/06a`) |

This is the only one of the three confirmed real-estate transfers where the
project's own spine independently shows the bezkhoz-designation date *before*
knowing this decision existed — the two records were captured through
entirely separate pipelines (the registry/decree crawl vs. this council-
decision crawl, months apart) and agree on the address down to the apartment
number. That independence is what makes this the flagship instance rather
than merely a plausible one.

## 3. The same recipient, twice more

**Решение №I/1-2 (22.01.2026)** transferred two further properties to the
same unit in one instrument:
- **пр. Ленина, 101, кв. 21** — 101.6 m², кадастровый №93:37:0010106:504.
  On spine (pid 4414) in `registry_inclusion`; the building carries extensive
  `ownerless_designation`/`reclaim`/`compensation_housing_listing` activity
  for its *other* apartments, but no matching `ownerless_designation` record
  was found for apartment 21 specifically — either a gap in this project's
  decree coverage, or this unit moved through an untracked path. Routed via
  the Территориальное управление Федерального агентства по управлению
  государственным имуществом в ДНР (Росимущество, 15.12.2025) in addition to
  the unit's own request (16.07.2025, №174-дсп).
- **ул. Чкалова, 23/25** — 2.72 m², кадастровый №93:37:0010313:354 (area
  consistent with a garage or storage unit, not a dwelling). On spine
  (pid 6917) in `registry_inclusion` only.

A third confirmed real-estate transfer, **Решение №I/11-2 (14.05.2026)**,
moved 430 m² of non-residential space (1st/2nd floor, пер. Киевский, 10А,
кадастровый №93:37:0010313:1069) to a *different* unit, ФГКУ «Войсковая
часть 76835» — establishing that the mechanism is not specific to one
recipient, even if в/ч 1297 is so far the only one confirmed to have
received residential housing.

## 4. Who в/ч 1297 is

ФГКУ «Войсковая часть 1297» — Федеральное государственное казенное
учреждение, ИНН 9310007740, ОГРН 1239300004866, registered 22 May 2023,
legal address Донецкая Народная Республика, Старобешевский район, с.
Победа, ул. Ленина, 35. Primary activity code ОКВЭД 84.22 ("Деятельность по
обеспечению военной безопасности"). Acting commander of record as of 25
August 2025: **Ладнов Сергей Сергеевич**.

**OpenSanctions** (sourced from the Russian Unified State Register of Legal
Entities, EGRUL) lists **ФСБ России — the Federal Security Service — as
owner**, holding an unspecified share, active from the unit's registration
date (22.05.2023) through 21.04.2026:
[opensanctions.org/entities/ru-inn-9310007740](https://www.opensanctions.org/entities/ru-inn-9310007740/).
This is the basis for the FSB attribution in this write-up. Two further
corporate-registry sources were located independently — rupep.org and
egrul-base.ru — but rupep.org returned a Cloudflare challenge and could not
be re-read directly from this project's research environment; egrul-base.ru
and a second aggregator (checko.ru) confirm the registration particulars
above but list the founder/учредитель field as access-restricted under
129-ФЗ (standard for defense-adjacent entities) rather than stating FSB
explicitly in the retrievable page content. **The FSB attribution therefore
rests on OpenSanctions/EGRUL, not on independent confirmation from a second
fully-read primary source** — a caveat that should travel with any
downstream citation of this finding until rupep.org (or an equivalent) can
be read directly.

## 5. The wider pattern: materials to at least eight more units

The same document family — Решение горсовета, identical "…в федеральную
собственность" operative clause, the identical named control officer
(**Яремчук Игнат Игнатович**, зам. главы Администрации, on nearly every
2025–2026 instance) — also transfers bulk *construction materials*, not
real estate, to a further set of named units between December 2024 and May
2026:

| Recipient | Materials | Decision |
|---|---|---|
| в/ч 29506 (заместитель командующего 5-й гвардейской общевойсковой армией) | Rebar А500С16 (1,786.52 m), treated lumber (50 m³), roofing felt (238,733.94 m²) | №I/12-7, 28.05.2026 |
| в/ч 74854 | Precast concrete slabs 6×2m (600 units); separately, precast slabs (302), lumber, roofing felt, SIP cable | №I/12-8 (28.05.2026); №I/5-6 (12.03.2026) |
| в/ч 76835 | (see §3 — real estate, not materials) | №I/11-2 |
| в/ч 52245 (инженерные войска) | Used cable, 200,000 running m | №I/11-3, 14.05.2026 |
| в/ч 6960 — Росгвардия | Used road plates ПДН-14 (8 units), crushed stone (483 t) | №I/14-5, 23.10.2025 |
| в/ч 19288 + в/ч 75245 | SIP cable, 3 + 4 km | №I/14-6, 23.10.2025 |
| (unnamed, МО РФ generally) | Sawn lumber — 716.3 + 39.4 + 260.3 m³ in one decision alone | №I/3-4, 18.02.2025 |
| (unnamed, МО РФ generally) | Sawn lumber, smaller volumes | №I/28-4, №I/28-5, 29.12.2024 |

**The provenance of these materials is not established** and should not be
asserted either way — precast road/airfield slabs (ПАГ-14, ПДН-14) are a
standard military-engineering stock item and plausibly state-procured; the
lumber volumes are large enough (over 1,000 m³ across just three decisions)
that demolition salvage is a plausible source worth checking against the
demolition register, but this write-up does not claim that link. Kept in
this case study as an open lead, not a finding.

## 6. Fit to the project's framework

This sits in a new rung, **[F2]**, in `docs/legal_mechanisms_review.md` —
distinct from [F] (civilian resale via the 2% mortgage subsidy). It
directly corroborates a statement already on record elsewhere in this
project's evidence base: DNR vice-premier **Татьяна Переверзева** told TASS
(01.05.2026, via @prav_dnr) that the republic needs ~7,000 apartments to
house "**учителей, медиков, силовиков и соцработников**," partly funded
"**за счёт ранее бесхозного жилья, которое перешло в муниципальную
собственность**" (rung [G], already [REPORTED]-grade). Until this find, that
was a policy statement without a named, address-specific instance. Чёрноморская
18/24 and Ленина 101/21 are the first two.

**RD4U:** A3.6 (loss of access/control of property, compounded here by
transfer into occupancy by a security-service institution rather than a
private buyer). **Rome Statute:** art. 8(2)(b)(viii) — and, because the
recipient is a named institution with a named commander of record rather
than an anonymous civilian purchaser, this is also relevant to any future
command-responsibility mapping.

Per project convention, the displaced owner(s) of these three properties
are not named or sought here — only the occupation officials and the
receiving institution, acting in official capacity, are in scope for
accountability (CLAUDE.md privacy rule).

## 7. Evidence gaps and priority follow-ups

- **Apartment 21's missing designation record.** Every other apartment
  captured in the Ленина 101 building has a dated `ownerless_designation`
  event; apartment 21 does not. Either the underlying decree wasn't
  captured, or this unit moved through a different/faster track — worth a
  targeted re-check of the decree corpus for this specific address before
  treating the gap as meaningful.
- **rupep.org re-read.** Cloudflare-blocked from this project's research
  environment; a second, independently-read source for the FSB ownership
  claim would strengthen §4 beyond OpenSanctions alone.
- **Materials provenance.** Cross-check the lumber/rebar/slab volumes in §5
  against `demolition_register`/`minstroy_demolition_register` for any
  salvage-quantity correlation — currently unexamined.
- **Load to DB — done 2026-07-20.** All 4 real-estate transfers (the three
  addresses above, split by apartment/unit where applicable) are loaded as
  `seizure_event(stage='military_transfer')` via `scripts/388_load_military_
  transfer_events.py`, a hand-curated loader (only 3 of the 339 decisions
  carry a real-estate transfer; the rest move construction materials, not
  loaded — see §5). в/ч 1297 and в/ч 76835 are upserted into `actor`
  (role='beneficiary') with the FSB-attribution caveat from §4 carried into
  `actor.notes`; Кольцов А.В. and Сенин Ю.А. are linked as signing
  officials via `event_actor`.
- **Remaining 339-decision corpus.** Only the `federal_transfer`-classified
  subset has been read in full. `bezkhoz_related` (4 hits, one of which —
  Решение №I/8-1, 19.03.2024 — appears to be a city-council-level primary
  instrument establishing the bezkhoz-registration procedure itself, not yet
  folded into `docs/legal_mechanisms_review.md` rung [A]) and the 60
  `land_plot_procedure` / 25 `tos_boundary` / 305 `administrative_other`
  buckets have not been individually read for further instances of this
  pattern.

## 8. Source register

**Primary (rank 1):**
- [Решение №I/5-5, 12.03.2026 — Чёрноморская 18/24 → в/ч 1297](https://mariupol.gosuslugi.ru/glavnoe/gorodskoy-sovet/?cur_cc=6980) (mariupol.gosuslugi.ru, captured `scripts/383`; direct PDF URL not yet re-extracted for this citation — see `data/raw` by sha via `source_document`)
- [Решение №I/1-2, 22.01.2026 — Ленина 101/21 + Чкалова 23/25 → в/ч 1297](https://mariupol.gosuslugi.ru/netcat_files/multifile/252/1655/Reshenie_I_1_2_ot_22.01.2026.pdf)
- Решение №I/11-2, 14.05.2026 — Киевский 10А → в/ч 76835 (mariupol.gosuslugi.ru, captured `scripts/383`)
- [OpenSanctions — ФГКУ «Войсковая часть 1297» entity page (FSB ownership, sourced from EGRUL)](https://www.opensanctions.org/entities/ru-inn-9310007740/)
- [egrul-base.ru — ФГКУ В/Ч 1297 registration particulars](https://www.egrul-base.ru/company/1239300004866/)
- [checko.ru — ФГКУ В/Ч 1297 company record](https://checko.ru/company/fgku-v-ch-1297-1239300004866)

**Cited but not independently re-verified (flagged, see §4):**
- [rupep.org — ФГКУ «Войсковая часть 1297» (Cloudflare-blocked to this project's fetch)](https://rupep.org/ru/company/47035)
- [rusprofile.ru — ФГКУ В/Ч 1297 (403 to this project's fetch)](https://www.rusprofile.ru/id/1239300004866)

**Corroborating context (rank 2/3):**
- Татьяна Переверзева / TASS statement on bezkhoz housing for силовики, 01.05.2026 (via @prav_dnr/42699) — see `docs/legal_mechanisms_review.md` rung [G]

---

*Cross-references:* `docs/legal_mechanisms_review.md` rung [F2] (mechanism),
`docs/stakeholder_network.md` Tier 1 (в/ч 1297 and sibling units as actors),
`memory/registry_decree_gap_resolved_2026-07-18.md` (registry-vs-decree
epistemics underlying the `registry_inclusion`/`ownerless_designation`
distinction this case study relies on).
