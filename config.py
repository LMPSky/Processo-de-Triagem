from __future__ import annotations

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class SourceConfig:
    """Configuração de uma fonte de dados."""
    files: list[str]
    cnj_column: str
    file_type: str
    separator: str | None = None
    extra_match_columns: list[str] = field(default_factory=list)
    text_column: str | None = None

@dataclass(frozen=True)
class AppConfig:
    input_dir: str = field(default_factory=lambda: os.getenv("INPUT_DIR", "input"))
    output_dir: str = field(default_factory=lambda: os.getenv("OUTPUT_DIR", "output"))

    legalone: SourceConfig = field(default_factory=lambda: SourceConfig(
        files=["Base LO.xlsx"],
        cnj_column="Número de CNJ",
        file_type="xlsx",
        extra_match_columns=["Outro número", "Número antigo"],
    ))

    painel: SourceConfig = field(default_factory=lambda: SourceConfig(
        files=["Painel1.xlsx", "Painel2.xlsx"],
        cnj_column="PROCESSO",
        file_type="xlsx",
        text_column="CLASSE JUDICIAL",
    ))

    dw: SourceConfig = field(default_factory=lambda: SourceConfig(
        files=["DW.xlsx", "DW2.xlsx"],
        cnj_column="Processo",
        file_type="xlsx",
        text_column="Texto da Intimação 02",
    ))

    webjur: SourceConfig = field(default_factory=lambda: SourceConfig(
        files=["Webjur1.csv", "Webjur2.csv"],
        cnj_column="Codigo",
        file_type="csv",
        separator=";",
        text_column="Juizo",
    ))

def get_config() -> AppConfig:
    return AppConfig()