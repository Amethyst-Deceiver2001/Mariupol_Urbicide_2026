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
    version** when one exists (`*-ru.html`). As of 2026-07-11, **every exhibit
    has a RU version**: `mariupol-master-dossier`, `dispossession-pipeline`,
    `two-property-systems`, `nakhimova-82-exhibit`,
    `case-study-II-registry-resale`, `case-study-III-stroiteley`,
    `case-study-IV-court-docket`, `case-study-troianda-metallurgov`,
    `lenina-104-106-108-110-exhibit`, `lenina133-apt19-exhibit`,
    `interactive-map`, `stakeholder-network`. `about.html` is trilingual
    in-page; `sources.html` is EN-only site chrome; the landing `index.html`
    carries an in-page По-русски toggle (EN default) rather than a separate
    RU file.
  - **EN-only target from a RU exhibit → caveat.** When a RU exhibit's
    Russian-labeled link necessarily points at an EN-only *exhibit* (currently
    none — see the list above; the rule stays for any future exhibit that ships
    EN-first), append the note
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

## 9. "Протокол Беркли," not "Берклийский протокол" (added 2026-07-08)

The Berkeley Protocol (on Digital Open Source Investigations) is always
rendered in RU-language text as **«протокол Беркли»** — never the adjectival
"Берклийский протокол." Check every RU exhibit's provenance/footer section
when adding or editing chain-of-custody language.

## 10. RU-exhibit quote fidelity, sourcing, and typography (added 2026-07-09)

Established during a full quote-by-quote audit of `dispossession-pipeline-ru.html`
against original Russian source material. Applies to every RU exhibit going
forward, not just that one file.

- **Quotes are drafted from the original Russian, never back-translated from an
  English exhibit's prose.** When a case-callout quotes a transcript, decree, or
  Telegram post, pull the exact wording from the raw source (`data/raw/*.json`
  message text, decree OCR, transcript file) — never paraphrase the EN exhibit's
  own callout and wrap it in guillemets. Verify every quote character-for-character
  against the source before publishing; a single inserted or dropped word (e.g. an
  added "вы," a "corrected" missing preposition) turns an evidentiary quote into a
  misquote. If the original has a grammatical quirk or apparent typo, preserve it
  and mark it `[так в оригинале]` rather than silently fixing it — except an
  obvious ASR mistranscription of an unrelated word (e.g. Whisper's "наториат" for
  "нотариат") may be silently corrected, since the point is fidelity to what the
  speaker said, not to the transcription tool's errors.
- **Never attribute a resident's paraphrase of an unseen document to the
  document's author.** If a Telegram post says "official X wrote, in essence,
  Y" and Y is the poster's own colloquial rendering (not the document's actual
  text), quote the *poster's own words* verbatim and attribute them to the
  poster — don't present Y as if it were official X's direct quote.
- **Never assert a real name behind a channel handle unless it's sourced.**
  Check the channel's own captured "about" text or an independently-sourced
  identification before writing "activist [Full Name]" for a handle like
  `@ssaniaworld` — if no source exists, cite the channel handle alone.
- **Спецзастройщик, not SPV/СПВ.** Render the Russian legal-entity type
  (специализированный застройщик, the special-purpose developer entity used in
  every no-tender land grant) as «спецзастройщик» throughout — never the
  transliterated Cyrillic "СПВ" and never the bare Latin "SPV" inside
  Russian-language prose.
- **Link to the original wherever a URL exists** — decree PDFs (glavadnr.ru,
  denis-pushilin.ru), Telegram posts/videos (`t.me/<channel>/<id>`), gosuslugi
  pages. Use a plain `target="_blank"` link with short visible text ("оригинал,"
  "видео," "оригинал поста") — don't print the bare URL in body text. If no
  public URL exists (an internal letter that was never published, a document
  known only via OCR of a photo), say so rather than link nothing silently.
- **No geoblock caveat needed in RU-exhibit link text or tooltips.** (This
  narrows `CLAUDE.md`'s general "always note geoblock status inline" rule
  specifically for RU-exhibit reader-facing links — the caveat is aimed at an
  English-speaking reader without Russian-language VPN access; it clutters a
  Russian-reading audience's experience for no benefit. The underlying
  `docs/sources.md` catalogue entry should still note geoblock status, since
  that's the researcher-facing record, not the reader-facing exhibit.)
- **No capture/research-processing dates in exhibit prose** — drop "найдено
  DD.MM.YYYY," "прочитан(о) DD.MM.YYYY," "эфир от DD.MM.YYYY" where the date
  given is *our* discovery/reading/transcription date, not a fact about the
  underlying event. A date stays if it's a fact the narrative needs — a
  decree's own signing date, a video's actual broadcast/upload date, an
  article's publication date, a deadline named in the source. Test: would a
  reader with no knowledge of this project's research process need this date
  to understand the claim? If the date only tells them when *we* did the
  work, cut it.
- **Proper names — bold on first mention, plain after.** The first time a
  named individual (official, judge, developer-entity beneficiary) appears in
  the document, wrap the name in `<b>`; every later mention of that same
  person stays plain (don't re-bold). This extends rule 7 (bold-consistency
  for companies) to people, and specifically mandates bolding at first
  mention rather than merely requiring consistency once bolded. Scope: named
  individuals and named entities/companies in narrative prose
  (`case-callout .cc-v`, footnotes, provenance text) — not in compact
  `chip-sub` reference labels, which stay unbolded to preserve their terse,
  uniform typography.
- **Direct quotes — italic (`<em>`), not just guillemets.** A verbatim quoted
  statement attributed to a specific speaker or document («...» following
  "заявляет," "пишет," "гласит," or similar) is wrapped in `<em>`. **Scare-quotes
  marking a euphemism or loaded institutional term in the exhibit's own prose
  stay plain guillemets, not italic** — e.g. «бесхозяйное», «недружественных
  стран», «признано бесхозяйным» used descriptively, not as reported speech.
  Test: is this a specific person or document's own words, being reported? →
  italic. Is this the exhibit's own narration flagging a euphemism? → plain
  «». A document's own *title*, quoted in guillemets, stays plain (titles are
  cited, not "spoken").
- **This pass covered `dispossession-pipeline-ru.html` only.** The other RU
  exhibits (`mariupol-master-dossier-ru.html`, `two-property-systems-ru.html`,
  `case-study-III-stroiteley-ru.html`, `case-study-IV-court-docket-ru.html`,
  `case-study-troianda-metallurgov-ru.html`, `nakhimova-82-exhibit-ru.html`)
  have not yet been audited against these rules — treat them as a backlog,
  not as already compliant.

## 11. Case-study identity — no ordinals; registry is authoritative (added 2026-07-11)

`docs/case_studies/REGISTRY.md` is the single source of truth for case-study
identity. The full rules live there; the display-facing consequences:

- **No ordinal numbering in display chrome or prose.** Kicker lines read
  `Case study · <modality label>` (EN) / `Дело · <метка модели>` (RU) — never
  "Case Study IV", «Дело V», "Exhibit B"/«Дело C». Those retired labels caused
  real collisions (two exhibits both claimed "Exhibit B") and implied a
  reading order that never existed. Modality codes («Модель 2», M1–M7) are
  fine in display — they classify, not enumerate.
- **Prose cross-references use short descriptive names**, linked: "the
  Stroiteley case study", «дело Нахимова, 82» — optionally followed by the
  accession code in parentheses in researcher-facing docs.
- **Every exhibited case study carries its accession code (`MUP-CS-NNN`) in
  its provenance block.** EN wording: "Accession code MUP-CS-NNN — permanent
  case-study identifier in the project register, docs/case_studies/REGISTRY.md."
  RU: «Учётный код MUP-CS-NNN — постоянный идентификатор дела в каталоге
  проекта, docs/case_studies/REGISTRY.md.»
- **New case studies**: take the next free code in REGISTRY.md *before*
  writing the exhibit; filename = subject slug (address or mechanism), never
  an ordinal. Legacy numerals fossilized in published filenames
  (`case-study-II/III/IV-*.html`) stay — URLs are immutable — but no new file
  ever gets one.
