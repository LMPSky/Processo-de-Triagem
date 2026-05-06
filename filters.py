# Filtros: duplicatas, classificação de número, UF, ramo, dígito verificador e idade.
from __future__ import annotations

import re
import pandas as pd


# ══════════════════════════════════════════════════════════
# Padrões de número
# ══════════════════════════════════════════════════════════

_CNJ_RE = re.compile(r"^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$")
_STJ_FULL_RE = re.compile(r"Nº\s*\d+.*\(\d{4}/\d{7}-\d\)")
_STJ_REGISTRO_RE = re.compile(r"\d{4}/\d{7}-\d")
_DIGITS_ONLY_RE = re.compile(r"^\d{5,}$")
_SEM_EXPEDIENTE_TERMS = [
    "sem expediente",
    "sem processo",
    "não localizado",
    "nao localizado",
    "não informado",
    "nao informado",
    "não informado",
    "n/a",
    "n/d",
    "pendente",
    "[alterar]",
]


def classify_number(value: str) -> str:
    """
    Classifica o tipo de um identificador numérico.

    Returns:
        Uma das strings: 'vazio', 'sem_expediente', 'cnj', 'stj',
        'numero_puro', 'texto', 'outro'.
    """
    if not value or not value.strip():
        return "vazio"

    clean = value.strip()
    lower = clean.lower()

    for term in _SEM_EXPEDIENTE_TERMS:
        if term in lower:
            return "sem_expediente"

    if _CNJ_RE.match(clean):
        return "cnj"

    if _STJ_FULL_RE.search(clean):
        return "stj"

    if _STJ_REGISTRO_RE.match(clean):
        return "stj"

    clean_digits = re.sub(r"[\s.\-/]", "", clean)
    if _DIGITS_ONLY_RE.match(clean_digits):
        return "numero_puro"

    if re.search(r"[a-zA-ZÀ-ÿ]", clean):
        return "texto"

    return "outro"


# ══════════════════════════════════════════════════════════
# Filtro 0: Validar CNJ (novo)
# ══════════════════════════════════════════════════════════

def is_valid_cnj(cnj: str) -> bool:
    """
    Verifica se o CNJ é válido e não é um número genérico/administrativo.
    
    Filtra:
    - CNJs vazios ou muito curtos
    - Números genéricos/administrativos
    - Números sem dígitos
    """
    if not cnj:
        return False
    
    cnj_norm = str(cnj).strip().lower()
    
    # CNJs genéricos/administrativos que devem ser filtrados
    INVALID_CNJS = [
        "02/2026",           # Administrativo (190 duplicatas!)
        "004/2020",          # Administrativo
        "47/2026",           # Administrativo
        "0000/2026",         # Genérico
        "9999/2026",         # Genérico
        "00/0000",           # Genérico
    ]
    
    # Verificar contra lista
    if cnj_norm in INVALID_CNJS:
        return False
    
    # CNJ válido deve ter pelo menos 15 caracteres
    # Formato: 0000000-00.0000.0.00.0000
    if len(cnj_norm) < 15:
        return False
    
    # CNJ válido tem dígitos
    if not any(c.isdigit() for c in cnj_norm):
        return False
    
    return True


# ══════════════════════════════════════════════════════════
# Filtro 1: Remover duplicatas
# ══════════════════════════════════════════════════════════

def remove_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Remove linhas duplicadas por CNJ, mantendo a primeira ocorrência."""
    is_dup = df.duplicated(subset=["cnj"], keep="first")

    unique = df[~is_dup].copy()
    duplicates = df[is_dup].copy()

    if len(duplicates) > 0:
        print(f"   🔄 Duplicatas removidas: {len(duplicates)} linhas")
        print(f"   ✅ Restaram: {len(unique)} linhas únicas")
    else:
        print(f"   ✅ Nenhuma duplicata encontrada")

    return unique, duplicates


# ══════════════════════════════════════════════════════════
# Filtro 1.5: Remover CNJs inválidos (novo)
# ══════════════════════════════════════════════════════════

def remove_invalid_cnjs(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Remove linhas com CNJs genéricos/administrativos.
    
    Returns:
        (DataFrame válido, DataFrame com CNJs inválidos)
    """
    valid_mask = df["cnj"].apply(is_valid_cnj)
    
    valid = df[valid_mask].copy()
    invalid = df[~valid_mask].copy()
    
    if len(invalid) > 0:
        print(f"   🚫 CNJs inválidos removidos: {len(invalid)} linhas")
        print(f"   ✅ Restaram: {len(valid)} linhas com CNJ válido")
        
        # Mostrar exemplos
        invalid_samples = invalid["cnj"].unique()[:5]
        print(f"   Exemplos de CNJs inválidos:")
        for cnj in invalid_samples:
            print(f"      • {cnj}")
    else:
        print(f"   ✅ Nenhum CNJ inválido encontrado")
    
    return valid, invalid


# ══════════════════════════════════════════════════════════
# Filtro 2: Classificar tipo de número
# ══════════════════════════════════════════════════════════

def add_number_classification(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona coluna 'tipo_numero' com a classificação de cada CNJ."""
    df = df.copy()
    df["tipo_numero"] = df["cnj"].apply(classify_number)

    counts = df["tipo_numero"].value_counts()
    print(f"   📊 Classificação dos números:")
    for tipo, count in counts.items():
        print(f"      • {tipo}: {count}")

    return df


# ══════════════════════════════════════════════════════════
# Filtro 3: Enriquecer com informações de fonte
# ══════════════════════════════════════════════════════════

def enrich_with_source_info(df: pd.DataFrame) -> pd.DataFrame:
    """Enriquece o DataFrame com informações sobre presença em múltiplas fontes."""
    df = df.copy()

    source_info = (
        df.groupby("cnj")['_fonte']
        .apply(lambda x: sorted(set(x)))
        .reset_index()
    )
    source_info["_fontes"] = source_info["_fonte"].apply(lambda x: ", ".join(x))
    source_info["_qtd_fontes"] = source_info["_fonte"].apply(len)
    source_info = source_info.drop(columns=["_fonte"])

    df = df.drop(columns=["_fontes", "_qtd_fontes"], errors="ignore")
    df = df.merge(source_info, on="cnj", how="left")

    df = df.sort_values("_qtd_fontes", ascending=False).reset_index(drop=True)

    multi = df[df["_qtd_fontes"] > 1]["cnj"].nunique()
    single = df[df["_qtd_fontes"] == 1]["cnj"].nunique()
    print(f"   📊 Presença em múltiplas fontes:")
    print(f"      • Em mais de 1 fonte: {multi} processos")
    print(f"      • Em apenas 1 fonte:  {single} processos")

    return df


# ══════════════════════════════════════════════════════════
# Filtro 4: Extrair UF e Ramo da Justiça do CNJ
# ═══════���══════════════════════════════════════════════════

_RAMOS_JUSTICA = {
    "1": "STF",
    "2": "CNJ",
    "3": "STJ",
    "4": "Justiça Federal",
    "5": "Justiça do Trabalho",
    "6": "Justiça Eleitoral",
    "7": "Justiça Militar da União",
    "8": "Justiça Estadual",
    "9": "Justiça Militar Estadual",
}

# Melhoria #8: Separado em dois dicionários para evitar sobrescrita de chaves
_UF_FEDERAL = {
    "01": "DF",
    "02": "RJ/ES",
    "03": "SP/MS",
    "04": "RS/SC/PR",
    "05": "PE/CE/AL/SE/PB/RN",
    "06": "MG",
}

_UF_ESTADUAL = {
    "01": "AC", "02": "AL", "03": "AP", "04": "AM", "05": "BA",
    "06": "CE", "07": "DF", "08": "ES", "09": "GO", "10": "MA",
    "11": "MT", "12": "MS", "13": "MG", "14": "PA", "15": "PB",
    "16": "PE", "17": "PI", "18": "PR", "19": "RJ", "20": "RN",
    "21": "RS", "22": "RO", "23": "RR", "24": "SC", "25": "SE",
    "26": "SP", "27": "TO",
}

_CNJ_PARSE_RE = re.compile(
    r"^(\d{7})-(\d{2})\.(\d{4})\.(\d)\.(\d{2})\.(\d{4})$"
)


def _parse_cnj(cnj: str) -> dict[str, str]:
    """
    Extrai componentes do CNJ.
    Formato: NNNNNNN-DD.AAAA.J.TT.OOOO
    N=número, D=dígito, A=ano, J=justiça, T=tribunal, O=origem
    """
    m = _CNJ_PARSE_RE.match(cnj.strip())
    if not m:
        return {}

    numero, digito, ano, justica, tribunal, origem = m.groups()

    ramo = _RAMOS_JUSTICA.get(justica, f"Desconhecido ({justica})")

    # UF depende do ramo — cada ramo usa seu próprio dicionário
    uf = "N/A"
    if justica == "8":  # Estadual
        uf = _UF_ESTADUAL.get(tribunal, f"UF? ({tribunal})")
    elif justica == "5":  # Trabalho
        uf = f"TRT-{tribunal}"
    elif justica == "4":  # Federal
        uf = _UF_FEDERAL.get(tribunal, f"TRF-{tribunal}")

    return {
        "ano_processo": ano,
        "ramo_justica": ramo,
        "tribunal": tribunal,
        "uf": uf,
        "origem": origem,
    }


def add_cnj_details(df: pd.DataFrame) -> pd.DataFrame:
    """Para processos com tipo_numero='cnj', extrai ano, ramo da justiça, UF."""
    df = df.copy()

    # Inicializa colunas
    df["ano_processo"] = ""
    df["ramo_justica"] = ""
    df["uf"] = ""

    mask_cnj = df["tipo_numero"] == "cnj"

    if mask_cnj.sum() == 0:
        return df

    parsed = df.loc[mask_cnj, "cnj"].apply(_parse_cnj)

    df.loc[mask_cnj, "ano_processo"] = parsed.apply(lambda x: x.get("ano_processo", ""))
    df.loc[mask_cnj, "ramo_justica"] = parsed.apply(lambda x: x.get("ramo_justica", ""))
    df.loc[mask_cnj, "uf"] = parsed.apply(lambda x: x.get("uf", ""))

    # Resumo
    print(f"\n   📊 Ramo da Justiça (CNJs):")
    ramo_counts = df.loc[mask_cnj, "ramo_justica"].value_counts()
    for ramo, count in ramo_counts.items():
        if ramo:
            print(f"      • {ramo}: {count}")

    print(f"\n   📊 UF (CNJs):")
    uf_counts = df.loc[mask_cnj, "uf"].value_counts()
    for uf, count in uf_counts.head(15).items():
        if uf:
            print(f"      • {uf}: {count}")
    if len(uf_counts) > 15:
        print(f"      ... e mais {len(uf_counts) - 15} UFs")

    return df


# ══════════════════════════════════════════════════════════
# Filtro 5: Validar dígito verificador do CNJ
# ══════════════════════════════════════════════════════════

def _validate_cnj_check_digit(cnj: str) -> bool:
    """
    Valida o dígito verificador do CNJ conforme Resolução 65.
    Formato: NNNNNNN-DD.AAAA.J.TT.OOOO
    Monta NNNNNNNAAAAJTTOOOODD e verifica se mod 97 == 1.
    """
    m = _CNJ_PARSE_RE.match(cnj.strip())
    if not m:
        return False

    numero, digito, ano, justica, tribunal, origem = m.groups()

    try:
        full_number = f"{numero}{ano}{justica}{tribunal}{origem}{digito}"
        return int(full_number) % 97 == 1
    except (ValueError, ZeroDivisionError):
        return False


def add_cnj_validation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Valida o dígito verificador dos CNJs.
    Adiciona coluna 'cnj_valido' (True/False).
    """
    df = df.copy()
    df["cnj_valido"] = True  # Default

    mask_cnj = df["tipo_numero"] == "cnj"

    if mask_cnj.sum() == 0:
        return df

    df.loc[mask_cnj, "cnj_valido"] = df.loc[mask_cnj, "cnj"].apply(_validate_cnj_check_digit)

    valid = df.loc[mask_cnj, "cnj_valido"].sum()
    invalid = mask_cnj.sum() - valid

    print(f"\n   📊 Validação de dígito verificador (CNJs):")
    print(f"      • Válidos:   {valid}")
    print(f"      • Inválidos: {invalid}")

    if invalid > 0:
        invalid_cnjs = df.loc[mask_cnj & ~df["cnj_valido"], "cnj"].head(10).tolist()
        print(f"      Exemplos de CNJs inválidos:")
        for cnj in invalid_cnjs:
            print(f"        ⚠️  {cnj}")

    return df


# ══════════════════════════════════════════════════════════
# Filtro 6: Marcar processos antigos
# ══════════════════════════════════════════════════════════

def add_age_flag(df: pd.DataFrame, cutoff_year: int = 2015) -> pd.DataFrame:
    """
    Marca processos com ano anterior ao cutoff_year.
    Adiciona coluna 'processo_antigo' (True/False).
    """
    df = df.copy()
    df["processo_antigo"] = False

    mask_cnj = df["tipo_numero"] == "cnj"

    if mask_cnj.sum() == 0 or "ano_processo" not in df.columns:
        return df

    def _is_old(ano: str) -> bool:
        try:
            return int(ano) < cutoff_year
        except (ValueError, TypeError):
            return False

    df.loc[mask_cnj, "processo_antigo"] = df.loc[mask_cnj, "ano_processo"].apply(_is_old)

    old_count = df.loc[mask_cnj, "processo_antigo"].sum()
    new_count = mask_cnj.sum() - old_count

    print(f"\n   📊 Idade dos processos (CNJs, corte: {cutoff_year}):")
    print(f"      • Antigos (antes de {cutoff_year}): {old_count}")
    print(f"      • Recentes ({cutoff_year}+):        {new_count}")

    if old_count > 0:
        # Mostra distribuição por ano dos antigos
        old_anos = df.loc[mask_cnj & df["processo_antigo"], "ano_processo"].value_counts().sort_index()
        print(f"      Distribuição dos antigos:")
        for ano, count in old_anos.items():
            print(f"        • {ano}: {count}")

    return df