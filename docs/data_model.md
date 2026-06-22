# Data model

The spine is `property`. Every source attaches to a property as one or more
`seizure_event` rows (the lifecycle), optionally a `court_case`, plus `actor`,
`financial`, and `corroboration`. `source_document` is the chain-of-custody record
for every raw artifact; `toponym` joins pre-war Ukrainian ↔ occupation addresses.

```
property ──┬─ owner            (minimized / sensitive)
           ├─ seizure_event ──< event_actor >── actor
           ├─ court_case
           ├─ financial
           └─ corroboration
toponym (prewar ↔ occupation address)      source_document (custody)
```

Lifecycle stages (`seizure_event.stage`): utility_cutoff → notice → inspection →
ownerless_designation → court_petition → court_transfer → entered_force →
reallocation → resale.

Every linkage row carries a `confidence` (0..1). Claim-grade rows: confidence ≥
0.8 and ≥ 2 independent sources. `property.rd4u_category` records which Register
of Damage claim categories the property's evidence supports, as a
comma-separated set (e.g. `A3.1,A3.6`) — a property can support more than one
claim. Computed by `scripts/36_categorize_rd4u.py`; see
`docs/legal_mechanisms_review.md` for the category definitions and the
stage→category mapping.

Full DDL: `db/schema.sql`.
