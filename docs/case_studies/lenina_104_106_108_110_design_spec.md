# Design Specification — пр. Ленина(Мира) 104/106/108/110 Exhibit

A brief for building a standalone visual exhibit (HTML, single-file, same
lineage as `docs/exhibits/nakhimova-82-exhibit.html` and
`case-study-II-registry-resale.html`) from the case study at
`docs/case_studies/lenina_104_106_108_110_restoration_without_restitution.md`
and the 30-file visual package at
`data/exports/designer_package/lenina_104_106_108_110/` (see its
`manifest.csv` for every asset's path/SHA-256/caption).

This is the THIRD exhibit in this lineage (after Нахимова 82 and the
registry-resale case study) — reuse the established visual system rather
than inventing a new one; consistency across exhibits matters more than any
one exhibit looking distinct.

## Visual system (inherited, do not redesign)

- **Palette**: dark forensic-dossier ground (`--ink:#0c0e11`), warm paper-tone
  text (`--paper:#e9e7e1`), two accent hues that map to specific evidentiary
  roles, not decoration:
  - `--evidence` (red, `#cd4030`) = loss / rupture / the contradiction itself
  - `--stamp` (gold, `#c79a44`) = state apparatus / official paper trail /
    provenance
  - **New for this exhibit**: add a third accent, `--testimony` (a desaturated
    blue, e.g. `#5a7d9a`), for resident-voice material (the letter, the
    on-camera testimony, the door-notice photos, the casualty record) — this
    case study has substantially more first-person material than the prior
    two exhibits and it should read as visually distinct from both the
    official-paper (`--stamp`) and the damage/rupture (`--evidence`) registers.
- **Type**: serif body (Georgia) for reading flow, mono (ui-monospace) for
  data/citations/SHA-256s, a bold sans display face for headers. Same as
  prior exhibits.
- **Layout**: sticky left index rail (210px) + single reading column
  (max ~760px measure), numbered sections with an `.eyebrow` label
  (`"01 · The footprint"` style) above each `<h2>`. Sticky top bar with
  exhibit title + custodian mark.
- **Sourcing footer**: every section ends with a small mono-font citation
  block (SHA-256 prefix + date + source URL), matching the existing exhibits'
  citation style — do not invent a new citation format.

## Section structure (maps directly to the case study's own headers)

Reuse the case study's section order — it's already sequenced for narrative
build-up; don't reshuffle it for the exhibit.

1. **Hero / eyebrow `"00 · Four buildings, one decree"`** — the bolded
   opening paragraph from the case study verbatim (it's already exhibit-
   ready prose). Visual: a 4-up grid of one representative image per
   building — recommend `104/verified_siege_damage/2022-05_siege_damage_facade.mp4`
   (poster frame), `106/verified_siege_damage/courtyard_view_106.jpg`,
   `108/demolition/demolition_one_entrance_partial.mp4` (poster frame),
   `110/prewar_baseline/1979_prewar_baseline_pastvu.jpg` — deliberately
   four DIFFERENT visual registers (siege damage / restoration / demolition /
   prewar) to make the "wildly different physical fates" claim legible at a
   glance before any text is read.
2. **`"01 · The four properties"`** — the property table. Render as a real
   table (mono font), not a redesigned card grid — the existing exhibits use
   plain tables for dense tabular claims and it works.
3. **`"02 · The contradiction"`** (Tracks 1–3) — this is the spine of the
   exhibit. Three sub-blocks, color-coded:
   - Track 1 (decree) → `--stamp` accent, cite the MinStroy CSV.
   - Track 2 (restoration in progress) → `--testimony` accent, the chat
     quotes as pull-quotes (the existing exhibits' pull-quote treatment —
     large serif, left rule in the section's accent color) + the
     `106/construction/` and `106/key_artifacts/` photos.
   - Track 3 (registry stripping) → `--evidence` accent, the 91-apartment
     count as a large mono numeral (the prior exhibits use oversized mono
     numerals for headline statistics — reuse that component).
4. **`"03 · The human cost"`** (Track 4, civilian casualties) — **NEW
   section type for this exhibit lineage**, handle with care:
   - This is the only section with named deceased individuals. Keep it
     visually restrained — no oversized numerals, no red accent (which
     elsewhere in the system means "the contradiction," not "death"; reusing
     it here would muddy the visual grammar). Use a quiet, list-form layout:
     name, dates, one-line circumstance, source link, in a neutral/muted
     tone. A small map thumbnail (Google My Maps screenshot, if one is
     captured) showing the courtyard-grave pin would be appropriate; do not
     dramatize.
   - Explicitly do NOT include the unverified bodies-in-blankets video lead
     (`AmPu1gRLh-M`) anywhere in the exhibit — it is not evidence yet.
5. **`"04 · The residents' own record"`** (the letter to Putin + the
   on-camera testimony video + the stalled-reconstruction walkthrough) —
   `--testimony` accent throughout. The letter's first page (already
   rendered as `shared/documents/Письмо в инстанции_p1-1.jpg`) is strong
   enough to use as a full-width image, not just a thumbnail — it has
   embedded photos of its own (the burning balcony, the restored facade)
   that read well at exhibit scale. Embed the testimony video and the
   walkthrough video as actual `<video>` elements (poster frame + controls),
   not links — this is the "every piece of evidence as visual material, not
   reference" requirement carried into the exhibit itself.
6. **`"05 · Paper trail, continued"`** (the Решение №I/3-3 compensation-
   housing finding) — `--stamp` accent. Use the rendered first-page thumbnail
   (`shared/documents/Reshenie_I_3_3_ot_13.02.2026_p1-01.jpg`) full-width.
   **Mandatory caveat box** (the existing exhibits use a bordered aside for
   methodological caveats, e.g. the Nakhimova exhibit's note on the
   negation-regex bug) stating the per-apartment OCR count is an unverified
   lead, not a confirmed figure — do not let the exhibit overstate this
   beyond what the case study itself claims.
7. **`"06 · Reallocation, demand side"`** — the resale listings (106/108/110)
   as a 3-up comparison card (price/area/floor/status per listing, pulled
   from the manifest captions verbatim) + the dnr.red listing thumbnail
   placeholder (it's HTML-only, no screenshot exists yet — render as a
   styled text card using the listing details already in the manifest
   caption, not a fake screenshot).
8. **`"07 · Legal mapping"`** — RD4U + Rome Statute paragraphs from the case
   study, verbatim. Same treatment as the existing exhibits' closing legal
   section (`06 · Legal mapping` in the Nakhimova exhibit).
9. **Provenance footer** — full chain-of-custody table, mono font, every row
   from the case study's Provenance table. This can be long; the existing
   exhibits collapse long provenance tables behind a `<details>` toggle —
   reuse that pattern rather than letting the exhibit run very long.

## Asset handling

- Reference images/video directly from
  `data/exports/designer_package/lenina_104_106_108_110/` via relative paths
  (the exhibit HTML should live at `docs/exhibits/lenina-104-106-108-110-exhibit.html`,
  so paths are `../../data/exports/designer_package/lenina_104_106_108_110/...`)
  — do NOT inline base64 the videos (file sizes are 10s of MB); images under
  ~500KB can be inlined if the exhibit needs to be a single portable file,
  but check with the user before doing that given the package's current size.
- The two PDF thumbnails generated this session
  (`shared/documents/*_p1-*.jpg`) are exactly the kind of asset this exhibit
  needs — full-resolution, real renders, not placeholders. Use them directly.
- HTML-only captures (the resale listings, two of them) have NO image
  asset — see section 7 above for how to handle that gap honestly rather
  than fabricating a screenshot.

## What NOT to do

- Don't invent new color meanings beyond the three accents above.
- Don't dramatize the casualty section — no large pull-quotes, no oversized
  numerals, no red.
- Don't cite the OCR'd apartment count from Решение №I/3-3 as confirmed —
  the case study itself flags it as unverified; the exhibit must carry that
  caveat forward, not silently drop it for visual cleanliness.
- Don't cite the `AmPu1gRLh-M` video anywhere.
- Don't reshuffle section order relative to the case study doc — the
  narrative sequencing there is deliberate (footprint → contradiction →
  human cost → residents' own record → paper trail → demand side → legal
  mapping) and was arrived at after multiple correction rounds; the exhibit
  should follow it, not improve on it independently.

## On using Claude Design for this

Claude Design (claude.ai/design) and the `DesignSync` tool that feeds it are
built for syncing a **design system** (a real, compiled React component
library) into Claude's design agent, so it can build new UI *out of a
customer's actual components*. That doesn't fit this task — there's no
component library here, and the deliverable is a one-off evidentiary
document, not a reusable UI system. Using `DesignSync`/Claude Design for
this would mean treating this case study's assets as if they were a design
system's components, which they aren't.

The actual precedent already in this project is simpler and more direct:
the prior two exhibits (Nakhimova 82, registry-resale) were built as
standalone HTML files, most likely authored in a claude.ai chat (where
Claude can render and iterate on an HTML artifact live) and then saved into
`docs/exhibits/`. That's the right tool for this job too — either:
1. **I write the HTML directly here**, following this spec, the same way I'd
   write any other file — fully scriptable, fits this session's workflow,
   no extra tool needed.
2. **You take this spec + the manifest into a claude.ai chat** (not
   Claude Design specifically) and iterate on the HTML interactively/
   visually before it lands in the repo, the same way the first two exhibits
   were likely made.

Recommend (1) if you want this done now in this session; I can write
`docs/exhibits/lenina-104-106-108-110-exhibit.html` directly. Say the word
and I'll start.
