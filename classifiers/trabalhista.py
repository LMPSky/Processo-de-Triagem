from __future__ import annotations

from rapidfuzz import fuzz
from .common import load_json

CATEGORIA_TERMS = load_json("trabalhista_categorias.json", {})


def classify_trabalhista_text(texto: str, threshold: int = 70) -> str | None:
    if not isinstance(texto, str) or not texto:
        return None

    texto_proc = texto.lower().replace("\n", " ")
    best_match = None
    highest_ratio = 0

    for categoria, aliases in CATEGORIA_TERMS.items():
        for alias in aliases:
            ratio = fuzz.partial_ratio(alias.lower(), texto_proc)
            if ratio > highest_ratio:
                highest_ratio = ratio
                best_match = categoria

    if highest_ratio >= threshold:
        return best_match
    return None