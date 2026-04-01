"""Classificador de processos por categoria e termos de busca."""
from __future__ import annotations

import re
from pathlib import Path
from datetime import datetime
import pandas as pd


# ══════════════════════════════════════════════════════════
# Categorias e termos de busca
# ══════════════════════════════════════════════════════════

CATEGORIES: dict[str, list[str]] = {
    "Ação de Cumprimento": [
        "Ação de Cumprimento",
        "Acao de Cumprimento",
        "A Cum",
        "ACum",
        "ACIA",
    ],
    "Carta Precatória": [
        "Carta Precatória",
        "Carta Precatoria",
        "Carta Precatória Cível",
        "Carta Precatoria Civel",
        "CartPrec",
        "CartPrecCiv",
        "CPre",
    ],
    "Conflito de Competência": [
        "CCCiv",
        "Conflito de Competência",
        "Conflito de Competencia",
    ],
    "Cumprimento de Sentença": [
        "Cumprimento de Sentença",
        "Cumprimento de Sentenca",
        "Cumprimento de sentenç",
        "CUMPRIMENTO DE SENTENÇA",
        "Cumprimento de Sentença (Vara Cível)",
        "Cumprimento de Sentença contra a Fazenda Pública",
        "Cumprimento Provisório de Sentença",
        "Cumprimento Provisorio de Sentenca",
        "CUMPRIMENTO PROVISÓRIO DE SENTENÇA",
        "CumPrSe",
        "CumSen",
        "CumSenFaz",
    ],
    "Décio Freire": [
        "Décio Flávio Gonçalves Torres Freire",
        "Decio Flavio Gonçalves Torres Freire",
        "Decio Flavio Goncalves Torres Freire",
        "Décio Freire",
        "Decio Freire",
    ],
    "Execução de Certidão de Crédito Judicial": [
        "ExCCj",
        "Execução de Certidão de Crédito Judicial",
        "Execucao de Certidao de Credito Judicial",
    ],
    "Execução de Título Extrajudicial": [
        "Execução de Título Extrajudicial",
        "Execução de Título Extrajudicia",
        "Execucao de Titulo Extrajudicial",
        "ExTiEx",
    ],
    "Execução Fiscal": [
        "Execução Fiscal",
        "EXECUÇÃO FISCAL",
        "Execucao Fiscal",
        "Execução Fiscal (Vara Execução)",
        "ExFis",
        "Cautelar Fiscal",
    ],
    "Execução Provisória": [
        "Execução Provisória",
        "Execucao Provisoria",
        "ExProvAS",
    ],
    "Mandado de Segurança": [
        "Mandado de Segurança",
        "Mandado de Seguranca",
        "MANDADO DE SEGURANÇA",
        "Mandado de Segurança Cível",
        "MANDADO DE SEGURANÇA CÍVEL",
        "Mandado de Seguranca Cível",
        "Mandado de Seguranca Civel",
        "Mandado de Segurança (Plenário)",
        "Mandado de Segurança (Vara Cível)",
        "MSCiv",
        "MSCi",
    ],
    "Recurso de Julgamento Parcial": [
        "Recurso de Julgamento Parcial",
        "Ofício Circular AR",
        "Oficio Circular AR",
        "tema 1.046",
        "tema 1046",
    ],
    "TRT 14 - Contrato GPA": [
        "Compre bem",
        "Comprebem",
        "SCB DISTR",
        "SCB Distribuição e Comércio Varejista de Alimentos Ltda",
        "SCB Distribuição e Comercio Varejista de Alimentos Ltda",
        "SCB DISTRIBUIÇÃO E COMÉRCIO VAREJISTA DE ALIMENTOS LTDA",
        "SCB DISTRIBUICAO E COMERCIO VAREJISTA DE ALIMENTOS LTDA",
        "Supermercado Compre bem",
        "Supermercado Comprebem",
    ],
    "Tutela Cautelar Antecedente": [
        "Tutela Cautelar Antecedente",
        "TutCautAnt",
        "Tutela Antecipada Antecedente",
        "TUTELA ANTECIPADA ANTECEDENTE",
    ],
}


# Limite de caracteres para a coluna _texto no Excel
_MAX_TEXT_LENGTH = 500


def _build_search_patterns() -> list[tuple[str, re.Pattern]]:
    patterns: list[tuple[str, str, re.Pattern]] = []

    for category, terms in CATEGORIES.items():
        for term in terms:
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            patterns.append((category, term, pattern))

    patterns.sort(key=lambda x: len(x[1]), reverse=True)

    return [(cat, pat) for cat, _, pat in patterns]


_PATTERNS = _build_search_patterns()


def classify_text(text: str) -> str | None:
    if not text or not text.strip():
        return None

    for category, pattern in _PATTERNS:
        if pattern.search(text):
            return category

    return None


def _truncate_text_column(df: pd.DataFrame) -> pd.DataFrame:
    """Trunca a coluna _texto para caber no Excel (32767 max, mas cortamos em 500 para legibilidade)."""
    df = df.copy()
    if "_texto" in df.columns:
        df["_texto"] = df["_texto"].apply(
            lambda x: (x[:_MAX_TEXT_LENGTH] + "... [TRUNCADO]") if isinstance(x, str) and len(x) > _MAX_TEXT_LENGTH else x
        )
    return df


def run_categorization(df: pd.DataFrame, output_dir: str, timestamp: str) -> pd.DataFrame:
    print("\n" + "═" * 60)
    print("📋 Classificando por categoria (texto)...")

    df = df.copy()
    df["_categoria"] = df["_texto"].apply(classify_text)

    classified = df[df["_categoria"].notna()].copy()
    not_classified = df[df["_categoria"].isna()].copy()

    total_classified = len(classified)
    total_not_classified = len(not_classified)

    print(f"   ✅ Classificados:     {total_classified} linhas")
    print(f"   ⬚  Sem categoria:     {total_not_classified} linhas")

    if total_classified == 0:
        print(f"   ℹ️  Nenhum processo classificado por categoria.")
        return not_classified

    print(f"\n   📊 Por categoria:")
    category_counts = classified["_categoria"].value_counts()
    for cat, count in category_counts.items():
        print(f"      • {cat}: {count}")

    out = Path(output_dir)
    categories_dir = out / "categorias"
    categories_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n   📁 Arquivos por categoria:")
    for category in sorted(classified["_categoria"].unique()):
        cat_df = classified[classified["_categoria"] == category].copy()

        safe_name = (
            category
            .lower()
            .replace(" ", "_")
            .replace("ã", "a")
            .replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
            .replace("ç", "c")
            .replace("-", "_")
        )
        safe_name = re.sub(r"[^\w]", "", safe_name)

        file_path = categories_dir / f"{safe_name}_{timestamp}.xlsx"
        cols_to_export = [c for c in cat_df.columns if c != "_categoria"]

        # Trunca texto antes de exportar
        cat_df_export = _truncate_text_column(cat_df[cols_to_export])
        cat_df_export.to_excel(
            file_path, index=False, sheet_name=category[:31], engine="openpyxl"
        )
        print(f"      • {file_path.name}  ({len(cat_df)} linhas)")

    all_classified_path = categories_dir / f"todos_classificados_{timestamp}.xlsx"
    classified_export = _truncate_text_column(classified)
    classified_export.to_excel(
        all_classified_path, index=False, sheet_name="classificados", engine="openpyxl"
    )
    print(f"      • {all_classified_path.name}  (consolidado: {total_classified} linhas)")

    not_classified = not_classified.drop(columns=["_categoria"], errors="ignore")

    return not_classified
