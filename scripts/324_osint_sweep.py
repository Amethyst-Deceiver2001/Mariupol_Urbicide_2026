#!/usr/bin/env python3
"""Per-address OSINT sweep — orchestrator (P0 build of
docs/address_osint_assistant_design.md).

Resolves one address to an AddressBundle (spine lookup, variant expansion),
then plans or runs the registered source modules. Default is --plan: print
what each source would do, its runner class (C=Claude-safe, U=user
terminal, V=VPS), and quota state — nothing fetches until --run.

Every network capture goes through forensics.capture_source() BEFORE any
parsing; per-source findings land in data/reports/osint/<slug>/<source>.json
for scripts/325 to assemble into the dossier.

Usage:
    # plan only (no side effects)
    PYTHONPATH=src .venv312/bin/python scripts/324_osint_sweep.py --pid 4837

    # run the purely-local sources (Claude-safe)
    PYTHONPATH=src .venv312/bin/python scripts/324_osint_sweep.py --pid 4837 --run --sources local

    # run everything in P0 (quick non-geoblocked fetches: pastvu, commons,
    # osm, eyesonrussia, wayback_tiles) — precedent scripts/159 & /200
    PYTHONPATH=src .venv312/bin/python scripts/324_osint_sweep.py --pid 4837 --run --sources all

    # single source, off-spine address
    PYTHONPATH=src .venv312/bin/python scripts/324_osint_sweep.py \
        --address "ул. Зелинского, 17а" --run --sources pastvu

Then:
    PYTHONPATH=src .venv312/bin/python scripts/325_osint_dossier.py --pid 4837
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mariupol_seizures import config, forensics  # noqa: E402
from mariupol_seizures.osint import ledger  # noqa: E402
from mariupol_seizures.osint.bundle import resolve_bundle  # noqa: E402
from mariupol_seizures.osint.sources import (  # noqa: E402
    CLAUDE_RUNNABLE, LOCAL_ONLY, REGISTRY)

log = logging.getLogger(__name__)


def outdir_for(slug: str) -> Path:
    d = config.DATA_DIR / "reports" / "osint" / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pid", type=int, help="spine property_id")
    ap.add_argument("--address", help="raw address (spine building_key match)")
    ap.add_argument("--lat", type=float, help="latitude for off-spine addresses")
    ap.add_argument("--lon", type=float, help="longitude for off-spine addresses")
    ap.add_argument("--sources", default="claude",
                    help="csv of source names, or a group: 'all' (every "
                         "registered source), 'claude' (RUN=C only — the "
                         "default, safe for Claude to execute), 'local' "
                         f"(no network). Available: {', '.join(REGISTRY)}")
    ap.add_argument("--run", action="store_true",
                    help="actually fetch (default: plan only)")
    ap.add_argument("--allow", default="C",
                    help="which run-classes may actually EXECUTE: csv of "
                         "C (Claude-safe), U (user terminal), V (VPS). "
                         "Default 'C'. A selected source whose class isn't "
                         "allowed is planned + its command emitted, not run "
                         "— this is what keeps Claude from executing "
                         "telethon/VPS/playwright jobs. On your own VPS pass "
                         "--allow C,U,V.")
    ap.add_argument("--radius", type=float, default=None,
                    help="search radius in metres, overriding each source's "
                         "own tuned default (pastvu 300m, commons 300m, "
                         "osm 40m, wayback 60m, eyesonrussia 150m) — leave "
                         "unset to use those per-source defaults")
    args = ap.parse_args()
    allowed_classes = {c.strip().upper() for c in args.allow.split(",") if c.strip()}

    bundle = resolve_bundle(pid=args.pid, address=args.address,
                            lat=args.lat, lon=args.lon)
    out = outdir_for(bundle.slug)
    (out / "bundle.json").write_text(
        json.dumps({**bundle.summary(),
                    "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat()},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    if args.sources == "all":
        selected = list(REGISTRY)
    elif args.sources == "local":
        selected = LOCAL_ONLY
    elif args.sources == "claude":
        selected = CLAUDE_RUNNABLE
    else:
        selected = [s.strip() for s in args.sources.split(",") if s.strip()]
        unknown = [s for s in selected if s not in REGISTRY]
        if unknown:
            log.error("unknown sources: %s (available: %s)",
                      unknown, ", ".join(REGISTRY))
            sys.exit(1)

    print(f"\n{'='*72}\nOSINT sweep — {bundle.slug}")
    print(f"  pid={bundle.pid}  {bundle.occupation_address or bundle.prewar_address}")
    print(f"  point=({bundle.lat:.6f}, {bundle.lon:.6f})  "
          f"variants={len(bundle.variants)}")
    print(f"  outdir={out}\n{'='*72}")

    con = forensics.open_state()
    ledger.ensure_schema(con)
    for src_name, budget in ledger.DAILY_BUDGETS.items():
        rem = ledger.remaining_today(con, src_name)
        print(f"  quota: {src_name} {rem}/{budget} remaining today")

    if not args.run:
        print("\n── plan (use --run to execute) ──")
        for name in selected:
            m = REGISTRY[name]
            state = "done" if (out / f"{name}.json").exists() else "pending"
            gate = "" if m.RUN in allowed_classes else "  [needs --allow " + m.RUN + "]"
            print(f"  [{m.RUN}] {name:18s} ({state}){gate} — {m.DESCRIPTION}")
            print(f"        would: {m.plan(bundle)}")
        con.close()
        return

    for name in selected:
        m = REGISTRY[name]
        if m.RUN not in allowed_classes:
            # not executed by this invocation — emit the ready-to-paste command
            # (this is the structural guard that keeps Claude from running
            #  telethon/VPS/playwright sources; the user runs them with --allow)
            pid_arg = f"--pid {bundle.pid}" if bundle.pid is not None \
                else f'--address "{bundle.occupation_address or bundle.prewar_address}"'
            print(f"\n⏭  {name} [{m.RUN}] — skipped (run class {m.RUN} not in "
                  f"--allow {','.join(sorted(allowed_classes))})")
            print(f"     run it yourself: PYTHONPATH=src .venv312/bin/python "
                  f"scripts/324_osint_sweep.py {pid_arg} --run "
                  f"--sources {name} --allow {m.RUN}")
            continue
        print(f"\n→ {name} [{m.RUN}] …")
        try:
            res = (m.fetch(bundle, con, args.radius) if args.radius is not None
                  else m.fetch(bundle, con))
        except Exception as e:  # noqa: BLE001
            log.exception("source %s crashed", name)
            res_json = {"source": name, "ok": False, "summary": f"crashed: {e}",
                        "n_findings": 0, "findings": [], "captured_sha256": []}
        else:
            res_json = res.to_json()
            print(f"  {res.summary}")
        res_json["generated_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat()
        (out / f"{name}.json").write_text(
            json.dumps(res_json, ensure_ascii=False, indent=2), encoding="utf-8")
    con.close()
    print(f"\ndone — results in {out}")
    print(f"Next: PYTHONPATH=src .venv312/bin/python scripts/325_osint_dossier.py "
          f"--slug {bundle.slug}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    main()
