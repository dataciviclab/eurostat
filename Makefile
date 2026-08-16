# CLI toolkit del Lab. La memoria DuckDB è controllata da safe_connect
# (lab-connectors) via env DUCKDB_MEMORY_LIMIT (default 2GB); nei runner CI
# con RAM ridotta il pipeline imposta limiti conservativi.
TOOLKIT = toolkit

# --- Dataset del repo -------------------------------------------------------
# Convenzione (ADR-001, modello multi-dataset):
#   datasets/ = dataset principali (una dir per dataset, ognuna con dataset.yml)
# Ogni dir è un "dataset" a sé: il comando toolkit riceve il --config.

DATASETS := $(shell find datasets -name dataset.yml 2>/dev/null | sort)

# --- Codelists (pre-requisito: i clean.sql fanno join con codelists/geo.csv) --

.PHONY: codelists
codelists:
	python scripts/update_codelists.py

# --- Run --------------------------------------------------------------------

.PHONY: run
run:
	$(TOOLKIT) run --batch batch.txt

.PHONY: run-all
run-all: codelists
	@find datasets -name dataset.yml | sort > batch.txt; \
	$(TOOLKIT) run --batch batch.txt

# --- Validazione config ------------------------------------------------------

.PHONY: check
check:
	@for f in $(DATASETS); do \
		echo "→ $$f"; \
		$(TOOLKIT) run preflight --config "$$f" > /dev/null 2>&1 || exit 1; \
	done
	@echo "✅ All configs valid"

# --- Pulizia -----------------------------------------------------------------

.PHONY: clean
clean:
	rm -rf out/data/_runs out/data/probe out/data/raw out/data/clean out/data/mart out/data/cross .tmp/

.PHONY: clean-runs
clean-runs:
	rm -rf out/data/_runs/

# --- Registry (artifact catalogo — dry-run di default) -----------------------

.PHONY: registry registry-write
registry:
	$(TOOLKIT) registry build --prefix eurostat --flat

registry-write:
	$(TOOLKIT) registry build --prefix eurostat --flat --write

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:' Makefile | sort
