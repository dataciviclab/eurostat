## Type

- [ ] Root fix (removes the cause of a bug)
- [ ] Contract alignment (aligns behavior across components)
- [ ] New dataset (adds a Eurostat dataflow to the registry)
- [ ] Infrastructure (CI, GCS, MCP, docs)
- [ ] Chore (cleanup, test, refactor)

## Problem

Describe the problem or motivation. What was broken or missing?

## Solution

What changed and why. One paragraph is enough.

## Test plan

- [ ] `pytest tests/ -v` passes
- [ ] `toolkit run full --config datasets/{slug}/dataset.yml --years 2024` passes (for new/fixed datasets)

## Downstream impact

- [ ] Parquet schema changed (columns renamed or removed)
- [ ] GCS paths changed
- [ ] MCP tools affected
- [ ] None — internal refactor only

If schema changed, list old vs new columns:

## Closes

If this PR addresses an issue, add `Closes #ISSUE_NUMBER` here.

## Checklist

- [ ] `ruff check connectors/ tests/` passes
- [ ] `docs/dataset-registry.md` updated if adding a dataset
- [ ] `docs/contributing.md` template still accurate
