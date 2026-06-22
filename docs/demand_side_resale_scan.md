# Demand-side resale scan — apartment-sale market (Mariupol)

*The market-facing end of the seizure pipeline: seized and rebuilt Mariupol flats
being **resold** into the Russian property market. This document covers the scan
built 2026-06-12 (scripts 49/50/51). Strategy context: `docs/reconceptualization_2026.md`
§3 (Tier-2 financial/beneficiary layer); mechanism mapping:
`docs/legal_mechanisms_review.md` rung [F]; demand-side overview: the
`[[demand_side_architecture]]` memory.*

---

## Why this is in scope

A live "**продаётся квартира в Мариуполе**" listing is a dated, public,
self-incriminating artifact: the occupier's own market openly trading dwellings in
occupied territory. It feeds both endpoints —

- **Rome Statute art. 8(2)(b)(viii)** (transfer of the occupier's own population) +
  **8(2)(a)(iv)/(b)(xiii)** (appropriation/disposal): the resale *is* the disposal of
  appropriated stock to incoming Russian buyers.
- **RD4U**: when a listing's address normalizes to a building already on our seizure
  spine, it corroborates that the documented-seized property has been disposed of —
  strengthening the dispossessed owner's A3.6 loss-of-access claim (they cannot
  prevent the sale of their own flat).

The sequence of dated snapshots is also a **demand-velocity series** — how fast
seized stock turns over — most informative across the 1 July 2026 deadline.

## Scope of this pass (deliberately narrow)

**Keep only: offers to SELL a residential APARTMENT in Mariupol.** Studios /
гостинки / малосемейки count as apartments. Everything else is classified and
written to an audit file but **not** emitted:

| Excluded | Why |
|---|---|
| Rentals (сдам / аренда / посуточно / руб/мес) | not a disposal of title |
| "Wanted" (куплю / сниму / ищу) | demand expressed, not stock offered |
| Rooms (комната / доля) | not a whole apartment |
| Houses / dachas / townhouses | not an apartment |
| Land plots (участок / соток) | not residential housing |
| Garages / parking / cellars | not residential housing |
| Commercial (офис / ПСН / склад / нежилое) | not residential |

## Sources

### A. Web marketplaces (script 49)
Sale-scoped Mariupol search entry points — Avito, ЦИАН, Домклик (Sberbank, ties to
the 2% mortgage), Мир Квартир, Аякс, Лига Квартир. Targets, pagination, and caps
live in `config.REALESTATE_TARGETS` / `REALESTATE_MAX_PAGES` / `REALESTATE_MAX_DETAIL`
— edit/extend there. Most are anti-bot and geoblocked → run from the VPS
(`config.PROXY`). The crawler captures search-result pages **and** follows into
per-listing detail pages; a captured block/404 page is itself a dated record.

### B. Telegram classified channels (script 50, MTProto via Telethon)
The most liquid, most current resale venue. `config.TELEGRAM_CHANNELS`, seeded with
the two user-named general channels (`@nemariupol`, `@mariupolskiy_uezd`) plus
dedicated Mariupol real-estate classifieds (`@Mariupol_Nedvizhimost`,
`@Mariupol_house`, `prodamMariupol`, `rieltorspivak`). These are mixed-content
(sale/rent/buy/commercial interleaved) — the scanner captures **every** message
verbatim; the apartment-sale filter is applied later (capture before parse). The
scan is **incremental** (only messages newer than the highest id already captured
per channel) and **resumable**.

## Pipeline (capture → parse, both re-runnable)

```
scripts/49_crawl_realestate_listings.py   ─┐  forensic raw capture
scripts/50_crawl_telegram_channels.py     ─┘  (SHA-256 + .meta.json custody)
        │   source_document: realestate_search_page / realestate_listing
        │                    telegram_channel_msg / telegram_channel_media
        ▼
scripts/51_parse_realestate_offers.py  (local, no network)
        │   classify (sale/rent/wanted × apartment/studio/room/house/land/garage/
        │             commercial), extract price/rooms/area/floor/address/contact,
        │             normalize address → building_key, flag on_seizure_spine
        ▼
   data/parsed/realestate_offers.jsonl     ← kept apartment-sale offers (deliverable)
   data/parsed/realestate_rejected.jsonl   ← filtered-out items + reason (audit)
   data/reports/realestate_offers_report.md
```

The parser reuses `normalize.address.classify_street` / `compute_building_key`, so
each listing's address produces the **same `building_key`** as the rest of the
project — a direct join to `address_registry.jsonl` and the seizure spine. Offers
whose key is on the spine carry `on_seizure_spine: true`: a flat being resold at an
address we have documented as seized / demolished / rebuilt.

## Running it (the user, from the VPS — Claude never runs crawlers)

```bash
pip install -e '.[telegram]'                       # telethon (one-time)
# Telegram creds already in .env (TELEGRAM_API_ID / _HASH / _PHONE_NUMBER)

python3 scripts/49_crawl_realestate_listings.py    # web marketplaces (all, or pass keys)
python3 scripts/50_crawl_telegram_channels.py      # channels (first run is interactive: login code)
python3 scripts/51_parse_realestate_offers.py      # local parse → offers + report
```

Re-run 49/50 periodically (the snapshot sequence is the demand-velocity series);
daily around 1 July 2026. 51 is offline and safe to iterate any time.

## Privacy (CLAUDE.md hard rule)

The protected class is the **lawful (dispossessed Ukrainian) owner** — never the
party reselling the flat. But a private seller may also be an innocent departing
resident, so the parser **isolates seller contact** (phone / `@username`) under each
offer's nested `contact` object and marks it `sensitive` for private individuals
(`is_agency: false`). Any shared export drops `contact` wholesale while the
public building-level fields (address, price, rooms, area) remain. Agencies /
realtors are commercial actors in official capacity → not minimized. `data/` is
gitignored in full, including the captured raw and the Telegram session token.

## Output schema (`realestate_offers.jsonl`, one row per offer)

`source` (telegram|web) · `source_type` · `source_sha256` · `source_url` ·
`captured_at` · `posted_date` · `venue` (channel/marketplace) · `offer_type` (sale)
· `property_class` (apartment|studio) · `is_studio` · `is_mariupol` · `price_rub` ·
`price_raw` · `rooms` · `area_total_m2` · `floor` · `floors` · `new_build` ·
`address_raw` · `street_clean` · `street_key` · `house` · **`building_key`** ·
**`on_seizure_spine`** · `text_excerpt` · `contact` {phones, usernames, is_agency,
sensitive}.

## Limits / next steps

- Marketplace detail-page field extraction is regex/JSON-LD/og-meta best-effort and
  robust to markup churn (we always hold the raw HTML to re-parse), but per-site
  selectors would raise recall — add them once real captures are in hand.
- Avito/ЦИАН JS challenges may yield block pages on some VPS IPs; captured blocks are
  recorded — rotate IP / add a headless fetch only if recall is poor.
- A DB loader (offers → `financial` / a `resale` corroboration signal joined on
  `building_key`) is the natural follow-up once a real capture exists, to fold spine
  hits into the corroboration report (script 33).
- `on_seizure_spine` hits are the highest-value rows — prioritize manual review of
  those (esp. `new_build: true`, i.e. demolish→rebuild resales like ЖК Черноморский).
