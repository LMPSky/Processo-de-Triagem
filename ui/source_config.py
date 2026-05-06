"""
Configuração central das fontes da aplicação.
"""
from __future__ import annotations

SOURCE_ORDER = [
    "legalone",
    "webjur",
    "dw",
    "painel",
    "modo_legalone_intimacoes",
]

SOURCES = {
    "legalone": {
        "label": "Base Legal One",
        "description": "Base principal obrigatória do Legal One.",
        "optional": False,
        "max_files": 1,
        "internal_filenames": ["Base LO.xlsx"],
    },
    "webjur": {
        "label": "WebJur",
        "description": "Base opcional do WebJur (até 2 arquivos).",
        "optional": True,
        "max_files": 2,
        "internal_filenames": ["Webjur1.csv", "Webjur2.csv"],
    },
    "dw": {
        "label": "DW",
        "description": "Base opcional do DW (até 2 arquivos).",
        "optional": True,
        "max_files": 2,
        "internal_filenames": ["DW1.xlsx", "DW2.xlsx"],
    },
    "painel": {
        "label": "Painel",
        "description": "Base opcional do Painel (até 2 arquivos).",
        "optional": True,
        "max_files": 2,
        "internal_filenames": ["Painel1.xlsx", "Painel2.xlsx"],
    },
    "modo_legalone_intimacoes": {
        "label": "Modo LegalOne de Intimações",
        "description": "Base opcional do Modo LegalOne de Intimações (até 2 arquivos).",
        "optional": True,
        "max_files": 2,
        "internal_filenames": [
            "ModoLegalOneIntimacoes1.xlsx",
            "ModoLegalOneIntimacoes2.xlsx",
        ],
    },
}


def get_source_config(source_key: str) -> dict:
    return SOURCES[source_key]


def get_source_label(source_key: str) -> str:
    return SOURCES[source_key]["label"]


def get_source_description(source_key: str) -> str:
    return SOURCES[source_key]["description"]


def is_source_optional(source_key: str) -> bool:
    return bool(SOURCES[source_key]["optional"])


def get_source_max_files(source_key: str) -> int:
    return int(SOURCES[source_key]["max_files"])


def get_source_internal_filenames(source_key: str) -> list[str]:
    return list(SOURCES[source_key]["internal_filenames"])


def build_empty_selected_files() -> dict[str, list[str]]:
    return {key: [] for key in SOURCE_ORDER}


def build_empty_skipped_sources() -> dict[str, bool]:
    return {key: False for key in SOURCE_ORDER}