"""Extração e normalização de números CNJ, STJ e outros identificadores."""
from __future__ import annotations

import re


# Padrão CNJ: 0000000-00.0000.0.00.0000
_CNJ_RE = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")

# Padrão STJ registro: 2025/0379643-0
_STJ_REGISTRO_RE = re.compile(r"\d{4}/\d{7}-\d")

# Padrão STJ número sequencial: Nº 3070359
_STJ_NUMERO_RE = re.compile(r"Nº\s*(\d{5,8})")

# Número puro (só dígitos, mínimo 5 para evitar falsos positivos)
_DIGITS_ONLY_RE = re.compile(r"^\d{5,}$")

def extract_all_numbers(raw: str) -> set[str]:
    """Extrai todos os identificadores possíveis de uma string.\n    Retorna um set de strings normalizadas (sem espaços, sem pontuação desnecessária)."""
    if not raw or not raw.strip():
        return set()

    raw = raw.strip()
    results: set[str] = set()

    # 1. CNJ padrão (com pontuação)
    for match in _CNJ_RE.finditer(raw):
        cnj = match.group()
        results.add(cnj)
        # Também adiciona versão só dígitos (para comparar com "Número antigo")
        results.add(re.sub(r"[.\-]", "", cnj))

    # 2. Registro STJ: 2025/0379643-0
    for match in _STJ_REGISTRO_RE.finditer(raw):
        results.add(match.group())

    # 3. Número sequencial STJ: Nº 3070359
    for match in _STJ_NUMERO_RE.finditer(raw):
        results.add(match.group(1))

    # 4. Se a string inteira já é um número puro
    clean = re.sub(r"[\s.\-/]", "", raw)
    if _DIGITS_ONLY_RE.match(clean):
        results.add(clean)

    # 5. Se nada foi encontrado, usa a string original limpa
    if not results:
        results.add(raw)

    return results

def normalize_number(raw: str) -> str:
    """Remove pontuação e espaços para comparação."""
    return re.sub(r"[\s.\-/]", "", raw.strip()) if raw else ""