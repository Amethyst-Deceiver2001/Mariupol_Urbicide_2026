# @mariupol_nash deep-mining findings — 2026-07-02

Consolidated record of a manual deep-mine of the @mariupol_nash corpus:
**159,363 captured messages** (text-only, `scripts/212`), **78,913 with text**,
the other **80,284 caption-free** (photo/video only — a 50% blind spot to every
keyword sweep). @mariupol_nash is a general occupation-aligned Mariupol channel;
treat reconstruction/showcase posts as claims-to-verify and `#нампишут` resident
posts as leads, never primary source, until corroborated.

Tooling produced this session:
- `scripts/224_deep_intel_mariupol_nash.py` — actor/legal/process/address sweep (read-only)
- `scripts/225_nash_flag_and_media_manifest.py` — consolidated flagging + media manifest (read-only, **run**)
- `scripts/226_pull_nash_flagged_media.py` — targeted media pull (**network — user runs from VPS**)
- `data/parsed/nash_flagged_messages.jsonl` — **5,867** flagged messages, tagged
- `data/parsed/nash_media_pull_manifest.jsonl` — **~2,900** media targets (16 P1 + 778 P2 + 2,110 P3)
- `docs/mariupol_channel_research_terms.md` — the reusable term bank
- `docs/research_outsourcing/nevsky_kvartal_case_study_request.md` — Nevsky research request (updated)

**Numbers below are unverified channel-sourced leads unless marked otherwise.**
Nothing here is on the spine yet; capture/load is the downstream step.

---

## 1. The flagship find — ЖК/МКР «Невский» (→ dedicated case study)

Two separate, deliberately-confusingly-named developments on ул. Куприна /
пр. Ленина, distinguished by the channel's own correction (msg 64629):

- **МКР «Невский»** — built directly by **Военно-строительная компания (ВСК)
  Минобороны РФ** (a MoD public-law company, NOT a commercial застройщик — which
  is why it has **no ЕИСЖС registry entry**). Built in **181 days** in 2022;
  by 2023 **6 nine-storey buildings** + a **1,100-student school** + a **150-place
  kindergarten**; hundreds of **ордеров** issued to families "чьё жильё
  разрушено". Overseen by **Тимур Иванов** (then Deputy Defence Minister — already
  a node in the project's VSK→Олимпситистрой→Оборонспецстрой→Иванов chain,
  `memory/vskmo_olimpsitistroy_chain_2026-06-20.md`). **Visited in person by
  Vladimir Putin, March 2023** (msg 30922). Launch event (2022-09-26, msg 13817)
  had Turchak attending a displaced family's move-in — textbook population-
  transfer showcase messaging.
- **ЖК «Невский»** — a separate, smaller, 2-building **commercial** complex by
  Moscow's **ООО «ОборонСпецСтрой»** (also a documented node in the same VSK
  chain — the name clash may be a shared network, not a coincidence).

**The open legal question that reframes it all:** are МКР Невский units permanent
replacement title or *revocable маневренный-фонд/ордер possession*? If the latter,
this is the project's most visible instance of contingent-possession-dressed-as-
resettlement, at the site Putin toured. Full status + remaining research tasks:
`docs/research_outsourcing/nevsky_kvartal_case_study_request.md`.

Neighbor **ЖК «Изумрудный»** (same block) shares the gap — no registry entry,
cement-plant dust + power/water outages in resident posts.

## 2. New / uncaptured legal instruments

- **ГКО №341 registration freeze + Указ №307 fix** (msgs 82512, 85263, 88180,
  Jun–Jul 2024) — the DNR Head's Administration admits №341 caused a "техническая
  накладка" that **suspended property-rights registration DNR-wide for months**;
  Пушилин Указ №307 issued to remediate; ОНФ involved in casework. **None of
  №341/№307/the freeze episode are in `docs/`.** High priority — a window where
  owners were structurally blocked from re-registering (the very defence against
  ownerless designation). Cross-check the freeze window against court-filing spikes.
- **Постановление Администрации №1592** (17.10.2025, "О постановке на учет
  недвижимой вещи в качестве бесхозяйной", msg 148557) — a specific ownerless-
  designation act, not in `docs/`.
- All other top-cited numbers (№175, №116, №39, №263, №300, №1103, №515, №66-РЗ,
  №141-РЗ) confirmed **already** in the project's scaffolding — no gap.

## 3. Policy / mechanism leads

- **Commercial ownerless auctions** (msg 145593, 2025-09-26) — Mariupol to auction
  ownerless *commercial* real estate; first commercial-auction endpoint reference.
- **2% new-build transfer** (msg 160632) — developers hand 2% of new-build units to
  the municipality; a mechanism distinct from the 2%-mortgage program in
  `memory/demand_side_architecture.md`.
- **"6,000 ownerless apartments" to be distributed** (msg 158705) — reconcile
  against the 12,948 registry figure in `docs/STATS.md`.
- **Federal-law 4-region scope + до 2030 + recipient list** (msg 156241) —
  силовики/военные/чиновники/учителя/врачи named as recipients (likely ФКЗ-4).
- **Count corroboration + УЖКХ→МИЗО handover** — 12,948-address bezkhoz list
  confirmed 17.03.2026 (msg 167525, matches STATS.md); 10 days later an 8,163
  combined жилой/нежилой list with the contact office moved from УЖКХ (бул.
  Шевченко 301Б) to **МИЗО (пер. Черноморский 10)** (msg 168833) — reconcile the
  count discrepancy and note the jurisdictional handover.
- **Non-residential victim class** (msg 167428) — a winter-swimming/volleyball
  club building tagged bezkhoz + told it'll be demolished. Different victim
  category than the residential case studies; a live, trackable eviction.
- **Morgun self-incrimination quote** (msg 109055) — *"а вдруг придёт
  собственник? ... Мы действуем в рамках закона."* Fits the authorial-voice
  self-incrimination-as-method style.

## 4. Restoration-theatre / demolish-rebuild suspicion

- **пр. Победы 123** (msgs 95692, 97196, Sep 2024) — approved for capital repair
  2022, partial 2023 work, then a Moscow expert finds the **foundation cracked and
  load-bearing basement walls separating** under the 4th floor, taking soil samples;
  residents suspect a quiet demolish-and-rebuild. Same shape as the Нахимова 82
  modality, caught mid-process. **Not in `docs/`.** Live/unresolved — a forward-
  tracking capture candidate.
- **пр. Металлургов 221** (msgs 108832, 109976, Dec 2024) — contractor took an 80%
  advance on a building later ruled аварийный, replaced 1 of 80 doors; "жить ОПАСНО".
- **Pattern across addresses** — Ленина 63/2, Городской Сад colonnade (repainted 2×),
  Шевченко 82/84 newbuilds — fresh plaster/paint cracking within months of
  "restoration"; the channel itself mocks it ("Конец ремонта и начало трещин").
  Recurring named contractors: Строймонолит, Модуль-Центр, ЛУКТЭЙТОР, Дагестан
  Каспийстрой, Петрострой — cross-ref against stakeholder network.

## 5. Court / prosecutor / civil-resistance leads

- **Sania Denisova** (msg 91318, 2024-08-06) — activist organizing displaced/
  bezkhoz owners into **collective prosecutor complaints**; a possible source
  contact, not just a data point.
- **пр. Ленина 97** (msg 116648) — 7 apartments refusing to vacate for repair;
  coercion-via-repair-logistics eviction pressure (distinct mechanism).
- **Азовстальская → пр. Тульский** (msg 154471, 2025-12-04) — **ВС ДНР rejected a
  collective resident lawsuit** contesting the street renaming. A concrete court-
  loss data point for the de-Ukrainianization theme. Not in `docs/`.
- **Novinsky / Амстор ECtHR claim** (msg 64952) — Akhmetov's partner filed an ECtHR
  claim over the Амстор supermarket's destruction; add to the Metinvest/SCM
  corporate-claims thread in `docs/legal_mechanisms_review.md`.

## 6. Developer / contractor entities (region-sponsor "шефство" layer)

New region-sponsor contractors not yet in the stakeholder network, each tied to a
sponsoring Russian region: **ООО «Геострой-2010»** (Moscow — new-build apt blocks
on ул. Куприна, Sep 2022, likely the Nevsky-area precursor), Р-Строй (Moscow),
Невское РЭУ (SPb — also the Ленина 105 contractor), Модуль-Центр (SPb), Гражданпроект
(Krasnoyarsk), Трансюжстрой, СМУ-3 (Lipetsk), ВНР (Novosibirsk), АльянсСпецСтрой
(Moscow — 4-building complex on ул. Артёма). Already tracked: РКС-НР, ПСК
Строймонолит, ГК ЕКС.
False positives to ignore: ФГУП «НИКИМП» (maritime-safety agency), АО «ПТС»
(a payment kiosk, not a company), ООО «Капшин» (power lines), ООО «ЮГМК» (mining).

## 7. Structural gaps in the capture itself (see term-bank doc §method)

1. **80,284 caption-free messages** (50%) never examined — no text to sweep.
2. **97% of all messages carry media we've never looked at** — every lead above
   describes a photo/video still uncaptured. `scripts/226` closes this for the
   flagged subset (~2,900 files, not 150K).
3. **32,352 forwards (20%) — now mapped, `scripts/230`/`231`.** 661 distinct
   forward-source channels; ranked by forward-count × flag-rate (same method that
   first found @mizodnr/@donurcenter, `memory/new_telegram_channels_intel_2026-06-27.md`).
   Standout: **«БЮРО ⁉️ Подслушано в Мариуполе»** (channel_id 1691983818) —
   3,278 forwards, **496 flagged (15.1%)**, more flagged messages than the other
   660 sources combined; a resident-complaints/gossip format matching the
   resident-voice gap in item 4 below, but **no public `@username`** (private/
   invite-only) — not crawlable with the current method. Second tier, all above
   baseline (0.2–3.9%): `@mariupol_po_faktu` (16.0% flag rate, public,
   crawlable), 4 district-administration channels (Орджоникидзевский 14.1%,
   Ильичёвский 12.8%, Жовтневый 11.5%, Приморский 11.4%, all private/no
   username), «НЕДВИЖИМОСТЬ. МАРИУПОЛЬ» (5.1%, private). Full ranked table:
   `data/parsed/nash_fwd_source_graph_resolved.jsonl`.
4. **Only 875 replies** — broadcast channel; resident voice reaches us only
   pre-filtered through admin-chosen `#нампишут` reposts.

---

## Next actions

1. **User:** run `scripts/226_pull_nash_flagged_media.py` (P1+P2 default) from the
   VPS to capture the ~800 core-seizure photos + 6 curated videos for the leads above.
2. Process the **№341/№307 registration-freeze** thread into
   `docs/legal_mechanisms_review.md` (capture the primary decrees — geoblocked,
   needs a capture script).
3. Draft the **Nevsky case study** once the outsourced N4/N5 (pre-war site history,
   final scale) return; the temporary-vs-permanent legal-status question is the lead.
4. ~~Run a `fwd_from` source-graph count over the Nash corpus~~ — **done**, see §7.3.
   Remaining: find a way in to «Подслушано в Мариуполе» (invite-link/private) and
   crawl `@mariupol_po_faktu` + the 4 district channels if reachable.
5. Reconcile the **12,948 vs 8,163 vs "6,000"** ownerless counts and the
   **УЖКХ→МИЗО** office handover against `docs/STATS.md` before the 1 July re-snapshot.
