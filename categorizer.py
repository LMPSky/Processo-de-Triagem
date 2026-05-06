"""Classificador de processos por categoria — carrega termos do categories.json."""
from __future__ import annotations

import json
import re
from pathlib import Path
import pandas as pd

from text_utils import truncate_text_column, safe_filename
from logger import setup_logger

log = setup_logger(__name__)


# ══════════════════════════════════════════════════════════
# Carregar categorias do JSON externo
# ══════════════════════════════════════════════════════════

_CATEGORIES_PATH = Path(__file__).parent / "categories.json"


def _load_categories() -> dict[str, list[str]]:
    """Carrega o dicionário de categorias do arquivo JSON."""
    if not _CATEGORIES_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo de categorias não encontrado: {_CATEGORIES_PATH}\n"
            f"Crie o arquivo categories.json na raiz do projeto."
        )

    with open(_CATEGORIES_PATH, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("categories.json deve conter um objeto JSON (dicionário).")

    return data


CATEGORIES: dict[str, list[str]] = _load_categories()


# ══════════════════════════════════════════════════════════
# Padrões de busca
# ══════════════════════════════════════════════════════════

def _build_search_patterns() -> list[tuple[str, re.Pattern]]:
    """Constrói padrões de busca ordenados pelo comprimento do termo (mais longo primeiro)."""
    patterns: list[tuple[str, str, re.Pattern]] = []

    for category, terms in CATEGORIES.items():
        for term in terms:
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            patterns.append((category, term, pattern))

    patterns.sort(key=lambda x: len(x[1]), reverse=True)

    return [(cat, pat) for cat, _, pat in patterns]


_PATTERNS = _build_search_patterns()


def classify_text(text: str) -> str | None:
    """Classifica um texto retornando a categoria correspondente, ou None."""
    if not text or not text.strip():
        return None

    for category, pattern in _PATTERNS:
        if pattern.search(text):
            return category

    return None


# ══════════════════════════════════════════════════════════
# Classificação e exportação por categoria
# ══════════════════════════════════════════════════════════

def run_categorization(df: pd.DataFrame, output_dir: str, timestamp: str) -> pd.DataFrame:
    """Classifica linhas por categoria e exporta arquivos Excel por categoria."""
    log.info("═" * 60)
    log.info("📋 Classificando por categoria (texto)...")

    df = df.copy()
    df["_categoria"] = df["_texto"].apply(classify_text)

    classified = df[df["_categoria"].notna()].copy()
    not_classified = df[df["_categoria"].isna()].copy()

    total_classified = len(classified)
    total_not_classified = len(not_classified)

    log.info("✅ Classificados:     %d linhas", total_classified)
    log.info("⬚  Sem categoria:     %d linhas", total_not_classified)

    if total_classified == 0:
        log.info("ℹ️  Nenhum processo classificado por categoria.")
        return not_classified

    log.info("📊 Por categoria:")
    for cat, count in classified["_categoria"].value_counts().items():
        log.info("   • %s: %d", cat, count)

    out = Path(output_dir)
    categories_dir = out / "categorias"
    categories_dir.mkdir(parents=True, exist_ok=True)

    log.info("📁 Arquivos por categoria:")
    for category in sorted(classified["_categoria"].unique()):
        cat_df = classified[classified["_categoria"] == category].copy()

        file_path = categories_dir / f"{safe_filename(category)}_{timestamp}.xlsx"
        cols_to_export = [c for c in cat_df.columns if c != "_categoria"]

        cat_df_export = truncate_text_column(cat_df[cols_to_export])
        cat_df_export.to_excel(
            file_path, index=False, sheet_name=category[:31], engine="openpyxl"
        )
        log.info("   • %s  (%d linhas)", file_path.name, len(cat_df))

    all_classified_path = categories_dir / f"todos_classificados_{timestamp}.xlsx"
    classified_export = truncate_text_column(classified)
    classified_export.to_excel(
        all_classified_path, index=False, sheet_name="classificados", engine="openpyxl"
    )
    log.info("   • %s  (consolidado: %d linhas)", all_classified_path.name, total_classified)

    not_classified = not_classified.drop(columns=["_categoria"], errors="ignore")

    return not_classified