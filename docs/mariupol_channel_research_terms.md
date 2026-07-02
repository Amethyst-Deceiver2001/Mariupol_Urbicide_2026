# Reusable term bank for mining occupation-Telegram channels

Distilled from the 2026-07 deep mining of @mariupol_nash (159K messages,
`docs/nash_channel_findings_2026-07.md`). These are the Russian search patterns
that proved **productive vs. noisy** on a general occupation-city channel, so a
new channel (`@mizodnr`, `@donurcenter`, `@mrpl_besxozxata`, building chats,
whatever comes next) can be swept without re-deriving the taxonomy. The machine
form of this list lives in `scripts/225_nash_flag_and_media_manifest.py`
(`SIGNALS` / `LEGAL_RX` / `ENTITY_RX`) — point it at a different `SOURCE_TYPE`
to reuse it verbatim.

**The core lesson from this session:** raw keyword frequency lies. On a general
city channel, `суд*` returns 2,711 hits that are ~95% war-crimes sentencing
news; `№\d+` collides constantly with house/school/bus numbers; `ООО «...»` is
dominated by hospitals and payment kiosks. Every high-value term below needs a
**co-occurrence anchor** (a property-nexus word nearby) or an **instrument-type
anchor** (Указ/Постановление immediately before the №) to be usable. Patterns
are grouped by how much de-noising they need.

---

## Tier 1 — high signal, low noise (flag on presence alone)

| Signal | Pattern (Russian roots) | Why it works | Watch for |
|---|---|---|---|
| **Ownerless designation** | `бесхозя*` `бесхозн*` | The single cleanest seizure term; nearly every hit is the actual ownerless-property machine. | none material |
| **Transit-housing fund** | `маневренн* фонд*` / `маневренн* жил*` | Cracked the Nevsky case; names the *temporary-possession* mechanism dressed as resettlement. | distinguish "получил жильё маневренного фонда" (revocable) from permanent ордер |
| **Removal from register** | `снят* с учёт*` `обращ* в муниципальн* собственност` `изыма* с обращен*` | Endpoint of the seizure lifecycle. | — |
| **Forced entry** | `вскрыл` `с полицией` `взлома* дверь` `срезал* замок` `порядок вскрыт*` | Physical-seizure evidence; ties to GKO forced-entry procedure decrees. | — |
| **Sealing** | `опечат` `пломб` `запечат` | Eviction/sealing photos. | — |
| **Military/state builder** | `военн* строит*` `ВСК` `Военно-строит*` `Минобороны` `МО РФ` `Оборонспецстрой` | Surfaces the MoD-built showcase resettlement track that entirely bypasses the commercial ЕИСЖС registry. | "ВСК" also = a bank; require a build-context word |
| **Residential complex / new-build** | `ЖК «...»` `микрорайон «...»/[Capital]` `новостройк*` `жилой комплекс` | Named developments → cross-ref to ЕИСЖС + land-grant decrees. | many are just ads; the *name* is the payload |
| **Resident testimony (channel tags)** | `#нампишут` `#сообщают` `#крикдуши` `#отподписчика` `#жалоба` `#нужнапомощь` `#какбыть` | The channel's own label for user-submitted content — a far cleaner testimony filter than any keyword. | volume is high (~3K on Nash); pair with an address regex |
| **Power of attorney** | `доверенност*` | Diaspora owners acting remotely — directly probes the personal-appearance barrier (66-РЗ). | — |
| **Street renaming (de-Ukrainianization)** | `переименова* улиц/проспект` `аннулир* незаконн* судебн*` | Surfaced a lost collective lawsuit (Азовстальская→Тульский). | — |
| **Colloquial/activist seizure framing** | `отжат*` `отжали` | Confirmed on @ssaniaworld (14/3,202 msgs) — a resident/activist channel's own word for a seizure, cleaner than any official term because it's used exactly when someone believes a taking was wrongful. Good "this post is a grievance" flag on activist-type channels; less useful on state-aligned ones. | — |
| **Presidential-administration escalation** | `администраци* президента` | 97/3,202 hits on @ssaniaworld — residents citing "жалоба в Администрацию президента" as the top-of-chain complaint channel once local/republic prosecutors stall. A strong marker that a post describes an unresolved, escalated grievance. | generic news mentions of Putin's admin — check for a nearby жалоба/обращение word |
| **Official self-incrimination admission** | `техническ* ошибк*` | 24/3,202 hits — officials publicly walking back a decree/action as a "technical error" (e.g. ГКО №341's registration-freeze admission). A reusable anchor for finding *other* admitted-mistake episodes beyond the ones already known. | also used for genuinely trivial typos — read context |
| **Anti-abandonment evidence** | `(оплачива\|плати[лт]а?)\w*\s+(коммунал\*\|за (свет\|воду\|отопление))` | 11/3,202 hits — the single most useful phrase for rebutting the occupation courts' "собственник не проявляет интереса" abandonment reasoning: owner fled but kept paying utilities. Pair with `court_ctx`/`ownerless` for case-grade leads. | — |

## Tier 2 — needs a property-nexus anchor to be usable

Only flag these when a property word — `квартир* недвижимост* собственност*
имуществ* жиль* дом[а]? бесхоз* переименова* застройщик* компенсац*` — appears in
the same message. Without the anchor they are mostly off-topic.

| Signal | Pattern | Noise it drowns in without the anchor |
|---|---|---|
| **Court** | `суд` `судебн*` `иск` `апелляц*` `кассац*` | war-crimes sentencing of Azov/mercenaries (the overwhelming majority) |
| **Prosecutor** | `прокуратур*` | war-crimes press releases, unrelated criminal news reposts |
| **Fraud** | `мошенн*` `афер*` | generic scam-warning PSAs (phone scammers, etc.) |
| **Demolition** | `снос*` `снесл*` `снесут` `демонтаж*` | routine "демонтаж bus-stop / kiosk" municipal work |
| **Collapse / disrepair** | `обруш*` `обвал*` `трещин*` `треснул*` `аварийн*` | weather ("шторм обрушился"), global disaster news, geomagnetic-storm clickbait |
| **Passport / citizenship gate** | `паспорт*` `гражданств*` | driving-licence / SIM-card / school-enrolment procedure posts |
| **Compensation / certificate / mortgage** | `компенсац*` `сертификат*` `ипотек*` | maternity-capital, pension, general-benefit posts |
| **Notary** | `нотариус*` `нотариальн*` | — (low volume, mostly relevant when it appears) |
| **Citizenship-gate mechanism** | `спец* разрешени*` `разрешени* на регистрац/распоряжен` `коллегиальн* орган` | — |
| **Court reasoning boilerplate** | `не проявляет\w* (к жилью )?интерес\w*` | Low raw hit count (1/3,202 on ssaniaworld) but when it hits, it's the exact abandonment-doctrine phrase courts use to justify an ownerless ruling — worth keeping as a precision anchor for a case-grade court-quote find even at low recall. | — |
| **Convicted-fraudster-turned-contractor** | `осужден\w*.{0,40}лишени\w* свобод\w*` near a contract-award word | 0 hits so far but structurally the same shape as the Ташкалюк lead (msg 1228 ssaniaworld) — a named contractor with a prior Russian conviction winning DNR construction contracts; worth trying on new channels even at low yield given the stakeholder-network payoff when it hits. | — |

## Tier 3 — anchored extraction patterns (structured, not keyword)

- **Legal instrument citation** — `(Указ|Распоряжени*|Постановлени*|Решени*|
  Приказ*|Закон*|ГКО)[^.№]{0,40}?№\s*<number>`. The instrument-type word MUST
  precede the № within ~40 chars, or you match house numbers. Capitalise +
  normalise (`ГКО №175` == `Постановление №175` when the body says "ГКО").
  Cross-check every number against `docs/legal_mechanisms_review.md` before
  treating it as new.
- **Named legal entity** — `(ООО|АО|ЗАО|ОАО|ПАО|ГУП|МУП|ФГУП|ППК)\s*«<name>»`,
  then require a build-context word (`строит* застройщик восстанавл* возвод*
  подрядчик девелоп СЗ ремонт`) within ~60 chars of the match, or the results
  are dominated by hospitals (ГБУ «...»), banks (ПАО «Промсвязьбанк»), and
  payment kiosks (АО «ПТС» is literally "платёжный терминал", not a company).
- **Free-text address candidate** — street-type token (`ул\.? улиц* пр\.?
  просп* проспект* пер\.? переулок* б-р бульвар* пл\.? площад* наб\.? шоссе
  кв-л квартал*`) + 1–4 name words + house-number token. **Leads only** — never
  claim-grade without the normalize/address.py fuzzy pass (≥0.8) per CLAUDE.md.
  On a general channel most hits are shops/clinics/government offices, not
  seizures — the `#нампишут`-scoped subset is far higher-yield.

---

## Method notes (carry to the next channel)

- **Read the raw file, match the full address — never trust the tag/title.**
  Same lesson as `memory/lifecycle_classifier_unreliable_siege_damage.md`;
  negation ("не сносили") and reposted-national-news both defeat keyword tags.
- **Frequency-rank then eyeball the top of each bucket.** A pattern that returns
  2,000 hits isn't 2,000 leads; it's usually ~20 leads and 1,980 of one
  recurring noise class you can then exclude.
- **Forwards are an unmapped source graph.** ~20% of Nash messages are
  `fwd_from` other channels; a `fwd_from` frequency count surfaces which
  channels the occupation ecosystem treats as authoritative (this is how
  `@mizodnr`/`@donurcenter` were originally found — see
  `memory/new_telegram_channels_intel_2026-06-27.md`). Not yet run on Nash.
- **50%+ of a media channel is text-free captions on photos/videos.** Every
  keyword sweep is blind to that half by construction; pair any channel scan
  with the `scripts/225→226` flag-then-targeted-pull pattern to recover the
  visual evidence for high-value leads without hauling the whole channel.
- **Reliability caveat travels with the channel.** @mariupol_nash is an
  occupation-aligned general channel (broadcast, only 875/159K messages are
  replies) — treat its self-congratulatory reconstruction posts as *claims to
  be verified*, and its `#нампишут` resident submissions as *leads*, never as
  primary source, until independently corroborated. @ssaniaworld runs the
  opposite direction — occupation-loyalist but property-grievance-focused, so
  its flag rate is 3-4x higher (25.6% vs 7.4%) but needs a **city filter**:
  it reposts official DNR-wide bezkhoz notices, not just Mariupol (a 17-address
  hit cluster turned out to be Горловка) — always check the city token in a
  matched address before treating it as a Mariupol lead.
