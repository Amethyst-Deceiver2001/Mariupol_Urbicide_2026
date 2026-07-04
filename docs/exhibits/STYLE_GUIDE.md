# Exhibit Style Guide — presentation rules (project-wide)

Standing rules for every HTML exhibit in `docs/exhibits/`, agreed 2026-06-19 after
the `lenina-104-106-108-110-exhibit.html` revision pass and **rolled out
2026-06-20** to all five exhibits (`nakhimova-82-exhibit.html`,
`case-study-II-registry-resale.html`, `dispossession-pipeline.html`,
`mariupol-master-dossier.html`, and the compiled `stakeholder-network.html`).
Every *new* exhibit built from here on should follow these rules from the start.

Two deliberate exceptions kept during the back-port, both evidentiary: (a) verbatim
Russian quotations shown with an English translation immediately adjacent (resident
chat blockquotes, the «razrushka» language note) are left in the original — the
original *is* the evidence; (b) the literal occupation markings reproduced as design
elements (the "ДЕТИ" theatre marking, the "БЕСХОЗЯЙНАЯ"/ownerless stamp motif) are
kept in Cyrillic for the same reason. Everywhere else, terms render English-first
with the original in a click-popup (`.xlit`) or a `title=` tooltip.

Overall goal: accessible to a layman audience at first glance. Lead with narrative,
not technical apparatus — court-admissibility lives in the underlying data/DB and
the case-study `.md` files, not in exhibit prose.

## 1. Transliteration (English-language exhibits only)

Render Cyrillic in Latin script in the body text, with a click-to-reveal popup
(`.xlit` component) holding the original. Click/tap toggles a small popup card;
click elsewhere closes it; keyboard-accessible (Enter/Space).

- **Toponyms** (street names, districts, place names) get the dual-spelling popup
  (`.xlit.wide` + `.pop-line` rows): pre-war **Ukrainian** form and occupation
  **Russian** form, each labeled. Don't collapse to one spelling — the dual form is
  itself evidentiary (renaming as de-Ukrainization).
- **Personal names** get a single-spelling popup (the original Cyrillic as it
  appears in the source document). Use Russian-form transliteration when the
  source document is Russian-language, to stay consistent with the address style
  already in use; flag to the user if a particular name's bearer is a Ukrainian
  civilian and Ukrainian-form transliteration is preferred instead — this hasn't
  been settled as an absolute rule, just a default.
- **RU/UK-language exhibit variants** (future trilingual plan): skip this
  transliteration layer entirely. It exists only to serve English-speaking
  readers who can't read Cyrillic.

## 2. Key terms, decrees, institutions

Render in **English translation** as the visible text. The Russian (or relevant
original-language) term is available on demand, not removed:
- Inside a clickable link (e.g. a stakeholder name, a chip linking elsewhere): use
  the `title="..."` attribute (hover tooltip) — a nested click-popup would conflict
  with the link's own click/navigation.
- In plain prose (not inside a link): use the same `.xlit` click-popup component
  used for toponyms/names.

Example: "Demolition Decree No. 56 (29.09.2022)" in the body, with
"Распоряжение ГКО ДНР № 56 от 29.09.2022" as the popup/title. Institution names
translate too: "Russian Ministry of Construction," "Public-Law Company 'Unified
Construction Client'" (ППК — публично-правовая компания, a Russian legal form
for state-created entities — not "Public Corporation"), "Mariupol City Council."

## 3. Sourcing — no inline hashes in the narrative

Don't print `sha256 ...` fragments inside body sections, figcaptions, or pull-quote
citations. State once, briefly (e.g. the sticky top bar), that every artifact is
sourced from the original and hashed for the record. The full chain-of-custody
catalogue — every hash, source URL, and capture date — belongs in a single
**Provenance** section at the end of the exhibit, collapsed behind a `<details>`
(not open by default), explicitly framed as being there for readers with a
professional or legal interest in independent verification. That section is the
"separate catalogue" — nothing more granular needs to exist yet, but if a project-
wide hash index is ever built, this section should link to it instead of
duplicating it.

## 4. No internal/methodological notation in the narrative

Never surface DB field names, table/column names, internal script numbers, or
internal jargon in exhibit prose — e.g. `corroboration.kind = civilian_casualty`,
`property_id`/`pid`, raw lat/long geocode columns, `registry_inclusion`,
"the spine," "differential entries," regex/keyword-classifier bug notes. Translate
every one of these into plain narrative English, or drop the detail if it adds
nothing for a lay reader. This kind of detail belongs in the case-study `.md` file
and project memory, not the exhibit.

## 5. Named-individual display format (added 2026-06-21)

For accountability-track individuals (officials, judges, prosecutors — anyone named
for Rome Statute/criminal-accountability purposes, not privacy-minimized civilians),
render the name as **conventional English order — given name first, surname
second** (e.g. "Denis Pushilin," not "Pushilin D.V." and not a mechanical
letter-by-letter transliteration of initials). Pair it with the **full Cyrillic
ФИО** (given name + patronymic + surname, not just initials) wherever it can be
researched — initials-only sourcing (typical of court-docket records) is a
placeholder, not the end state.

- **Non-link contexts** (profile cards, command-spine list items, captions): show
  the full Cyrillic ФИО as **visible text directly below** the English name, in
  smaller/muted styling (see `.person-fio` / `.spine-fio` in
  `mariupol-master-dossier.html` for the reference implementation) — not hidden
  behind a tooltip. The point of a profile card is to show both forms at once.
- **Link contexts** (a name that is itself a clickable link, e.g. a
  stakeholder-network reference): keep rule 2's `title=` tooltip pattern — a
  nested click-popup would conflict with the link. The tooltip should still hold
  the *full* ФИО once researched, not just initials.
- **Research depth is bounded by significance, not applied uniformly.** Spend
  real effort (decree archives, kremlin.ru, regional news, VK/social posts) on
  the figures a reader is actually likely to focus on — apex chain-of-command,
  named case-study subjects, the most-cited judges/prosecutors. Don't burn
  effort chasing patronymics for every name in a 28-judge docket table or a
  50+-node stakeholder graph; "Surname I.O." is an acceptable, honest fallback
  for long roster lists where the source material itself never gives more.
  If a specific search comes back empty, leave the initials-only form rather
  than guessing — never fabricate a given name or patronymic.
- Once a full name is confirmed for someone who also appears as a node in
  `stakeholder-network.jsx`, update that node's display there too (a
  `DISPLAY_NAME_OVERRIDES`-style map keyed by `node_id`, not a hand-edit of the
  generated bundle) and rebuild per
  `memory/stakeholder_network_rebuild_style_audit_2026-06-20.md`'s documented
  esbuild pipeline — don't let the two exhibits drift to different name forms
  for the same person.

## 6. Cross-linking pattern (established, keep using)

- Named stakeholders (officials, contractors, agencies) → link to
  `../stakeholder_network.md` (relative from `docs/exhibits/`). No per-entity
  anchor exists there yet — the React `stakeholder-network.jsx` component has no
  hash-routing, so it can't be deep-linked to a specific node. If per-node linking
  is ever wanted, that requires adding `location.hash` routing to the jsx component
  first — a separate task, not assumed done.
- Cited legislation/decrees → link to the matching rung card in
  `dispossession-pipeline.html#card-X` (rungs A–H; verify the anchor id is real
  before using it — `grep 'id="card-'` in that file).
- **Exhibit-to-exhibit references (added 2026-07-03).** Whenever an exhibit
  mentions another exhibit by name (a sibling case study, the pipeline, the
  stakeholder network, the master dossier, the interactive map), that mention
  is a hyperlink — don't leave a named cross-reference as plain prose.
  - **Language targeting.** From a **RU** exhibit, link to the target's **RU
    version** when one exists (`*-ru.html`). RU versions currently exist for:
    `mariupol-master-dossier`, `case-study-III-stroiteley`,
    `case-study-IV-court-docket`, `case-study-troianda-metallurgov`,
    `two-property-systems`, `nakhimova-82-exhibit`. Everything else is
    EN-only. (A `dispossession-pipeline-ru.html` was drafted 2026-07-03 but
    pulled offline pending review — don't re-link it until it's back.)
  - **EN-only target from a RU exhibit → caveat.** When a RU exhibit's
    Russian-labeled link necessarily points at an EN-only *exhibit*
    (dispossession-pipeline, interactive-map, stakeholder-network,
    case-study-II, lenina-133, lenina-104…-110), append the note
    `(пока нет перевода, ссылка временно ведёт на английскую версию)` right after
    the link — as a small muted `<span>` inline, or as a `display:block` note
    under a card-style `.cs-link`, styled
    `font-family:var(--font-mono);color:var(--muted)`. In compact top-nav chrome
    where an inline parenthetical would wreck the layout, carry the same text in a
    `title=` tooltip on the link instead and put the visible caveat on the
    substantive body mention of that exhibit.
  - **No caveat needed** for: the `English version` language toggle; nav links
    already labeled with the English word (`about`, `sources`); and the recurring
    footer `автор → about.html` boilerplate — `about`/`sources` are site chrome,
    not exhibits whose content the reader needs translated. EN→EN links never take
    a caveat (every RU exhibit has an EN counterpart, so an EN exhibit never lacks
    a same-language target).

## 7. Bold consistency for proper names (added 2026-07-03)

If a company, organization, or other proper-name entity is rendered in `<b>` at
its first mention in a section, render it in `<b>` at every subsequent mention
in that same section too — never bold-then-plain for the same entity within
one section. (Bolding used purely for numeric/factual emphasis — a ruble
figure, a percentage, a date — is unaffected by this rule and doesn't need to
carry through to every later mention of that same number.) Applies per
document; EN and RU variants are checked independently since a term bolded in
one language's prose doesn't obligate the other to match unless the same
entity is also bolded there. Audited 2026-07-03 across
`case-study-troianda-metallurgov.html`/`-ru.html`: no company/entity name is
currently rendered in `<b>` in either file (institution names are conveyed via
the `.xlit`/`title=` popup pattern from rule 2 instead) — so this rule has no
current violation to fix, it's a guardrail for future edits.

## 8. Non-recognition of DNR institutions — the «ГКО ДНР» rule (added 2026-07-03)

This project does not recognize the "Donetsk People's Republic" as a state or
its "State Defense Committee" (Государственный комитет обороны, ГКО) as a
lawful authority. That non-recognition is enforced typographically, in every
exhibit, every time this body is named:

- **RU-language text** (visible prose, `title=` tooltips, `.pop` popup
  content): always **«ГКО ДНР»** — Cyrillic К (never the Latin-alphabet
  look-alike "K"), always paired with "ДНР" (never bare "ГКО" standing
  alone), always inside guillemets. "Постановление ГКО ДНР №162" →
  "Постановление «ГКО ДНР» №162"; "Распоряжение ГKO №56" (typo'd K, missing
  ДНР) → "Распоряжение «ГКО ДНР» №56."
- **EN-language visible text**: always **DNR &ldquo;State Defense
  Committee&rdquo;** — "DNR" bare (consistent with how this project already
  writes DNR &ldquo;Supreme Court&rdquo; elsewhere — the geographic/
  adjectival "DNR" label isn't itself scare-quoted, only the institutional
  claim is), the institution name always quoted, always the full "State
  Defense Committee" (retire the partial forms "GKO DNR," "DNR
  State-Committee," "DNR State Committee," and the bare transliteration
  "GKO" used as a noun). E.g. "DNR State Defense Committee Resolution No.
  162" → "DNR &ldquo;State Defense Committee&rdquo; Resolution No. 162";
  "GKO DNR Distributive Order No. 56" → "DNR &ldquo;State Defense
  Committee&rdquo; Distributive Order No. 56."
- Applies to every named GKO DNR instrument across exhibits (Resolution/
  Постановление No. 1, 162, 164, 175, 245, 263, 290, 300; Directive/
  Распоряжение No. 56, etc.) — not just the ones already touched as of this
  pass. Extend this rule to any newly-cited GKO DNR document going forward
  without being asked again.
