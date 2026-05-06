"""Utilitários de texto compartilhados entre módulos."""
from __future__ import annotations

import re
import pandas as pd

def normaliza_cnj(cnj):
    """
    Recebe string (ou número) de CNJ (qualquer formato) e retorna SEMPRE
    o formato padronizado CNJ (ex: 0700083-59.2019.8.01.0016)
    ou uma string vazia se não bate 20 dígitos.
    """
    if not cnj or pd.isnull(cnj):
        return ""
    c = re.sub(r'\D', '', str(cnj))
    if len(c) == 20:
        return f"{c[:7]}-{c[7:9]}.{c[9:13]}.{c[13:14]}.{c[14:16]}"
    return ""

# Limite de caracteres para a coluna _texto no Excel
MAX_TEXT_LENGTH = 500

def truncate_text_column(df: pd.DataFrame) -> pd.DataFrame:
    """Trunca a coluna _texto para caber no Excel (32767 max, mas cortamos em 500 para legibilidade)."""
    df = df.copy()
    if "_texto" in df.columns:
        df["_texto"] = df["_texto"].apply(
            lambda x: (x[:MAX_TEXT_LENGTH] + "... [TRUNCADO]")
            if isinstance(x, str) and len(x) > MAX_TEXT_LENGTH
            else x
        )
    return df


def safe_filename(name: str) -> str:
    """Converte nome da categoria em nome de arquivo seguro (sem acentos, espaços, etc.)."""
    safe = (
        name
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
    return re.sub(r"[^\w]", "", safe)