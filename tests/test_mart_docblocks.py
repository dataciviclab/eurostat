"""Coherence check: mart docblock titles must match their dataset theme.

Regression guard for the recurring copy-paste bug where a mart SQL file
is copied from another dataset and the docblock title keeps the source
dataset's subject (e.g. 'Soil erosion' title on the tourism mart).

Rule: the first meaningful word of each mart_sintesi/mart_trend docblock
title must appear in the dataset's registry.theme (case-insensitive),
and must NOT appear in another dataset's theme as a leading subject.
"""

from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent

# Keywords used as leading subject in docblock titles, mapped to the
# dataset slug that owns them. A docblock title may only use the keyword
# of ITS dataset (or a generic one like 'by country'/'region').
SUBJECT_OWNER: dict[str, str] = {
    "area": "eurostat-area-nuts3",
    "business demography": "eurostat-business-demography-nuts3",
    "crime": "eurostat-crime-nuts3",
    "demographic balance": "eurostat-demo-balance-nuts3",
    "births": "eurostat-demo-r-fagec3-nuts3",
    "deaths": "eurostat-demo-r-magec3-nuts3",
    "population density": "eurostat-pop-density-nuts3",
    "population": "eurostat-demo-r-pjangrp3-nuts3",
    "early school leavers": "eurostat-early-school-leavers-nuts2",
    "employment": "eurostat-emp-nuts3",
    "fertility": "eurostat-fertility-nuts3",
    "gdp": "eurostat-gdp-nuts3",
    "gross value added": "eurostat-gva-nuts3",
    "heating degree days": "eurostat-nrg-chddr2-a-nuts3",
    "monthly heating degree days": "eurostat-heating-degree-days-monthly-nuts3",
    "population structure": "eurostat-pop-structure-nuts3",
    "income inequality": "eurostat-income-inequality-nuts2",
    "poverty": "eurostat-poverty-risk-nuts2",
    "rd expenditure": "eurostat-rd-expenditure-nuts2",
    "physicians": "eurostat-physicians-nuts2",
    "hospital beds": "eurostat-hospital-beds-nuts2",
    "tourism nights": "eurostat-tourism-nuts3",
    "soil erosion": "eurostat-soil-erosion-nuts3",
    "labour productivity": "eurostat-labour-productivity-nuts3",
    "tran road": "eurostat-tran-sf-roadnu",
}


def _docblock_title(slug_dir: str, mart: str) -> str:
    """First line of the mart docblock, minus the '-- mart_x — ' prefix."""
    f = REPO / "datasets" / slug_dir / "sql" / f"mart_{mart}.sql"
    if not f.exists():
        return ""
    line = f.read_text(encoding="utf-8").splitlines()[0]
    return line.split("—", 1)[-1].strip() if "—" in line else ""


@pytest.mark.contract
@pytest.mark.parametrize("mart", ["sintesi", "trend"])
def test_docblock_title_matches_owner(mart):
    """Each mart title's subject belongs to its own dataset, not another's."""
    for slug_dir in sorted((REPO / "datasets").iterdir()):
        if not (slug_dir / "dataset.yml").exists():
            continue
        title = _docblock_title(slug_dir.name, mart)
        if not title:
            continue
        lower = title.lower()
        # Match the LONGEST subject keyword present (most specific wins),
        # e.g. 'population density' beats 'population'.
        matched = sorted(
            (subj for subj in SUBJECT_OWNER if subj in lower),
            key=len,
            reverse=True,
        )
        if not matched:
            continue  # generic title (e.g. 'by country and ranking')
        owner = SUBJECT_OWNER[matched[0]]
        own_slug = slug_dir.name
        assert owner == own_slug, (
            f"mart_{mart} of {own_slug} has title referencing "
            f"{owner}'s subject: '{title}'"
        )
