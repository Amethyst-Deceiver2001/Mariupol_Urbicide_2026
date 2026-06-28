# DNR Supreme Court "ownerless property" appeals — outcome analysis

*Analysis date: 2026-06-26, corrected 2026-06-27. Source: originally 95
hand-pulled appellate rulings (`scripts/175`); `scripts/178` then enumerated
the **complete** docket via systematic pagination (427 cards, including
text-less cases the hand-pulled batches structurally could not reach).
Capture: `scripts/175` + `scripts/178`. Classification: `scripts/176`. Raw:
`data/raw/<sha>.html`; parsed: `data/parsed/dnr_bezkhoz_outcomes.{json,csv}`.*

> **Correction (2026-06-27, twice-revised):** the headline "Mariupol is
> ~2.5× harsher" finding below (§"The signal that actually matters") was
> computed on the 95-case hand-pulled sample and **did not replicate** once
> the docket was re-pulled in full (427 cases, `scripts/178`) — first pass
> gave 1.28×/p=0.49. Investigating *why* the UNKNOWN rate differed by
> municipality then surfaced a **real classifier bug** in `scripts/176`: its
> "AFFIRM" and "petition-bounced" branches guessed an owner-side direction
> from an empty facts/disposition match instead of checking whether the
> ruling *text* was published at all, silently mislabeling 58 metadata-only
> cards as `AFFIRM_lower_direction_unclear` (65% of which were Mariupol).
> Fixed (guard added: no `Судебный акт` heading in the card → return
> `UNKNOWN_full_text_not_published` instead of guessing). **Numbers after
> the fix:** Mariupol decided n=22 (LOSE 8, WIN 13, NEUTRAL 1) = **36.4%**
> LOSE rate; rest-of-DNR decided n=99 (LOSE 24, WIN 52, NEUTRAL 23) =
> **24.2%** LOSE rate. Ratio **1.5×**, Fisher exact p = **0.29** — still not
> statistically significant, but the fix moved the point estimate back
> *toward* the original disparity rather than away from it, because the bug
> had been diluting Mariupol's decided-sample with miscategorized cases.
> Treat as: directionally consistent with Mariupol being somewhat harsher,
> not proven, decided-n still small (22). This does **not** affect the
> citizenship-doctrine textual finding
> ([dnr_bezkhoz_citizenship_doctrine_2026-06](dnr_bezkhoz_citizenship_doctrine_2026-06.md)),
> which rests on direct reading of specific ruling text, not on population
> size. **The UNKNOWN-rate gap itself persists post-fix and is now the most
> interesting open thread**: Mariupol's full-text-unpublished rate (cases
> flagged `UNKNOWN_full_text_not_published`) is **58.5% (83/142)** vs **44.6%
> (127/285)** rest-of-DNR — a real, unexplained 14-point gap (publication
> policy difference at Mariupol's source courts? case backlog? worth a direct
> look at a sample of Mariupol text-unpublished cards vs rest-of-DNR ones
> before drawing a conclusion). *(Corrected 2026-06-28: an earlier draft of
> this notice quoted 83.8%/63.9%, which was both stale and internally
> inconsistent — 119+182 did not sum to the 210 total stated below. The
> figures here are recomputed from `data/parsed/dnr_bezkhoz_outcomes.json` and
> sum to 210.)*

## What this is

Every one of these cases is the occupation's own paper trail of a single
attempted appropriation: a municipal administration (or, in 19 cases, the
DNR State Property Fund) declares a war-emptied flat *бесхозяйная* and asks a
court to vest it in municipal ownership. This dataset is the **appellate
layer** — the cases where *someone contested* a first-instance ruling. It is
emphatically **not** the base rate of seizure: the far larger mass of
uncontested first-instance grants (owners who never found out, never
appeared, or could not reach the court from displacement) never reaches
appeal and is not counted here. Read every number below as *the contest rate
among those who managed to contest.*

## Method, and why a single regex was not trusted

Outcome was derived from two reconciled signals, never one pattern over
prose:
1. the standardized GAS «Правосудие» **«Результат рассмотрения»** metadata
   code (present even on the handful of cards whose full ruling text is not
   published);
2. the **prose disposition** after `ОПРЕДЕЛИЛА:` / `РЕШИЛА:`, used to
   disambiguate the two metadata codes that are owner-direction-ambiguous on
   their own. The decisive trap: «оставить без рассмотрения» means **opposite
   things** depending on the noun it attaches to —
   * *заявление [администрации] … оставить без рассмотрения* → the **petition**
     is bounced (owner's reprieve); whereas
   * *(апелляционную) жалобу … оставить без рассмотрения* → the **appeal** is
     dismissed, usually a non-party for lack of standing, and the
     first-instance grant **stands** (owner loses).

   The clean petition-bounce tell is the advisory line «разъяснить … право
   разрешить спор в порядке искового производства», which appears only when
   the petition is sent off to ordinary litigation.

**Bug fixed 2026-06-27:** both the metadata-ambiguous branches above need
the prose disposition (or, for the AFFIRM code, the facts recital) to
disambiguate — but on a card whose ruling text isn't published, neither
exists. The classifier was matching an empty string against its disambiguation
regexes and silently keeping whatever branch the regex *failed to rule out*,
instead of checking for the absence of a `Судебный акт` heading (the
text-published marker) up front. Net effect: 58 metadata-only cards were
labeled `AFFIRM_lower_direction_unclear` (a wrong-but-plausible-looking
"ambiguous ruling" reading) rather than the correct `UNKNOWN_full_text_not_published`
— and 65% of those 58 were Mariupol cases, which is what first surfaced this
while investigating the Mariupol/rest-of-DNR UNKNOWN-rate gap. Now guarded:
every branch checks `text_published` (presence of `Судебный акт` in the card)
before attempting disambiguation.

## Headline distribution

**Original sample (n = 95, hand-pulled — superseded below):**

| Owner-side outcome | n | share |
|---|---|---|
| **WIN** (procedural / temporary) | 45 | 47% |
| **NEUTRAL** (claim revived / remanded for merits) | 24 | 25% |
| **LOSE** (seizure granted or upheld) | 20–22 | 21–23% |
| UNKNOWN (full text not published) | 3 | 3% |
| WITHDRAWN | 2 | 2% |
| OTHER (state railway infrastructure, out of pattern) | 1 | 1% |

**Full population, post classifier-bug-fix (n = 427, `scripts/178` +
`scripts/176` fixed 2026-06-27):**

| Owner-side outcome | n | share |
|---|---|---|
| UNKNOWN (full text not published) | 210 | 49% |
| UNKNOWN / unclassified disposition text | 89 | 21% |
| **WIN** (procedural / temporary) | 65 | 15% |
| **LOSE** (seizure granted or upheld) | 32 | 7% |
| **NEUTRAL** (claim revived / remanded for merits) | 24 | 6% |
| WITHDRAWN | 5 | 1% |
| UNKNOWN (affirmed, owner-direction unclear) | 2 | 0% |

The honest UNKNOWN-text-unpublished share is **49%**, not the pre-fix 11% —
nearly half the full docket genuinely has no ruling text on the portal at
all, regardless of municipality. (The hand-pulled 95-case sample's 3%
unpublished-rate was itself a sampling artifact: someone browsing for
readable rulings naturally skips the blank ones.) The 89 "unclassified
disposition text" cases are real published rulings the regex vocabulary
doesn't yet cover (rare result codes — appeal-process violations, partial
reversals, etc.) — a genuinely separate, smaller gap from the
text-unpublished one, and not yet worth a fix at 89/427 = 21%.

WIN detail: 28 petitions bounced to ordinary proceedings · 16 petitions
refused on the merits · 1 first-instance refusal affirmed.
LOSE detail: 11 third-party appeals dismissed so the grant stands · 6
first-instance grants affirmed · 3 seizures granted by the appellate court
itself · (+2 affirmed-grants confirmed by hand).

## The thing the headline number hides

A "WIN" here is **almost always procedural and reversible.** The dominant
mechanism (50 of the reversals) is the court finding a *спор о праве* — that
a real owner exists, or was never joined as a party — which the simplified
особое-производство track cannot resolve, so the petition is **bounced to
ordinary litigation, which the administration can and does refile.** The
appellate court is not ruling that seizing a displaced person's home is
unlawful; it is correcting first-instance courts that rubber-stamped these
petitions without so much as joining the owner. The brake exists — but it
engages **only when an owner surfaces.** The whole structure presupposes a
claimant who appears; displacement is precisely what prevents appearing.

## ⇒ Why Mariupol is harsher — read the rulings, not the tally

The outcome tally below is the skeleton; the **mechanism** is in the reasoning
text and is documented separately in
[dnr_bezkhoz_citizenship_doctrine_2026-06](dnr_bezkhoz_citizenship_doctrine_2026-06.md).
Reading the full text of every Mariupol ruling showed the disparity is not
luck or paperwork but a **named, written doctrine**: the court treats a
Ukrainian citizen's flight from the siege plus their not holding a Russian
passport as voluntary abandonment, dismisses paid utilities, holds that the
owner's claim does not even create a dispute, and states the goal as transfer
to the state. Every genuine Mariupol residential LOSE applies it; no WIN does.

## The signal that actually matters for this project: Mariupol vs rest of DNR

**Twice-revised, 2026-06-27 — see correction notice at top for the full
chain.** Original 95-case table (hand-pulled sample, kept for the record):

| | LOSE | WIN | NEUTRAL | LOSE rate (of decided) |
|---|---|---|---|---|
| **Mariupol** | 7 | 8 | 1 | **44%** (7/16) |
| **Rest of DNR** | 13 | 37 | 23 | **18%** (13/73) |

First full-population pull (427 cases) gave 1.28×/p=0.49, suggesting the
2.5×/p=0.057 reading was a sampling artifact and the disparity might not be
real. Fixing the classifier bug above (58 metadata-only cards wrongly
absorbed into "ambiguous" instead of "text unpublished," 65% of them
Mariupol) shrank the decided-sample further but moved the point estimate
**back toward** the original finding. Current table, full 427-case docket,
fixed classifier:

| | LOSE | WIN | NEUTRAL | LOSE rate (of decided) |
|---|---|---|---|---|
| **Mariupol** | 8 | 13 | 1 | **36.4%** (8/22) |
| **Rest of DNR** | 24 | 52 | 23 | **24.2%** (24/99) |

Mariupol owners who appeal lose at **1.5× the rate** of owners elsewhere in
occupied Donetsk oblast — Fisher exact two-sided *p* = 0.29. Still not
statistically significant (decided-n is small on both rounds of correction),
but directionally consistent with the original finding rather than against
it, once the actual bug — not the sample size — is accounted for. **Read this
as: real disparity plausible, not proven; do not state a multiplier as fact.**
The textual citizenship-doctrine finding (next section) stands independent of
all of this: it documents *what the courts write*, not a population-level
rate, and a written doctrine is still a documented doctrine regardless of how
the statistics around it move.

## The "outside Russian Federation territory" thread

Only 3 of the full 427-case population state on their face that the owner is
«находится за пределами Российской Федерации» — unchanged from the original
95-case sample (these 3 were among the readable rulings either way). None of
the three won: one outright LOSE
(№33-1529/2025, the appellate court itself granted the seizure), two NEUTRAL
(remanded for merits, claim alive). The number is too small to carry weight
on its own, but it is consistent with the structural reading in
[legal_mechanisms_review](legal_mechanisms_review.md): Закон №66-РЗ's
personal-confirmation escape names only an RF-citizen passport, and territorial
presence — not citizenship on its face — is the lever the courts actually pull.

## Scope and caveats

- **Population, not sample, of the appellate layer** — but a *self-selected*
  population (only contested cases). Says nothing about the uncontested base.
- Full population (427 cases): 76 residential / 2 non-residential / 349
  unclear object type (the "unclear" share is large because text-unpublished
  cards carry no facts recital to classify from); 353 municipal-administration
  vs 36 State-Property-Fund vs 9 ministry vs 1 state-unitary-enterprise
  petitioners.
- **The residual UNKNOWN-rate gap, post classifier fix:** 58.5% of Mariupol's
  142 cases (83) carry the `UNKNOWN_full_text_not_published` flag, vs 44.6% of
  the rest-of-DNR's 285 (127) — a real ~14-point gap that survives the fix.
  (These two counts sum to the 210 total below; an earlier draft's 83.8%/63.9%
  did not and has been corrected — see the top notice.) Not yet explained:
  candidates are a genuine publication-policy or backlog difference at
  Mariupol's four contributing district courts, or a residual classifier gap
  specific to how Mariupol cards are formatted. Worth a direct side-by-side
  read of a sample of Mariupol vs. rest-of-DNR text-unpublished cards before
  drawing a conclusion either way.
- 210 of 427 cases have **no published ruling text** (metadata only, fixed
  classifier flags these as `UNKNOWN_full_text_not_published` rather than
  guessing); these are flagged, not force-classified.
- Reproducible end to end from `data/raw/` via `scripts/176`.
