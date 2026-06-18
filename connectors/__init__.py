"""Eurostat connectors for DataCivicLab."""

from connectors.tsv_normalize import (
    detect_dims,
    eurostat_url,
    normalize,
    normalize_stream,
    parse_value,
)

__all__ = [
    "detect_dims",
    "eurostat_url",
    "normalize",
    "normalize_stream",
    "parse_value",
]
