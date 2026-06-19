"""MCP server for querying Eurostat data on GCS.

Tools: list available datasets, run SQL queries, resolve codelists.
Reads parquet from GCS via DuckDB + lab-connectors.

Usage:
    python eurostat-mcp/server.py
"""

from __future__ import annotations

from typing import Any

from lab_connectors.mcp import create_mcp_server, guard_timed

from client import (
    describe_dataset,
    facts,
    get_codelist,
    list_datasets,
    query,
)

SERVER = "eurostat"


def _list_response(result: Any) -> dict[str, Any]:
    """Wrap a list in dict with data/count for structured_output compatibility."""
    if isinstance(result, dict) and ("error" in result or "code" in result):
        return result
    return {"data": result, "count": len(result)}


mcp = create_mcp_server(
    name=SERVER,
    instructions=(
        "MCP connector for Eurostat regional data (NUTS2/NUTS3). "
        "Provides access to published datasets: GDP, GVA, crime, population. "
        "All data covers all EU countries and multiple years.\n\n"
        "Tools available:\n"
        "- eurostat_list_datasets — see what's available\n"
        "- eurostat_describe_dataset — inspect schema, years, and dimension values\n"
        "- eurostat_query — run SQL against a dataset (FROM data)\n"
        "- eurostat_get_codelist — resolve geo/unit/freq codes\n"
        "- eurostat_facts — auto-discovered facts about any or all datasets\n\n"
        "Example queries:\n"
        "- 'GDP pro-capite province italiane 2024'\n"
        "  → eurostat_query(slug='eurostat_gdp_nuts3', "
        "sql=\"SELECT geo, value FROM data WHERE geo LIKE 'IT%' AND unit='EUR_HAB' ORDER BY value DESC\")\n"
        "- 'Popolazione Italia 2024'\n"
        "  → eurostat_query(slug='eurostat_pop_nuts3', "
        "sql=\"SELECT SUM(value) FROM data WHERE geo LIKE 'IT%' AND unit='NR' AND sex='T' AND age='TOTAL'\")\n"
        "- 'Reati a Milano 2024'\n"
        "  → eurostat_query(slug='eurostat_crime_nuts3', "
        "sql=\"SELECT iccs, value FROM data WHERE geo='ITC4C' AND unit='NR'\")\n"
        "All data from Eurostat SDMX API. Quality flags preserved as 'flag' column."
    ),
)


@mcp.tool(
    description=(
        "List all available Eurostat datasets with metadata: "
        "slug, dataflow ID, theme, NUTS level, dimensions, description."
    ),
    structured_output=True,
)
def eurostat_list_datasets() -> dict[str, Any]:
    return _list_response(
        guard_timed(list_datasets, "eurostat_list_datasets", logger_name=SERVER)
    )


@mcp.tool(
    description=(
        "Get schema and dimension values for a Eurostat dataset. "
        "Returns columns with types, total row count, year range, "
        "and up to 20 distinct values per dimension (unit, geo, freq, ...). "
        "Each dimension reports total_count and a truncated flag — "
        "pass dimension_limit=0 for no cap. "
        "Use this before eurostat_query to discover available codes and filters."
    ),
    structured_output=True,
)
def eurostat_describe_dataset(slug: str) -> dict[str, Any]:
    return guard_timed(
        describe_dataset, "eurostat_describe_dataset", slug, logger_name=SERVER
    )


@mcp.tool(
    description=(
        "Run a SQL query on a specific Eurostat dataset. "
        "The parquet data is aliased as 'data'. Always use FROM data in your SQL. "
        "Examples:\n"
        "  SELECT year, geo, value FROM data WHERE geo LIKE 'IT%' LIMIT 10\n"
        "  SELECT geo, AVG(value) AS media FROM data WHERE unit='EUR_HAB' GROUP BY geo\n\n"
        "Available slugs: eurostat_gdp_nuts3, eurostat_gva_nuts3, "
        "eurostat_crime_nuts3, eurostat_pop_nuts3\n"
        "Use eurostat_list_datasets for full metadata."
    ),
    structured_output=True,
)
def eurostat_query(slug: str, sql: str, limit: int = 100) -> dict[str, Any]:
    return _list_response(
        guard_timed(query, "eurostat_query", slug, sql, limit, logger_name=SERVER)
    )


@mcp.tool(
    description=(
        "Resolve a Eurostat codelist by ID. "
        "Available codelists: freq (frequency codes), unit (units of measure), "
        "flag (SDMX quality flags), nuts_italy (Italian NUTS2 regions)."
    ),
    structured_output=True,
)
def eurostat_get_codelist(codelist_id: str) -> dict[str, Any]:
    return guard_timed(
        get_codelist, "eurostat_get_codelist", codelist_id, logger_name=SERVER
    )


@mcp.tool(
    description=(
        "Auto-discover facts about Eurostat datasets without writing SQL. "
        "Scans dataset schemas and optionally runs data queries to surface trends, "
        "rankings, and summary statistics. Use this to understand what a dataset "
        "contains before writing detailed queries.\n\n"
        "Parameters:\n"
        "- dataset: (optional) slug to inspect a single dataset. "
        "Omitting it scans all available datasets.\n"
        "- detail: if true, runs actual data queries for trends and rankings. "
        "Default false (schema-only).\n"
        "- limit: max results per fact (default 5).\n\n"
        "Example: eurostat_facts(dataset='eurostat_gdp_nuts3', detail=True)"
    ),
    structured_output=True,
)
def eurostat_facts(
    dataset: str | None = None,
    detail: bool = False,
    limit: int = 5,
) -> dict[str, Any]:
    return _list_response(
        guard_timed(facts, "eurostat_facts", dataset, detail, limit, logger_name=SERVER)
    )


if __name__ == "__main__":
    mcp.run()
