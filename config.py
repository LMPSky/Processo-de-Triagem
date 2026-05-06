from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

_PROJECT_DIR = Path(__file__).resolve().parent
_CONFIG_DIR = _PROJECT_DIR / "configs"


@dataclass(frozen=True)
class SourceConfig:
    """Configuração de uma fonte de dados."""
    files: list[str]
    cnj_column: str
    file_type: str
    separator: str | None = None
    extra_match_columns: list[str] = field(default_factory=list)
    text_column: str | None = None
    prefer_sanitized: bool = False


@dataclass(frozen=True)
class AppConfig:
    input_dir: str = field(default_factory=lambda: os.getenv(
        "INPUT_DIR", str(_PROJECT_DIR / "input")
    ))
    output_dir: str = field(default_factory=lambda: os.getenv(
        "OUTPUT_DIR", str(_PROJECT_DIR / "output")
    ))

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
        files=["DW1.xlsx", "DW2.xlsx"],
        cnj_column="Processo",
        file_type="xlsx",
        text_column="Texto da Intimação 02",
    ))

    webjur: SourceConfig = field(default_factory=lambda: SourceConfig(
        files=["Webjur1.csv", "Webjur2.csv"],
        cnj_column="Número do Processo",
        file_type="csv",
        separator=";",
        text_column="Publicação",
        prefer_sanitized=True,
    ))

    modo_legalone_intimacoes: SourceConfig = field(default_factory=lambda: SourceConfig(
        files=["ModoLegalOneIntimacoes1.xlsx", "ModoLegalOneIntimacoes2.xlsx"],
        cnj_column="Número do Processo",
        file_type="xlsx",
        text_column="Publicação",
    ))

    def print_validation(self) -> bool:
        ok = True
        problems: list[str] = []

        input_path = Path(self.input_dir)
        if not input_path.exists():
            problems.append(f"Diretório de entrada não encontrado: '{self.input_dir}'")
            problems.append("  💡 Crie a pasta e coloque os arquivos de dados dentro dela.")
            ok = False

        if not _CONFIG_DIR.exists():
            problems.append(f"Pasta de configs não encontrada: '{_CONFIG_DIR}'")
            problems.append("  💡 Crie a pasta 'configs' na raiz do projeto.")
            ok = False
        else:
            required_config_files = [
                "trabalhista_categorias.json",
                "civel_priority_names.json",
                "civel_priority_clients.json",
                "civel_excludentes.json",
                "civel_numero_patterns.json",
                "civel_categorias.json",
                "civel_macrocategorias.json",
            ]
            for cfg in required_config_files:
                cfg_path = _CONFIG_DIR / cfg
                if not cfg_path.exists():
                    problems.append(f"Arquivo de configuração ausente: '{cfg_path.name}'")
                    ok = False

        if input_path.exists():
            all_sources = [
                ("Legal One", self.legalone),
                ("Painel", self.painel),
                ("DW", self.dw),
                ("WebJur", self.webjur),
                ("Modo LegalOne de Intimações", self.modo_legalone_intimacoes),
            ]
            for name, source in all_sources:
                missing = []
                for f in source.files:
                    path = input_path / f
                    if not path.exists():
                        missing.append(f)
                if missing:
                    problems.append(f"[{name}] Arquivos não encontrados: {', '.join(missing)}")

        if problems:
            print("⚠️  VALIDAÇÃO DE ENTRADA:\n")
            for p in problems:
                print(f"   {p}")
            print()

            if not input_path.exists() or not _CONFIG_DIR.exists():
                return False

            print("   ℹ️  Arquivos ausentes serão ignorados quando possível. Continuando...\n")
            return ok

        print("✅ Validação OK — inputs e configs encontrados.\n")
        return True


def get_config() -> AppConfig:
    return AppConfig()