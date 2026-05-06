"""Pacote de classificadores."""

from .common import (
    load_json,
    sanitize_sheet_name,
    normalize_text,
    contains_any,
    safe_filename,
    truncate_text_column,
    rename_output_columns,
    word_frequency,
)
from .trabalhista import classify_trabalhista_text
from .civel import classify_civel_record, confidence_from_signals
from .normalizer import normalize_client_name, normalize_text as normalize_text_normalizer, resolve_client_group

__all__ = [
    "load_json",
    "sanitize_sheet_name",
    "normalize_text",
    "contains_any",
    "safe_filename",
    "truncate_text_column",
    "rename_output_columns",
    "word_frequency",
    "classify_trabalhista_text",
    "classify_civel_record",
    "confidence_from_signals",
    "normalize_client_name",
    "resolve_client_group",
]