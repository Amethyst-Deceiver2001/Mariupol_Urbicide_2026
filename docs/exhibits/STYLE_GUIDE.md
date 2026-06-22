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
translate too: "Russian Ministry of Construction," "Public Corporation 'Unified
Construction Client'," "Mariupol City Council."

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
