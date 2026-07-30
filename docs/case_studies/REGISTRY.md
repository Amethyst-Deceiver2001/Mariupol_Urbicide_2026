# Case-study registry

Single source of truth for case-study identity. Every case study — draft or
exhibited — has exactly one row here. Rules:

1. **Identity = accession code**, `MUP-CS-NNN`, assigned once when the case
   study is first registered, in accession order. The order is an accident of
   production and carries **no meaning** — codes are never reused, renumbered,
   or read as ranking. Cite the code in legal-facing contexts; it survives
   retitles and re-publication.
2. **Files and URLs = subject slugs** (anchor address or mechanism), never
   ordinals. Published filenames are immutable — the Roman numerals fossilized
   in `case-study-II/III/IV-*.html` stay in the URLs because the site is live
   and links rot, but no new file ever gets one.
3. **Display chrome carries no ordinal.** Kicker lines read
   `Case study · <modality label>` (EN) / `Дело · <метка модели>` (RU).
   Modality codes (below) are semantic and stable; they may appear in display
   («Модель 2») because they classify, not enumerate.
4. **Prose cross-references use short descriptive names** ("the Stroiteley
   case study", «дело Нахимова, 82»), linked, never "Case Study IV".
5. New case studies: take the next code, add the row here **before** writing
   the exhibit, put the code in the exhibit's provenance block.

## Modality vocabulary

M1–M3 match the "Modality 1/2/3" labels already printed in the master dossier.
Cross-cutting studies document the machine itself rather than one seizure
modality.

| Code | EN label | RU label |
|---|---|---|
| M1 | Demolition & address-laundering (demolish → rebuild → resell) | Снос и смена адреса |
| M2 | Flat-by-flat registry sweep → resale | Поквартирное включение в реестр «бесхозяйного» → продажа |
| M3 | Block-level demolition, land to a single developer | Снос целого квартала, земля — одному застройщику |
| M4 | Restoration without restitution | Восстановление без реституции |
| M5 | Registry enforced in the physical world (sealing / eviction) | Реестр, приведённый в исполнение |
| M6 | Land grant / no-tender lease | Передача земли без торгов |
| M7 | Showcase / military reconstruction (ордер, not title) | Витринная застройка: ордер вместо титула |
| X | Cross-cutting (court conveyor, resistance, victim overlays) | Сквозные темы |
| M10 | Registry sweep → transfer into federal ownership (a named military/security unit, or the federal treasury) | Реестр «бесхозяйного» → передача в федеральную собственность (войсковой части / силовому ведомству либо в казну) |
| M11 | Demolish-and-abandon (land held empty/reserved, no redevelopment) | Снос и заброшенность (земля не застроена, зарезервирована) |

Reserved for proposed work: **M8** paper remedy / reclaim-into-the-void
(Металлургов 25), **M9** non-residential / livelihood seizures.

## Register

| Code | Slug / anchor | Modality | Research doc | EN exhibit | RU exhibit |
|---|---|---|---|---|---|
| MUP-CS-001 | Нахимова 82 → Черноморский 1Б | M1 | [nakhimova_82_chernomorsky_1b.md](nakhimova_82_chernomorsky_1b.md) | [nakhimova-82-exhibit.html](../exhibits/nakhimova-82-exhibit.html) | [-ru](../exhibits/nakhimova-82-exhibit-ru.html) |
| MUP-CS-002 | Ленина (Мира) 104/106/108/110 | M4 | [lenina_104_106_108_110_restoration_without_restitution.md](lenina_104_106_108_110_restoration_without_restitution.md) | [lenina-104-106-108-110-exhibit.html](../exhibits/lenina-104-106-108-110-exhibit.html) | [-ru](../exhibits/lenina-104-106-108-110-exhibit-ru.html) |
| MUP-CS-003 | Ленина (Мира) 133, кв. 19 — опечатанная дверь | M5 | [lenina133_apt19_sealing.md](lenina133_apt19_sealing.md) | [lenina133-apt19-exhibit.html](../exhibits/lenina133-apt19-exhibit.html) | [-ru](../exhibits/lenina133-apt19-exhibit-ru.html) |
| MUP-CS-004 | Registry sweep → live resale (Строителей 108 / Ленина 100…) | M2 | [mass_registry_to_resale.md](mass_registry_to_resale.md) | [case-study-II-registry-resale.html](../exhibits/case-study-II-registry-resale.html) | [-ru](../exhibits/case-study-II-registry-resale-ru.html) |
| MUP-CS-005 | Троянда-М — Металлургов 47, жители против сноса | X (court resistance) | [troianda_m_demolition_challenge.md](troianda_m_demolition_challenge.md) | [case-study-troianda-metallurgov.html](../exhibits/case-study-troianda-metallurgov.html) | [-ru](../exhibits/case-study-troianda-metallurgov-ru.html) |
| MUP-CS-006 | Проспект Строителей — «Резиденция» on a burial ground | M3 | *(exhibit-built; victim overlay in [death_sites_new_construction.md](death_sites_new_construction.md))* | [case-study-III-stroiteley.html](../exhibits/case-study-III-stroiteley.html) | [-ru](../exhibits/case-study-III-stroiteley-ru.html) |
| MUP-CS-007 | The court docket — 33 judges, 2,694 rulings, no address | X (court conveyor) | *(built from `docs/dnr_district_first_instance_2026-06.md`)* | [case-study-IV-court-docket.html](../exhibits/case-study-IV-court-docket.html) | [-ru](../exhibits/case-study-IV-court-docket-ru.html) |
| MUP-CS-008 | МКР «Невский» — ордер, не титул | M7 | [nevsky_microdistrict_ordena_not_title.md](nevsky_microdistrict_ordena_not_title.md) | — | — |
| MUP-CS-009 | ЖСК «Бригантина» → СЗ «ГСА Девелопмент» | M6 | [brigantina_zhsk_land_lease.md](brigantina_zhsk_land_lease.md) | — | — |
| MUP-CS-010 | Death sites, ad-hoc graves & collapse-entombment × new construction | X (victim overlay) | [death_sites_new_construction.md](death_sites_new_construction.md) | [death-sites-new-construction-exhibit.html](../exhibits/death-sites-new-construction-exhibit.html) | [-ru](../exhibits/death-sites-new-construction-exhibit-ru.html) |
| MUP-CS-011 | Чёрноморская 18 / Ленина 101 → в/ч 1297 (FSB); + bulk apartments → federal treasury | M10 | [chernomorskaya18_fsb_transfer.md](chernomorskaya18_fsb_transfer.md) | — | — |
| MUP-CS-012 | Levoberezhny quarter — Ломизова / 50 лет Октября (Меотиды) / Азовстальская / Комсомольский (Морской) — demolished, never rebuilt | M11 (a 2025 federal highway-planning decree reserving the site for a road interchange is the only documented reason on file for the continued emptiness — see the case-study doc's "№186-од" section) | [levoberezhny_quarter_demolish_and_abandon.md](levoberezhny_quarter_demolish_and_abandon.md) | [levoberezhny-quarter-exhibit.html](../exhibits/levoberezhny-quarter-exhibit.html) | — |

Retired display labels (for anyone holding an old citation): "Case Study II"
= MUP-CS-004, "Case Study III" = MUP-CS-006, "Case Study IV" = MUP-CS-007,
"Case Study V" = MUP-CS-003, "Exhibit B" was ambiguously used for both
MUP-CS-004 and MUP-CS-003, "Exhibit C" / «Дело C» = MUP-CS-002, and the
master dossier's "Case study I" = MUP-CS-001.
