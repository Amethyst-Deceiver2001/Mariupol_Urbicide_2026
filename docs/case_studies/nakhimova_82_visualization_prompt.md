# Claude-app visualization prompt — Нахимова 82 → Черноморский 1Б

Paste everything between the lines below into a new Claude.ai conversation. It is
self-contained (all facts embedded) and asks for a single-file interactive HTML
artifact with labelled image slots you can drop your collected visuals into.

---8<--- COPY FROM HERE ---8<---

Build me a single-file, self-contained **interactive HTML artifact** (inline CSS
+ vanilla JS, no external libraries, no build step — must run if I save it as one
`.html` file and open it). It is a forensic case-study exhibit documenting how
one residential building in occupied Mariupol was destroyed, demolished, and
replaced with a new building at a *different address* that was then sold off — an
"address-laundering" property seizure. Tone: sober, evidentiary, court-exhibit —
NOT marketing. Think investigative-journalism explainer (Bellingcat / NYT Visual
Investigations), dark neutral palette, generous whitespace, strong typography.

## Structure: a vertical scroll story with these sections

**1. Header / thesis.** Title: "Нахимова 82 → Черноморский 1Б". Subtitle: "How a
destroyed Mariupol home was rebuilt under a new address and sold to the
occupier's population." One-line thesis: a 36-apartment privately owned building
was destroyed in 2022, demolished by occupation decree, and replaced on the same
footprint by a 51-apartment building at a new address — now 94% sold, while the
original owners are off the map.

**2. The footprint map callout.** Show that OLD and NEW are the same spot:
coordinates 47.0760°N, 37.5125°E, ~10 m apart. Include an `<iframe>` or static
embed slot for a map centered there (leave a clearly-labelled IMAGE/MAP SLOT —
see slots list). Caption: "Same site. Different address. That gap is the seizure."

**3. The five-leg lifecycle** — the core. A horizontal or vertical stepper /
timeline with 5 stages; each stage is a card with: an IMAGE SLOT, a date, a
headline, 2–3 lines of text, and a small "SOURCE" footnote line. Make the cards
visually progress (e.g. a thin connecting line / progress rail). The five stages:

- **1 · INTACT — before 2022.** 4-storey residential building (МКЖД), 36
  apartments, privately owned. SOURCE: Russian federal damage tracker (building
  record).
- **2 · DESTROYED — March 2022.** Burned in the siege. 100% destruction. SOURCE:
  Russian federal damage/reconstruction tracker, destruction = 100%, Priority
  Phase II.
- **3 · DEMOLISHED — 29 Sep 2022.** Razed under occupation order Распоряжение ГКО
  ДНР №56. SOURCE: DNR MinStroy demolition register.
- **4 · REBUILT — 29 Dec 2023.** A new 5-storey, 51-apartment building "Дом на
  Нахимова" is commissioned — but registered at the NEW address пер. Черноморский
  1Б, new cadastral 93:37:0010410:173. Land was leased to the developer WITHOUT
  auction (Распоряжение №289, 07 Sep 2023). SOURCE: Russian ЕИСЖС / наш.дом.рф
  registry, object 54284.
- **5 · SOLD — 2024–2026.** 94.3% of apartments sold, largely to Russian buyers
  via the federal 2% subsidized mortgage open to any Russian citizen. SOURCE:
  same ЕИСЖС registry (live sold-out %).

**4. The "smoking gun" panel.** Visually emphasized (boxed/quote style). Two
facts side by side from the Russian state's OWN registry:
- Project NAME: «Дом на Нахимова» → admits it stands on the Нахимова site.
- Registered ADDRESS: пер. Черноморский 1Б → the address break that erases the
  link to destroyed пр. Нахимова 82.
Plus: the cadastral 93:37:0010410:173 appears in BOTH the land-grant order
("территория ограничена проспектом Нахимова, улицей Черноморской") AND the new
building's registration — one number stitching old footprint to new title.

**5. The arithmetic panel.** A big bold visual contrast: "36 apartments
(privately owned, destroyed) → 51 apartments (94% sold to incomers)". Make the
36→51 and the 94% prominent (large numerals). Caption: "The original owners
receive nothing — on paper, their address no longer exists."

**6. Beneficiary card.** ООО «СЗ-1 «Порфир»» (ИНН 9310009271, ОГРН 1239300008870,
registered 11 Jul 2023; brand ГК ЮгСтройИнвест). Label it "Named beneficiary".

**7. Legal mapping strip.** Two compact badges:
- RD4U restitution: category A3.6 (loss of access in occupied territory) +
  A3.1/A3.2 (destruction of residential property).
- Rome Statute: art. 8(2)(b)(viii) (transfer of occupier's own population) +
  appropriation of property, art. 8(2)(a)(iv).

**8. Provenance footer.** Small print: every fact is drawn from captured
occupation/Russian-government records, each stored with a SHA-256 hash and
retrieval timestamp (Berkeley Protocol chain of custody). Note: "Occupation
registrations are evidence of the seizure act, not valid title. Ukraine does not
recognize them."

## IMAGE / MAP SLOTS (critical)

I will drop in my own collected visuals later. For EVERY image/map, render a
styled placeholder `<div class="slot">` with: a dashed border, the slot's label
in the center, and an HTML comment marking exactly where to paste a URL, e.g.
`<!-- SLOT: leg1-intact — replace src below -->` then an `<img src="" alt="...">`.
Make it trivial for me to swap a placeholder for a real image/iframe by editing
one line. The slots I need, in order:
1. `map-footprint` — map centered on 47.0760, 37.5125 (old+new site).
2. `leg1-intact` — pre-war Street View / photo of пр. Нахимова 82.
3. `leg2-destroyed` — satellite/Google Earth or photo of the destroyed building, 2022.
4. `leg3-demolished` — cleared lot, late 2022 / 2023.
5. `leg4-rebuilt` — наш.дом.рф render / photo of «Дом на Нахимова» / Черноморский 1Б.
6. `leg5-sold` — Авито/ЦИАН listing screenshot or 2%-mortgage banner.

Each slot should gracefully show the labelled placeholder if no image is set, so
the artifact looks complete even before I add visuals.

## Polish
- Responsive (works on a laptop and when exported to PDF/print — add a sensible
  print stylesheet).
- A small sticky timeline/progress indicator on the left as I scroll the 5 legs
  is a nice touch.
- All Cyrillic must render correctly (UTF-8). Keep all the dates, numbers,
  decree numbers, cadastral, INN/ОГРН, and SHA-256 references EXACTLY as given —
  do not invent or round any fact. If you need a fact I didn't supply, leave a
  visible "[TODO: ...]" rather than guessing.

---8<--- COPY TO HERE ---8<---
