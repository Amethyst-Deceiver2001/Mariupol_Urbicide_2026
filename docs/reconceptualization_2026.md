# Mariupol Property Seizures — Reconceptualization from First Principles (June 2026)

*Prepared as a fresh-start strategy note for the Mariupol urbicide / property-seizure documentation project. It checks the previous iteration against the situation as of mid-2026, then rebuilds the data strategy from the goal backwards.*

---

## 1. Why this needs a reset

The last project handover (27 July 2025) described an evidence pipeline built around **harvesting PDFs from a single occupation portal** (`mariupol-r897.gosweb.gosuslugi.ru`), a single-building case study (Morskoy 46), and a theoretical frame ("administrative violence / bureaucratic self-incrimination"). The numbers then were ~163 PDFs, ~500 documented seizures, 5,172 properties in "repair" programs.

Three things have changed enough to invalidate the old center of gravity:

1. **The evidence universe is now an order of magnitude larger and far more structured than a folder of municipal PDFs.** As of early–mid 2026 the dominant, most legally potent record is the body of **occupation *court* cases** transferring property to municipal ownership — Human Rights Watch identified ~**8,116 publicly available property-seizure cases across 25 occupation court websites** (23 district + 2 regional courts in the so-called DNR/LNR), with ~2,113 decisions published, filed March 2024–January 2026 (HRW, 26 May 2026). Each case is a near-complete, dated, self-incriminating chain: notice → inspection → "ownerless" designation → court transfer → reallocation.

2. **There is now a concrete restitution endpoint that defines "actionable."** The Council of Europe's **Register of Damage for Ukraine (RD4U)** is live (~150,000 claims as of April 2026), and the **Convention establishing an International Claims Commission for Ukraine was signed by 35 states + the EU in December 2025**. RD4U category **A3.6 — loss of access to property in occupied territories** maps directly onto these seizures; A3.1/A3.2/A3.3 cover damage/destruction/loss of housing. This is where structured data becomes a victim's claim, not just a narrative.

3. **The clock is short and the curve is steep.** A December 2025 federal-law amendment pulled the deadline for Ukrainians to re-register property under Russian law **forward from January 2028 to 1 July 2026** — roughly one month from now. Andriushchenko's Center for the Study of Occupation reports ~5,000 Mariupol apartments already designated "ownerless" and **100–200 added per week**; ~900 apartments were added to a Mariupol "compensatory housing" redistribution list in May 2026; evictions began April 2026. A large new wave of designations and court filings is expected on and after 1 July 2026. The project should be positioned to *capture a flow*, not just archive a stock.

**First-principles consequence:** the project is no longer primarily a PDF scraper. It is an **aggregation, cross-referencing, and evidentiary-structuring layer** sitting on top of several primary streams — and its comparative advantage is *linking* (property ↔ owner ↔ seizure event ↔ named actor ↔ beneficiary ↔ corroboration), at Mariupol granularity, in a form that two specific downstream consumers can use.

---

## 2. The goal, stated minimally

> Produce a verifiable, queryable, court-admissible evidence base that links **specific Mariupol properties** to **specific unlawful seizure acts** by **specific Russian occupation actors**, structured so it can feed (a) **individual restitution claims** (RD4U / Claims Commission) and (b) **criminal accountability** (war crime of unlawful appropriation of property — Rome Statute art. 8(2)(a)(iv)/(b)(xiii) — and unlawful transfer of the occupier's own population — art. 8(2)(b)(viii)).

Everything below is derived from that sentence. If a data source or feature does not move a property closer to one of those two endpoints, it is out of scope.

### The irreducible data atom

A single record should answer: *which property, owned by whom, was taken how, by whom, when, to whose benefit, and how do we know?* Concretely:

| Field group | Content |
|---|---|
| **Property identity** | Pre-war Ukrainian address + cadastral number + coordinates ↔ occupation-era address (street renamings + re-addressing after demolition) |
| **Owner** | Lawful owner where knowable from Ukrainian registries; *minimized/redacted* for living private individuals (see §6) |
| **Seizure lifecycle** | Event type + date + source document + SHA-256, for each stage: utility cut-off → "ownerless" notice → commission inspection → designation → court petition → court transfer → entry into force → reallocation/resale |
| **Actor** | Signing official, court, judge, commission, notary, named beneficiary/new occupant |
| **Financial layer** | Subsidized-mortgage program, sale price, budget allocation, bank |
| **Corroboration** | Satellite before/after, witness/testimony reference, Ukrainian-side mirror, cross-source confirmation count + confidence |

---

## 3. Actionable-data inventory (source by source)

Ordered by evidentiary value × tractability. For each: what it yields, how to get it, reliability, and the structuring task.

### Tier 1 — The new crown jewel: occupation court records
- **What it yields:** the most complete and most self-incriminating unit available — a dated judicial act transferring a *named* Ukrainian owner's identified property to municipal ownership, citing the exact legal grounds (almost always "absence of Russian registration"), inspection evidence (often absurd: "overgrown grass," "closed door"), and frequently *acknowledging the owner's identity while still ruling the property "ownerless."* HRW: ~8,116 cases, 25 courts; reviewed decisions show a ~1-year lifecycle with explicit dates.
- **Mariupol-specific courts seen in rulings:** Primorskyi (Primorsk) District Court, Pershotravnevyi District Court, Telmanovskiy District Court (Donetsk region).
- **Access:** the occupation courts run on Russian "ГАС Правосудие"–style portals (per-court websites with case cards / "судебное делопроизводство"). These are geoblocked/unstable; access via a Russia-routed VPS, with each retrieved card hashed and timestamped on capture.
- **Reliability:** very high as evidence *of the occupier's own administrative act* — that is precisely the point; these are confessions in judicial form. Not reliable as to facts (they ignore ownership), which is itself the documentable abuse.
- **Structuring task:** define a court-case schema; build a resilient, polite crawler keyed to the "special proceedings / признание права муниципальной собственности" case type; OCR/parse Cyrillic case cards; extract address, dates, court, judge, grounds, outcome. **This is the single highest-leverage build for the next phase**, and it should be ready before the 1 July 2026 deadline wave.

### Tier 1 — Occupation "ownerless property" lists (the original stream, still essential)
- **What it yields:** the *upstream* of the court cases — the periodic municipal lists naming addresses given 30 days to come forward. Published "several times per month" on occupation municipal sites; Mariupol Left-Bank batches run to thousands; a December 2025 Mariupol batch designated one apartment "along with 341 other properties."
- **Access:** occupation municipal websites (gosuslugi.ru subdomains, mrpl.news, district administration pages) + **Telegram channels** used by Mariupol residents where lists circulate.
- **Reliability:** high as primary administrative artifacts; pair every list with capture hash + archive snapshot (lists are edited/removed).
- **Structuring task:** continue scraping, but treat each list entry as the *opening* of a lifecycle record that should later be matched to its court case (Tier 1) — i.e., join, don't silo.

### Tier 1 — Russia's property registry (Rosreestr / Unified State Register of Real Estate, ЕГРН)
- **What it yields:** the registration status that the entire "ownerless" logic hinges on. Russian authorities reported **4.6M properties registered across the four occupied regions since Sept 2024, with ~550,000 flagged as having no documentation** (RG, Aug 2025) — i.e., the at-risk pool. New Russian ownership entries (post-seizure) name the beneficiary.
- **Access:** ЕГРН extracts are partially paid/limited and increasingly restricted to Russian-passport holders; treat as targeted lookups for high-value cases, not bulk.
- **Structuring task:** for priority properties, capture the registration state-change (Ukrainian owner → "ownerless" → municipal → new owner) as dated evidence of the transfer.

### Tier 2 — Authoritative aggregate figures (for scale, framing, corroboration)
- **OHCHR / UN HRMMU 43rd periodic report (9 Dec 2025):** >38,000 properties noticed as "potentially abandoned" by Nov 2025; **5,557 formally designated "abandoned"** in Donetsk/Luhansk regions. Authoritative, citable baselines.
- **HRW (26 May 2026):** the court-case census + lifecycle + legal analysis (above).
- **BBC Verify (2025):** analysis of occupation documents identifying **≥5,700 Mariupol homes** for seizure (2,200 imminent + 3,550 potential).
- **Center for the Study of Occupation / Petro Andriushchenko:** the highest-frequency Mariupol monitor — ~5,000 designated by Dec 2025, +100–200/week; ~22,000 residents without homes, only ~4,500 confirmed for compensation; leaked occupation documents (e.g., the pilot to distribute apartments to Prosecutor's Office / Investigative Committee / FSB staff). His Telegram channel is a primary-document source.
- **Use:** these are not the granular evidence base; they are the numerator/denominator that lets the project state scale defensibly and sanity-check its own counts.

### Tier 2 — Parallel datasets (complement, don't duplicate)
- **Leibniz-IfL / KonKoop "VisLab" (Guénola Inizan):** already **scraping + geocoding the published ownerless lists across 16 DNR municipalities**, producing per-day animated maps (e.g., Khartsyzk). Methodologically identical to the project's list-scraping; worth contacting for collaboration / data-sharing rather than rebuilding.
- **Dossier Center:** reviewed hundreds of "ownerless" units and matched them to named beneficiaries (e.g., an aide to the occupation mayor of Berdyansk) — proof that the lists can be turned into *actor accountability*, not just maps.
- **Novaya Gazeta Europe (May 2024):** mapped the geographic pattern (concentration in city centers / along main roads; Mariupol, Melitopol, Svatove as hotspots).
- **Use:** position the project as the Mariupol-deep, *linkage-focused* node that joins these efforts to court records and to RD4U claim categories.

### Tier 2 — Financial / beneficiary layer
- Subsidized-mortgage population-replacement programs (preferential ~2% rates; ~75% of apartments bought by Russians, mostly from Moscow/Moscow Oblast); Promsvyazbank lending; "compensatory housing" redistribution lists naming categories of beneficiaries (military, security, officials, education/health staff). Budget allocations for "repairs" create a financial trail.
- **Use:** links the dispossession to the population-transfer war-crime theory and to sanctions/illicit-finance work.

### Tier 3 — Corroboration sources
- **Satellite (Sentinel-2 free; Planet via humanitarian/edu):** before/during/after for demolition + re-addressing cases (e.g., Nakhimova 82 → Chornomorsky lane). Confirms physical reality behind a paper transfer.
- **Filtration / entry-ban data (East SOS):** ~1 in 4 allowed through; 30,000 Ukrainians denied entry Oct 2023–Apr 2025 with 20–50-year bans. Evidence that the "appear in person within 30 days" requirement is *designed* to be impossible — central to proving the process is a sham.
- **Utility-disconnection signal:** Russia cuts utilities to flag/empty units (reported March 2026). A leading indicator that can prioritize which addresses to watch.
- **Street-renaming / re-addressing tables:** the toponymic layer (already partly built) is the join key between pre-war Ukrainian addresses and occupation-era addresses; without it, court cases and Ukrainian registries won't match.

---

## 4. The data model that ties it together

The previous iteration's schemas were oriented around documents and a single building. Reorient around the **seizure lifecycle of a property**, so that any source plugs into a shared spine:

```
property (canonical)
  ├─ prewar_address, cadastral_no, coords (UCS-2000/EPSG:6387 → WGS84)
  ├─ occupation_address  ──┐ (via toponymic + re-addressing tables)
  └─ building_id           │
                           │
owner (minimized)  ────────┤
                           │
seizure_event (1..n) ──────┤   type ∈ {utility_cutoff, notice, inspection,
  ├─ event_date            │           ownerless_designation, court_petition,
  ├─ source_doc_id         │           court_transfer, entered_force,
  ├─ sha256, captured_at   │           reallocation, resale}
  └─ confidence            │
                           │
actor (1..n) ──────────────┤   role ∈ {signing_official, court, judge,
                           │           commission_member, notary, beneficiary}
court_case (0..1) ─────────┤   court, case_no, judge, legal_grounds, outcome
financial (0..n) ──────────┤   mortgage_program, sale_price, bank, budget_line
corroboration (0..n) ──────┘   satellite_pair, testimony_ref, mirror_source
```

Key joins: **toponymic table** (prewar↔occupation address) and a **confidence/`n_sources` field** on every linkage (≥2 independent confirmations for legal-grade rows). The RD4U mapping is an attribute on `property`/`seizure_event`: which claim category (A3.1/A3.2/A3.3/A3.6) it could support.

---

## 5. Architecture, reconceptualized (leaner)

- **Drop the assumption that bespoke harvesting is the core work.** Two of the three Tier-1 streams (lists, aggregate figures) are partly covered by others (Leibniz, OHCHR, HRW, Andriushchenko). The *unique* build is the **court-records crawler + parser** and the **linkage spine** above.
- **Aggregate-first.** Ingest others' published datasets where licenses allow; reconcile to the canonical `property` spine; spend scarce effort on the joins nobody else is doing (court case ↔ list ↔ Ukrainian cadastre ↔ beneficiary).
- **Capture-time forensics stay non-negotiable:** SHA-256 + ISO-8601 capture timestamp + source URL + archive snapshot (archive.today / Wayback / local WARC) for *every* artifact; Berkeley Protocol chain-of-custody log. This is unchanged from prior iterations and remains correct.
- **Resource envelope:** the 8 GB / sub-$20 framing still works for everything except resilient geoblocked crawling, where a small Russia-routed VPS is the one justified recurring cost. Streaming/tiled processing for satellite remains the right call.
- **Output ergonomics:** the deliverable is not a monolith but (a) a queryable DB, (b) per-property "evidence dossiers" exportable as PDF for a claimant or investigator, and (c) aggregate maps/timelines for advocacy.

---

## 6. Guardrails (forensic + ethical)

- **Owner privacy:** lawful owners who are living private individuals must be minimized/pseudonymized in any shared output; their identity belongs in the secured evidentiary layer that feeds *their own* claim, not in a public map. The court records publish some owner data — handle as sensitive personal data, store encrypted, expose only aggregate or owner-consented detail.
- **Don't launder occupation "facts."** Occupation registrations, "ownerless" designations, and court rulings are evidence *of the act of seizure*, not evidence of valid title. Ukraine does not recognize them; the project should frame them the same way (a documented unlawful act), never as authoritative ownership data.
- **Two-consumer discipline:** tag each property with which downstream use it is ready for — RD4U claim support vs. criminal-accountability dossier — because the evidentiary thresholds and privacy handling differ.

---

## 7. Concrete next steps (priority order)

1. **Build the court-records crawler + Cyrillic parser** for the 25 occupation court portals, scoped to the "recognition as municipal property / признание права муниципальной собственности" special-proceeding case type, Mariupol courts first (Primorskyi, Pershotravnevyi, Telmanovskiy). Forensic capture on every card. *Do this before the 1 July 2026 deadline wave.*
2. **Stand up the lifecycle spine** (§4) and migrate existing list/PDF data onto it, so new court data joins cleanly to the old list data.
3. **Finalize the toponymic + re-addressing join table** (prewar Ukrainian ↔ occupation address), the dependency that everything else needs to match.
4. **Reconcile against authoritative counts** (OHCHR 5,557 designated; HRW 8,116 cases; Andriushchenko's running tally) to validate coverage and report scale defensibly.
5. **Map every property to its RD4U category** and produce a prototype per-property evidence dossier suitable for a claimant.
6. **Reach out to parallel efforts** (Leibniz-IfL/KonKoop, Dossier Center) for data exchange to avoid duplicate scraping and to extend beyond Mariupol if useful.

---

## 8. Open gaps / things still to confirm

- Exact URLs/structure and current accessibility of the 25 occupation court portals (the HRW report names the count, not the addresses).
- Whether any party has already published the court-case dataset in structured form (worth confirming before building the crawler — could collapse step 1).
- RD4U's exact evidentiary requirements for category A3.6 (occupied-territory access loss) — needed to shape the per-property dossier export.
- Licensing for ingesting Leibniz / Dossier / Novaya Gazeta datasets.

---

*Sources consulted (mid-2026): Human Rights Watch, "Ukraine: Russia Illegally Seizing Property in Occupied Areas," 26 May 2026; UN OHCHR 43rd periodic report on Ukraine, 9 Dec 2025; Council of Europe Register of Damage for Ukraine (rd4u.coe.int) + CMS/Sayenko Kharenko/Kyiv Post coverage of the 29 Apr 2026 category launch and Dec 2025 Claims Commission Convention; BBC Verify (2025); Leibniz-IfL/KonKoop VisLab blog, 28 Nov 2024; Kyiv Independent, Euromaidan Press, NV, CEPA, Mezha, Russian Life/Dossier Center, 2025–2026. Russian-language primary references embedded in the HRW report: npa.dnronline.su (Law 66-RZ), publication.pravo.gov.ru (15 Dec 2025 amendments), rg.ru (Aug 2025 registry figures), mrpl.news.*
