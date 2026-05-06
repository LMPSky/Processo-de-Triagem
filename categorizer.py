"""Classificador de processos por categoria e termos de busca."""
from __future__ import annotations

import re
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
