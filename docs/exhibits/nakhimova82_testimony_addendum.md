# Addendum — Нахимова 82 testimony + award (2023 & 2025)

**For the conversation iterating on the visual-narrative exhibits.** This is
new evidence captured 2026-06-13, additive to `docs/case_studies/
nakhimova_82_chernomorsky_1b.md` and `nakhimova-82-exhibit.html` ("Exhibit
A"). It does not change any of the 5 legs already documented there — it adds
two bracketing dates: a first-person testimony from *before* the new building
opened, and the occupation administration's own publicity for the finished
building *after*.

Both are now in the forensic store (`forensics.capture_source()`, SHA-256 +
`.meta.json`, logged to `source_document`), captured by
`scripts/59_fetch_nakhimova82_testimony.py`. Neither is loaded into
`corroboration` yet — see "Where this could go in the DB" below.

---

## Leg 0 — testimony (27 Dec 2023)

**Source:** Telegram, Олег Царёв channel, post
[t.me/olegtsarov/9754](https://t.me/olegtsarov/9754) — 180K views, edited.
SHA-256 `9a2264f7…891691`, captured 2026-06-13.

Царёв relays reader comments responding to his earlier post about unfair
post-occupation housing distribution in Mariupol. One comment names the
property directly:

> «…имел квартиру на Нахимова, 82. Дом был в ОСМД. Его снесли, построили
> ипотечный и распродали. Ни одного бывшего владельца там теперь нет. Так
> происходит со всеми лакомым кусочками в городе. Бывших владельцев тупо
> выкидывают на улицу. Обращались и в СК и в прокуратуру и в Администрацию
> Президента РФ и у депутата от Единой России были с более сотней обращений.
> Бестолку. Всё пересылают в ДНР для решения вопроса.»

> *"...I had an apartment at Nakhimova 82. The building was managed by an
> OSMD [condo association]. It was demolished, a mortgage-development was
> built and sold off. Not a single former owner is there now. This is what
> happens with every prime spot in the city. Former owners are simply thrown
> onto the street. We complained to the Investigative Committee, the
> Prosecutor's Office, the Administration of the President of Russia, and a
> United Russia deputy — over a hundred complaints. No use. Everything gets
> forwarded to the DNR to 'resolve'."*

Other comments in the same thread (not address-specific, but useful context
for the master dossier's housing-distribution narrative):
- "дом с часами" (the clock-tower building) — demolished, rebuilt, nothing
  given to former residents.
- "В 60-70% случаев получить какую-либо квартиру... практически невозможно... А
  это время [1,5-2 года] нужно где-то жить" — 60-70% of cases can't get any
  replacement unit; 1.5-2 year waits where they're allocated at all.
- "Дома, которые во всеуслышание пообещали людям на Невском/Изумрудном, стоят
  пустые в основной массе" — the Nevsky/Izumrudny buildings publicly promised
  to residents stand mostly empty.

This is a **first-person admission, dated before the replacement building was
even commissioned** (commissioning was 29 Dec 2023 per the ЕИСЖС record — two
days after this post), describing exactly the demolish→mortgage-sale pattern
that the administrative-record chain (legs 3-5 of the case study) proves from
the other direction. Two independent lines of evidence — a resident's
complaint trail and the developer's own registry filings — converge on the
same building, the same outcome, the same ~month.

---

## Leg 6 — the occupation's own victory lap (3 Oct 2025)

**Source:** Telegram, МАРИУПОЛЬ 24 channel, post
[t.me/mariupol24tv/104461](https://t.me/mariupol24tv/104461) — 1.52K views.
SHA-256 `8b8b6834…86fbb2`, captured 2026-06-13.

> «Две мариупольские постройки завоевали призовые места в престижном
> смотре-конкурсе «АРХИТАВР» ... По итогам смотра-конкурса бронзовым дипломом
> в номинации «Многоквартирные жилые здания» отмечен проект решения
> многоквартирного жилого дома со встроенными помещениями по проспекту
> Нахимова, 82, который подготовил Проектный институт Архитектуры и
> Строительства... Как отметила начальник управления градостроительства и
> архитектуры АГО Мариуполь Наталья Клочкова, две высокие награды из более 160
> представленных на конкурс проектов – достойное признание заслуг
> архитекторов, которые работают над преображением Мариуполя в современный
> комфортный российский город.»

> *"Two Mariupol buildings won prizes at the prestigious 'ARKHITAVR'
> competition... A bronze diploma in the 'Multi-apartment residential
> buildings' category went to the design for a multi-apartment residential
> building with ground-floor commercial space at Nakhimova Avenue, 82,
> prepared by the Design Institute of Architecture and Construction... As
> Natalya Klochkova, head of AGO Mariupol's city-planning and architecture
> department, noted, two top awards out of more than 160 entries are
> well-deserved recognition for the architects working to transform Mariupol
> into a modern, comfortable **Russian city**."*

**Why this matters:**
- It is the occupation administration **naming the address "Нахимова, 82"
  itself**, in 2025, for the *new* building — a fourth independent admission
  that "Нахимова 82" and the Черноморский-1Б building are the same site (after
  the DNR land order, the federal RPD declaration, and the developer's render
  filenames — see "smoking gun" section of the case study).
- A **named official** (Наталья Клочкова, head of city-planning/architecture,
  AGO Mariupol) is quoted using explicitly Russification language —
  "transforming Mariupol into a modern comfortable **Russian** city" — about a
  competition entry for *this specific building*. That is directly usable for
  the Rome Statute art. 8(2)(b)(viii) framing the dossier already argues from
  the demand-side mortgage-sale data; this is the supply-side, in an
  official's own words.
- It closes the loop with Leg 0: the same building a resident describes (Dec
  2023) as "snесли... построили ипотечный и распродали, ни одного бывшего
  владельца там теперь нет" is, 22 months later, the administration's
  award-winning poster child.

---

## Suggested use in the exhibits

- **Exhibit A (`nakhimova-82-exhibit.html`):** add a 6th timeline marker after
  "29 Dec 2023 — commissioned" (or before, since this post is 27 Dec 2023):
  *"27 Dec 2023 — a Mariupol resident's complaint, naming this address, posted
  to a 180K-view Russian Telegram channel: demolished, rebuilt as a mortgage
  development, no former owner retained a unit."* And after the existing
  timeline: *"3 Oct 2025 — AGO Mariupol's head of architecture publicly cites
  the replacement building (named 'Нахимова, 82') as an example of
  'transforming Mariupol into a modern comfortable Russian city.'"*
- **Master dossier / preamble:** the Klochkova quote is a strong candidate for
  a pull-quote near the Rome Statute / population-transfer framing — it is a
  named occupation official, on the record, using the word "Russian city" to
  describe redevelopment of a residential building whose former owners were
  dispossessed.
- Both posts are **primary-source, dated, high-reach** (180K and 1.52K views
  respectively) — useful for "this isn't just our inference, the occupation
  side and Mariupol residents are saying it too" framing.

---

## Where this could go in the DB (not done)

Tier-3 sub-layer **S5 (testimony_ref)** in
`docs/tier3_corroboration_design.md` is currently pure design — these two
posts are the first concrete candidates. A future `corroboration` row for
property **5865** (Нахимова 82 / Черноморский 1Б, per
`nakhimova_82_chernomorsky_1b.md`) with `kind='testimony_ref'`,
`source_doc_id` pointing at SHA `9a2264f7…891691`, `verdict='confirms'`,
`observed_start=observed_end='2023-12-27'` would be the natural load — but per
the S5 counting-rule question still open in the design doc (is a Telegram
testimonial an "independent" family on the same footing as UNOSAT?), this
should wait for that design decision rather than being loaded ad hoc.

---

## Provenance

| Leg | Source | SHA-256 | Captured |
|---|---|---|---|
| 0 (testimony, 27 Dec 2023) | t.me/olegtsarov/9754 (`?embed=1`) | `9a2264f7…891691` | 2026-06-13 |
| 6 (award, 3 Oct 2025) | t.me/mariupol24tv/104461 (`?embed=1`) | `8b8b6834…86fbb2` | 2026-06-13 |

Both raw HTML + `.meta.json` sidecars in `data/raw/`; manifest at
`data/parsed/nakhimova82_testimony_manifest.json`. Fetched directly (public
Telegram embed widgets, non-geoblocked, same precedent as scripts 52/54-58).

*Telegram posts are third-party statements (resident complaints, occupation
press), not court or registry records — treat per the project's normal
caveat: evidence of the *narrative/admission*, not independently verified
fact, except where they corroborate records already in the DB (as Leg 0
does for legs 3-5).*
