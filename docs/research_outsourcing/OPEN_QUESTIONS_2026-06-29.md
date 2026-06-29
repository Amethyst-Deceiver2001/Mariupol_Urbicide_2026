# Open Questions — batch 2 (2026-06-29)

New tasks identified this session (apartment-collapse/unit-table work +
gap-register review). Same usage as `OPEN_QUESTIONS.md`: copy a `## Task`
block, paste after `RESEARCH_BRIEF.md`, send to the outsourced researcher LM.
Move resolved items to a Closed section (or back into the main
`OPEN_QUESTIONS.md` once that file's current Q6 is resolved and it gets
tidied) rather than deleting.

---

## Task — Q7: GKO decree series sweep (siblings of №263)

**Question:** Are there other DNR State Committee for Defense (ГКО)
decrees, in the same numbering neighborhood and timeframe as №263
(29.09.2022, "пополнение маневренного фонда" — replenishment of the
transit-housing fund) and №300, that name specific Mariupol street
addresses for forced expropriation?

**Why it matters:** №263 turned out to be a named 13-address expropriation
decree, not a generic framework instrument — 10 of its 13 addresses were new
to the spine and have now been loaded (`scripts/209`). If this is a series
rather than a one-off, there may be more named-address decrees sitting
unindexed.

**What we already know:**
- №263 (29.09.2022) and №300 are both confirmed, OCR'd, and loaded.
- №300 mentions a related №164 (a 1-year "temporary use" stage) — also a
  lead, not yet chased.
- All three are ГКО ДНР instruments, so likely hosted on the same
  domains as the two already found.

**What "done" looks like:** A list of any additional ГКО decree numbers
(roughly #150-#350 range, 2022-2023) whose title or body mentions specific
street addresses for expropriation/transit-fund allocation, with links/PDF
locations. A confirmed "no other address-naming decrees found in this range"
is also a complete answer.

**Known dead ends:** none yet — this angle hasn't been tried.

**Domains likely to host the answer:** `pravo.gov.ru` (where №263/№300 were
found — note their PDFs are scanned-image-only, require OCR, real download
URL pattern is `/file/pdf?eoNumber=<id>` not the JS-shell View page),
`glavadnr.ru`, `npa.dnronline.su`, `gisnpa-dnr.ru`.

---

## Task — Q8: Identify/rule out 3 GKO №263 near-match addresses

**Question:** For three addresses named in GKO №263 — Лунина 9, Карпинского
84, Сеченова 81 — are they the *same physical building* as the spine
properties they were near-matched to (property_id 5816, 5672, 5759
respectively), or genuinely distinct buildings that happen to share a house
number on a similarly-named street?

**Why it matters:** These 3 of 13 addresses were skipped (not force-merged)
during the №263 load because the match wasn't certain. Confirming or
rejecting the match closes out the decree's full address list.

**What we already know:**
- The decree gives only street+house, no apartment/block detail (consistent
  with all other ГКО-level instruments).
- The near-match property IDs are already on the spine from other sources.

**What "done" looks like:** For each of the 3, either (a) independent
confirmation the two addresses refer to the same building (e.g. a court case,
registry entry, or map source giving both names/spellings for one location),
or (b) confirmation they're different buildings (in which case the №263
address should be loaded as a new property instead of merged).

**Domains likely to host the answer:** Mariupol gosuslugi ownerless registry
search by street name (catches alias spellings), 2GIS/Yandex Maps historical
listings, DNR district court case texts mentioning either spelling.

---

## Task — Q9: Docket check for the 5 building-relocated DNR courts

**Question:** Do Bakhmut, Vuhledar, Sloviansk, or Kramatorsk, or Pokrovsk
district courts have any published "особое производство" /
"бесхозяйная недвижимая вещь" (ownerless-property) case listings under
their own court name, on ГАС «Правосудие» or any DNR/LNR court-portal
mirror, filed 2022–2026?

**Why it matters:** These are the 5 of 15 zero-result DNR courts confirmed
*not* to have had jurisdiction formally transferred elsewhere (unlike the
other 10, which were recovered hiding inside an absorbing court's docket —
see `scripts/186`). They're either destroyed (Bakhmut, Vuhledar) or
"ghost" courts for Ukrainian-held territory Russia claims on paper
(Sloviansk, Kramatorsk, Pokrovsk). A genuine zero is itself meaningful
(supports the "abolished/non-functioning" reading) but hasn't been
positively confirmed past "our crawler found nothing."

**What we already know:**
- `courts.py` already lists all 5 in its court directory; 0 cases returned
  by the existing crawl.
- The ВС ДНР venue notice (captured 2026-06-28) is what established these 5
  had no jurisdiction transfer, unlike the other 10.

**What "done" looks like:** Either a small number of recovered case
records for one or more of these courts (would need to be added to the
crawl), or a clearly-sourced statement that no court-portal page/docket
exists for the court at all (e.g. site structurally absent, court name not
findable in any portal's court-selector dropdown). This is a discovery
question — a confirmed negative with evidence is a complete answer.

**Known dead ends:** `ej.sudrf.ru` is confirmed authenticated-only, don't
re-try it.

**Domains likely to host the answer:** ГАС «Правосудие» court-portal
mirrors used elsewhere in this project (see `src/mariupol_seizures/crawl/
courts.py` and `dnr_supreme_court.py` for the working domain patterns),
any DNR-side judiciary directory listing active courts.

---

## Task — Q10: EGRUL alternative for captcha-blocked founder lookups

**Question:** Do `rusprofile.ru`, `list-org.com`, or `checko.ru` expose the
same EGRUL extract data (founders, INN, registration date, legal address)
for Russian legal entities as `egrul.org`, without a captcha gate on
name-based search?

**Why it matters:** `nalog.ru` is geoblocked; `egrul.org` works but
captcha-gates name search, blocking lookups where only a company name (not
an INN) is known — this has stalled at least one developer-chain lead
(СЗ ГСА ДЕВЕЛОПМЕНТ, see Q6 in `OPEN_QUESTIONS.md`) and likely others in
the stakeholder network.

**What we already know:**
- INN-based lookups on egrul.org work fine; only name search is
  captcha-gated.
- 17 INNs from disclosed founders are already in hand and don't need this
  (`egrul_founders_and_appointment_decrees.md`).

**What "done" looks like:** Confirmation that one of the alternative sites
returns equivalent EGRUL data via name search without a captcha, with a
worked example (search by a known company name, confirm the returned INN
matches what we already have on file as a sanity check). A confirmed "all
three are also gated/incomplete" is also useful.

**Domains likely to host the answer:** `rusprofile.ru`, `list-org.com`,
`checko.ru`, `egrul.org` (baseline for comparison).

---

## Closed (additional, this batch)

- ~~Q12. Primary text of Presidential Decree No. 201 (20.03.2020, Crimea)~~
  — **RESOLVED 2026-06-29.** `pravo.gov.ru`'s own full-text search engine
  (the ИПС at `pravo.gov.ru/proxy/ips/`) turned out not to support phrase
  search — six scripted hops (`scripts/212`–`218`) just got drowned in
  unrelated documents sharing a date or number token. Found instead via a
  plain (non-geoblocked) web search for the decree's title, which surfaced
  its `publication.pravo.gov.ru` ID (0001202003200021) directly; fetched
  and OCR'd in one more step (`scripts/219`). Confirms it amends Decree
  No. 26 (09.01.2011) by adding 19 Crimean municipal districts + 8
  Sevastopol city-districts, folded into the same housekeeping amendment as
  unrelated Astrakhan/Belgorod/Kaliningrad edits — not a standalone
  Crimea-specific act as the secondary reporting implied. **Lesson for next
  time:** try a plain web search for the instrument's title before
  attempting to drive a geoblocked portal's own internal search engine —
  the search engine itself may not support the query semantics assumed.

---

## Closed

- ~~Q13. Primary text of FKZ-4's underlying federal "ownerless housing"
  amendments~~ — **RESOLVED 2026-06-29.** ФКЗ-4 itself (not a separate
  amendment) is the instrument — full text captured via `pravo.gov.ru` ИПС
  search (`scripts/212`–`216`, nd=609234940). Article 1 inserts a new
  **Статья 21¹** into ФКЗ №5-ФКЗ (the DNR-admission law). Confirms the
  Rosreestr+Rosimushchestvo joint-processing claim (primary-sourced, not
  just press paraphrase); surfaces a previously-undocumented **1 January
  2030** State-side backstop deadline for completing title transfer
  (distinct from the 1 July 2026 citizen-facing cutoff); confirms военнослужащим
  (military personnel) by name as an allocation category; and surfaces a
  **compensation-in-kind clause (§4.4)** — a like-kind replacement unit back
  to the original displaced owner — not previously documented anywhere in
  this project. Full text loaded into `docs/legal_mechanisms_review.md`'s
  Framework table; `docs/exhibits/two-property-systems.html` updated from
  Reported→Captured.

---

## Task — Q11: Registry "last updated" signal ahead of 1 July 2026 deadline

**Question:** Does the Mariupol gosuslugi ownerless-property registry page
expose any "last updated"/version timestamp, revision history, or
incrementing record-count signal that would let us measure registry growth
across the 1 July 2026 re-registration deadline?

**Why it matters:** The project's live front line is the ownerless registry
(court conveyor having shut down). A pre/post-deadline snapshot comparison
would be a clean, dated data point on how much the deadline itself drove
registry growth — but only if there's a way to detect *when* entries were
added, not just a flat current count.

**What we already know:**
- The registry has been snapshotted before (temporal differential work,
  `scripts/150`) using dated full-page captures, not a built-in version
  signal.

**What "done" looks like:** Either confirmation of a usable timestamp/
version field on the page (with the field name/location), or confirmation
there isn't one — in which case the answer is "rely on manual dated
snapshots, no native signal available," which is itself useful to know
before scheduling a capture.

**Domains likely to host the answer:** the Mariupol gosuslugi ownerless-
registry page itself (mariupol.gosuslugi.ru or equivalent — see existing
crawl scripts for the exact URL).
