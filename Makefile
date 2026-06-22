.PHONY: setup crawl parse load verify test
setup:
	python -m venv .venv && . .venv/bin/activate && pip install -e ".[geo,dev]"
crawl:   ## run from VPS only
	PYTHONPATH=src python scripts/01_crawl.py
parse:
	PYTHONPATH=src python scripts/02_parse.py
load:
	PYTHONPATH=src python scripts/03_load.py
verify:  ## re-hash raw store against the custody log
	PYTHONPATH=src python -c "from mariupol_seizures import forensics as f; c=f.open_state(); bad=f.verify_store(c); print('OK' if not bad else f'MISMATCH: {bad}')"
test:
	PYTHONPATH=src pytest -q
