.PHONY: help install test quote verify spend

PY := ./.venv/bin/python

help:
	@echo "make install   create the venv and install requirements"
	@echo "make test      run the offline suite"
	@echo "make quote     price the yield workflow, pay nothing"
	@echo "make verify    re-check every signal in the committed evidence"
	@echo "make spend     show what the caps have been charged"

install:
	python3 -m venv .venv
	$(PY) -m pip install -q -r requirements.txt

test:
	$(PY) -m pytest tests -q

quote:
	$(PY) cli.py quote yield --project aave-v3

verify:
	$(PY) scripts/verify_evidence.py evidence/listing-20261119T071626Z.json
	$(PY) scripts/verify_evidence.py evidence/stablecoin-20261119T071634Z.json
	$(PY) scripts/verify_evidence.py evidence/yield-20261119T071831Z.json

spend:
	$(PY) cli.py spend
