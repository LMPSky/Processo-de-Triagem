from __future__ import annotations

import pandas as pd
from .common import load_json, contains_any
from .normalizer import normalize_text, resolve_client_group

CIVEL_PRIORITY_NAMES = load_json("civel_priority_names.json", [])
CIVEL_PRIORITY_CLIENTS = load_json("civel_priority_clients.json", [])
CIVEL_EXCLUDENTES = load_json("civel_excludentes.json", [])
CIVEL_NUMERO_PATTERNS = load_json("civel_numero_patterns.json", [])
CIVEL_CATEGORIAS = load_json("civel_categorias.json", {})
CIVEL_MACROCATEGORIAS = load_json("civel_macrocategorias.json", {})
CLIENT_ALIASES = load_json("client_aliases.json", {})


def confidence_from_signals(
    *,
    is_excluded: bool,
    match_location: str = "",
    has_priority: bool = False,
    has_specific_category: bool = False,
    has_macro_category: bool = False,
    has_generic_keyword: bool = False,
    has_num_relevante: bool = False,
    match_count: int = 0,
) -> int:
    """
    Score sofisticado:
    - Levanta score se match está no texto (mais relevante que cliente)
    - Levanta score com múltiplos sinais de confirmação
    - Penaliza se apenas keyword genérica
    """
    if is_excluded:
        return 99

    score = 0

    if has_specific_category:
        score = 90
        if match_location == "texto":
            score += 5
    elif has_macro_category:
        score = 70
        if match_location == "texto":
            score += 5
    elif has_generic_keyword:
        score = 50
        if match_location == "texto":
            score += 3
    else:
        score = 0

    if has_priority:
        score += 8
    if has_num_relevante:
        score += 5

    if match_count > 1:
        score += 3

    return min(score, 100)


def _detect_match_location(texto_norm: str, cliente_norm: str, termo: str) -> str:
    """Detecta se o termo foi encontrado em texto ou cliente."""
    termo_norm = normalize_text(termo)
    if termo_norm in texto_norm:
        return "texto"
    if termo_norm in cliente_norm:
        return "cliente"
    return "unknown"


def classify_civel_record(row: pd.Series) -> pd.Series:
    texto = str(row.get("_texto", "") or "")
    cliente = str(row.get("_cliente", "") or "")
    cnj = str(row.get("cnj", "") or "")

    texto_norm = normalize_text(texto)
    cliente_norm = normalize_text(cliente)
    base_norm = " | ".join([texto_norm, cliente_norm, normalize_text(cnj)])

    categoria = None
    macro_categoria = None
    subcategoria = None
    prioridade = ""
    motivo = ""
    cliente_match = ""
    cliente_group = ""
    excludente_match = ""
    confidence = 0
    match_count = 0

    has_priority = False
    has_specific_category = False
    has_macro_category = False
    has_generic_keyword = False
    has_num_relevante = False
    match_location = ""

    if cliente:
        resolved_group = resolve_client_group(cliente, CLIENT_ALIASES)
        if resolved_group != cliente:
            cliente_group = resolved_group

    excludente = contains_any(base_norm, CIVEL_EXCLUDENTES)

    if excludente and normalize_text(excludente) == "light":
        if ("tribut" in base_norm) or ("ente" in base_norm):
            excludente = None

    if excludente:
        categoria = "EXCLUIDO"
        motivo = f"excludente:{excludente}"
        excludente_match = excludente
        confidence = confidence_from_signals(
            is_excluded=True,
            has_priority=False,
            has_specific_category=False,
            has_macro_category=False,
            has_generic_keyword=False,
            has_num_relevante=False,
        )
        return pd.Series({
            "_categoria_civel": categoria,
            "_macro_categoria_civel": macro_categoria,
            "_subcategoria_civel": subcategoria,
            "_prioridade_civel": prioridade,
            "_motivo_civel": motivo,
            "_cliente_match": cliente_match,
            "_cliente_group": cliente_group,
            "_excludente_match": excludente_match,
            "_confidence_civel": confidence,
        })

    nome_match = contains_any(base_norm, CIVEL_PRIORITY_NAMES)
    if nome_match:
        prioridade = "PRIORIDADE"
        has_priority = True
        match_count += 1
        motivo = f"nome_prioritario:{nome_match}"

    cliente_prio = contains_any(base_norm, CIVEL_PRIORITY_CLIENTS)
    if cliente_prio:
        prioridade = "PRIORIDADE"
        has_priority = True
        match_count += 1
        cliente_match = cliente_prio
        motivo = f"{motivo} | cliente_prioritario:{cliente_prio}".strip(" |")

    num_relevante = contains_any(base_norm, CIVEL_NUMERO_PATTERNS)
    if num_relevante:
        has_num_relevante = True
        match_count += 1
        subcategoria = "numero_relevante"
        motivo = f"{motivo} | numero_relevante:{num_relevante}".strip(" |")

    for cat, termos in CIVEL_CATEGORIAS.items():
        termo_cat = contains_any(base_norm, termos)
        if termo_cat:
            categoria = cat
            has_specific_category = True
            match_count += 1
            match_location = _detect_match_location(texto_norm, cliente_norm, termo_cat)
            motivo = f"{motivo} | categoria:{termo_cat}".strip(" |")
            break

    if categoria is None:
        for macro, termos in CIVEL_MACROCATEGORIAS.items():
            termo_macro = contains_any(base_norm, termos)
            if termo_macro:
                categoria = macro
                macro_categoria = macro
                has_macro_category = True
                match_count += 1
                match_location = _detect_match_location(texto_norm, cliente_norm, termo_macro)
                motivo = f"{motivo} | macro:{termo_macro}".strip(" |")
                break

    if categoria is None:
        if "recurso" in base_norm:
            categoria = "Recursos"
            macro_categoria = "Recursos"
            has_generic_keyword = True
            motivo = f"{motivo} | palavra:recurso".strip(" |")
        elif "agravo" in base_norm:
            categoria = "Recursos"
            macro_categoria = "Recursos"
            has_generic_keyword = True
            motivo = f"{motivo} | palavra:agravo".strip(" |")
        elif "embargos" in base_norm:
            categoria = "Embargos"
            macro_categoria = "Embargos"
            has_generic_keyword = True
            motivo = f"{motivo} | palavra:embargos".strip(" |")
        elif "cumprimento de sentenca" in base_norm or "cumprimento de sentença" in base_norm:
            categoria = "Cumprimento de Sentença"
            macro_categoria = "Execução/Cumprimento"
            has_generic_keyword = True
            motivo = f"{motivo} | palavra:cumprimento de sentença".strip(" |")
        elif "carta precatoria" in base_norm or "carta precatória" in base_norm:
            categoria = "Carta Precatória Cível"
            macro_categoria = "Instrumentos Auxiliares"
            has_generic_keyword = True
            motivo = f"{motivo} | palavra:carta precatoria".strip(" |")

    confidence = confidence_from_signals(
        is_excluded=False,
        match_location=match_location,
        has_priority=has_priority,
        has_specific_category=has_specific_category,
        has_macro_category=has_macro_category,
        has_generic_keyword=has_generic_keyword,
        has_num_relevante=has_num_relevante,
        match_count=match_count,
    )

    return pd.Series({
        "_categoria_civel": categoria,
        "_macro_categoria_civel": macro_categoria,
        "_subcategoria_civel": subcategoria,
        "_prioridade_civel": prioridade,
        "_motivo_civel": motivo,
        "_cliente_match": cliente_match,
        "_cliente_group": cliente_group,
        "_excludente_match": excludente_match,
        "_confidence_civel": confidence,
    })