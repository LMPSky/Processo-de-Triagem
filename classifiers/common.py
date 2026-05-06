from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from collections import Counter
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "configs"


def load_json(filename: str, default):
    path = CONFIG_DIR / filename
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return default
            return json.loads(content)
    except Exception:
        return default


def sanitize_sheet_name(name: str) -> str:
    name = str(name or "categoria")
    name = re.sub(r'[/\\\?\*\:\[\]]', '_', name)
    return name[:31]


def normalize_text(texto) -> str:
    if texto is None:
        return ""

    s = str(texto)

    s = s.replace("??", " ")
    s = s.replace("ô", "o")
    s = s.replace("ü", "u")

    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = s.lower()
    s = s.replace("\n", " ")
    s = s.replace("\r", " ")
    s = s.replace("\t", " ")
    s = re.sub(r"\s+", " ", s).strip()

    return s


def contains_any(texto_norm: str, termos: list[str]) -> str | None:
    for termo in termos:
        termo_norm = normalize_text(termo)
        if termo_norm and termo_norm in texto_norm:
            return termo
    return None


def safe_filename(name: str) -> str:
    safe = (
        name.lower()
        .replace(" ", "_")
        .replace("ã", "a").replace("á", "a")
        .replace("é", "e").replace("í", "i")
        .replace("ó", "o").replace("ú", "u")
        .replace("ç", "c").replace("-", "_")
    )
    return re.sub(r"[^\w]", "", safe)


def truncate_text_column(df: pd.DataFrame, max_text_length: int = 500) -> pd.DataFrame:
    df = df.copy()
    if "_texto" in df.columns:
        df["_texto"] = df["_texto"].apply(
            lambda x: (x[:max_text_length] + "... [TRUNCADO]") if isinstance(x, str) and len(x) > max_text_length else x
        )
    return df


def rename_output_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "_data_publicacao": "Data da Publicação",
        "_data_captura": "Data da Captura",
        "_tribunal": "Tribunal",
        "_sistema": "Sistema",
        "_categoria_civel": "categoria_civel",
        "_macro_categoria_civel": "macro_categoria_civel",
        "_subcategoria_civel": "subcategoria_civel",
        "_prioridade_civel": "prioridade_civel",
        "_motivo_civel": "motivo_civel",
        "_cliente_match": "cliente_match",
        "_cliente_group": "cliente_group",
        "_excludente_match": "excludente_match",
        "_confidence_civel": "confidence_civel",
    }
    cols_present = {k: v for k, v in rename_map.items() if k in df.columns}
    return df.rename(columns=cols_present)


def word_frequency(text_series: pd.Series, top_n: int = 50) -> pd.DataFrame:
    stopwords = {
        "de", "da", "do", "das", "dos", "e", "o", "a", "os", "as", "em", "para", "por",
        "com", "sem", "na", "no", "nas", "nos", "um", "uma", "ao", "aos", "à", "às",
        "que", "se", "del", "dela", "processo", "judicial", "justica", "justiça"
    }
    counter = Counter()

    for text in text_series.fillna("").astype(str):
        norm = normalize_text(text)
        if norm:
            words = re.findall(r"\b[a-z0-9]{3,}\b", norm)
            words = [w for w in words if w not in stopwords]
            counter.update(words)

    if not counter:
        return pd.DataFrame(columns=["Palavra", "Frequencia"])

    data = counter.most_common(top_n)
    return pd.DataFrame(data, columns=["Palavra", "Frequencia"])