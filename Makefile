.PHONY: help install test verify demo

PY := ./.venv/bin/python

help:
	@echo "make install   create the venv and install requirements"
	@echo "make test      run the offline suite"
	@echo "make claims    the seven claims and the intents behind them"
	@echo "make verify    verify the committed bundle without trusting it"
	@echo "make demo      run the api and open the demo page"

install:
	python3 -m venv .venv
	$(PY) -m pip install -q -r requirements.txt

test:
	$(PY) -m pytest tests -q

claims:
	$(PY) -m colony.cli claims

verify:
	$(PY) scripts/verify_bundle.py evidence/colony-maersk-20261121.json

demo:
	$(PY) -m colony.api --port 8088
