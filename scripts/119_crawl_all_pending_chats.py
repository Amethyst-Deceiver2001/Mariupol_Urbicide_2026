#!/usr/bin/env python3
"""Run all pending building-chat crawls sequentially, in one process.

Combines scripts 105-118 — the last batch of Telegram building/area chats
identified this session, none yet captured. Each underlying script is
unchanged; this just loads each module's run() function (via importlib,
since the filenames start with digits and can't be `import`ed normally)
and calls them one after another, so you don't have to babysit fourteen
separate invocations.

Failures are isolated: if one chat is inaccessible (e.g. a pending join
request not yet approved, per script 111's nahimova_lavitskogo handling)
or errors out, that's logged and the run moves on to the next chat rather
than stopping the whole batch.

Chats run, in order:
  105  invite_jWgnL94OdmYmMy        (unresolved invite)
  106  mariupol_komsomolets         (scope unconfirmed — public)
  107  invite_ucWZaRSL1Gk1NjRi      (unresolved invite)
  108  metalurgov89_91              (pid=4550/4551, demolished, capped 2024-05-24)
  109  invite_rBQJ4lUIDZc5YTUy      (unresolved invite, capped 2022-12-31)
  110  invite_ZPLyCLn2RItmNWMy      (unresolved invite)
  111  nahimova_lavitskogo          (Нахимова/Лавицкого area, public)
  112  invite_DCg6OyadlYYyYjc6      (unresolved invite, capped 2022-12-31)
  113  invite_gxgwA2by644ZTAy       (unresolved invite, capped 2023-12-31)
  114  metallgov                    (пр. Металлургов area, public)
  115  budivelnikiv                 (пр. Строителей, Ukrainian name, public)
  116  shevchenko74mariupol         (pid=4399, demolished, public)
  117  invite_SWCkzbFpPJBkODBi      (Шевченко/Котляревского area, invite)
  118  invite_Xr0WjIQ8rOU2NmYy      (pid=6258, Азовстальская 27, demolished, invite)

Claude must never run this. Run from project root:
    .venv312/bin/python scripts/119_crawl_all_pending_chats.py

Re-runs are incremental (each underlying script dedupes against what's
already in the forensics store).
"""
import importlib.util
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

log = logging.getLogger(__name__)

SCRIPTS = [
    "105_crawl_invite_jWgnL94OdmYmMy.py",
    "106_crawl_mariupol_komsomolets_chat.py",
    "107_crawl_invite_ucWZaRSL1Gk1NjRi.py",
    "108_crawl_metalurgov89_91_chat.py",
    "109_crawl_invite_rBQJ4lUIDZc5YTUy.py",
    "110_crawl_invite_ZPLyCLn2RItmNWMy.py",
    "111_crawl_nahimova_lavitskogo_chat.py",
    "112_crawl_invite_DCg6OyadlYYyYjc6.py",
    "113_crawl_invite_gxgwA2by644ZTAy.py",
    "114_crawl_metallgov_chat.py",
    "115_crawl_budivelnikiv_chat.py",
    "116_crawl_shevchenko74_chat.py",
    "117_crawl_invite_SWCkzbFpPJBkODBi.py",
    "118_crawl_invite_Xr0WjIQ8rOU2NmYy.py",
]


def _load_module(script_name: str):
    path = ROOT / "scripts" / script_name
    mod_name = f"_pending_crawl_{path.stem}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    results = {}
    for i, script_name in enumerate(SCRIPTS, 1):
        print(f"\n{'='*72}")
        print(f"[{i}/{len(SCRIPTS)}] {script_name}")
        print(f"{'='*72}")
        try:
            module = _load_module(script_name)
            module.run()
            results[script_name] = "ok"
        except Exception:
            log.exception("crawl failed: %s", script_name)
            results[script_name] = "FAILED"

    print(f"\n{'='*72}")
    print("ALL PENDING CHATS — RUN SUMMARY")
    print(f"{'='*72}")
    for script_name, status in results.items():
        print(f"  {status:8s}  {script_name}")
    n_fail = sum(1 for s in results.values() if s == "FAILED")
    print(f"\n  {len(results) - n_fail}/{len(results)} completed without raising; "
          f"{n_fail} failed (see log above) or were blocked (e.g. pending join "
          f"approval, per-script logs note this explicitly).")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
