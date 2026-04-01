"""Orquestrador principal — comparação com Legal One e exportação de resultados."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import re
import pandas as pd
from config import AppConfig
from reader import read_source, read_all_external
from number_extractor import extract_all_numbers, normalize_number
from filters import (
    remove_duplicates,
    add_number_classification,
    enrich_with_source_info,
    add_cnj_details,
    add_cnj_validation,
    add_age_flag,
)
from categorizer import classify_text


_MAX_TEXT_LENGTH = 500

def _truncate_text_column(df: pd.DataFrame) -> pd.DataFrame:
    """Trunca a coluna _texto para caber no Excel."""
    df = df.copy()
    if "_texto" in df.columns:
        df["_texto"] = df["_texto"].apply(
            lambda x: (x[:_MAX_TEXT_LENGTH] + "... [TRUNCADO]") if isinstance(x, str) and len(x) > _MAX_TEXT_LENGTH else x
        )
    return df

def _safe_filename(name: str) -> str:
    """Converte nome da categoria em nome de arquivo seguro."""
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

def _build_legalone_pool(legalone_df: pd.DataFrame, extra_columns: list[str]) -> set[str]:
    pool: set[str] = set()

    for _, row in legalone_df.iterrows():
        cnj = str(row.get("cnj", "")).strip()
        if cnj:
            pool.update(extract_all_numbers(cnj))
            pool.add(normalize_number(cnj))

        for col in extra_columns:
            val = str(row.get(col, "")).strip()
            if val and val != "nan":
                pool.update(extract_all_numbers(val))
                pool.add(normalize_number(val))

    pool.discard("")
    return pool

def _check_match(cnj_value: str, legalone_pool: set[str]) -> bool:
    numbers = extract_all_numbers(cnj_value)

    for num in numbers:
        if num in legalone_pool:
            return True
        if normalize_number(num) in legalone_pool:
            return True

    return False

def run_matching(config: AppConfig) -> None:
    """Executa o matching completo e exporta os resultados."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ──────────────────────────────────────────────
    # 1. Ler a base do Legal One
    # ──────────────────────────────────────────────
    print("═" * 60)
    print("📂 Lendo fonte: LEGAL ONE")
    legalone_df = read_source(config.legalone, config.input_dir)

    print(f"   → {len(legalone_df)} linhas no Legal One")

    extra_cols = config.legalone.extra_match_columns
    legalone_pool = _build_legalone_pool(legalone_df, extra_cols)
    print(f"   → {len(legalone_pool)} identificadores únicos no pool de comparação")

    # ──────────────────────────────────────────────
    # 2. Ler e juntar as 3 bases externas
    # ──────────────────────────────────────────────
    print("\n" + "═" * 60)
    external_df = read_all_external(config)
    print(f"\n   → {len(external_df)} linhas totais nas bases externas")

    # ──────────────────────────────────────────────
    # 3. Classificar tipo de número
    # ──────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("📋 Classificando tipos de número...")
    external_df = add_number_classification(external_df)

    # ──────────────────────────────────────────────
    # 4. Enriquecer com info de fontes
    # ──────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("📋 Analisando presença em múltiplas fontes...")
    external_df = enrich_with_source_info(external_df)

    # ──────────────────────────────────────────────
    # 5. Remover duplicatas
    # ──────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("📋 Removendo duplicatas...")
    external_df, duplicates_df = remove_duplicates(external_df)

    # ──────────────────────────────────────────────
    # 6. Extrair detalhes do CNJ (UF, Ramo, Ano)
    # ──────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("📋 Extraindo detalhes dos CNJs (UF, Ramo, Ano)...")
    external_df = add_cnj_details(external_df)

    # ──────────────────────────────────────────────
    # 7. Validar dígito verificador
    # ──────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("📋 Validando dígito verificador dos CNJs...")
    external_df = add_cnj_validation(external_df)

    # ──────────────────────────────────────────────
    # 8. Marcar processos antigos
    # ──────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("📋 Verificando idade dos processos...")
    external_df = add_age_flag(external_df, cutoff_year=2015)

    # ──────────────────────────────────────────────
    # 9. Comparar TODOS com Legal One
    # ──────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("🔍 Comparando com Legal One...")

    external_df["match_legalone"] = external_df["cnj"].apply(
        lambda x: _check_match(x, legalone_pool)
    )

    matched = external_df[external_df["match_legalone"]].copy()
    unmatched = external_df[~external_df["match_legalone"]].copy()

    print(f"   ✅ COM match (nossos):  {len(matched)} linhas")
    print(f"   ❌ SEM match (lixo):    {len(unmatched)} linhas")

    # ──────────────────────────────────────────────
    # 10. Classificar os COM MATCH por categoria
    # ──────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("📋 Classificando processos COM match por categoria...")

    matched["_categoria"] = matched["_texto"].apply(classify_text)

    # Separar Décio Freire como PRIORIDADE
    decio_df = matched[matched["_categoria"] == "Décio Freire"].copy()
    other_categorized = matched[
        (matched["_categoria"].notna()) & (matched["_categoria"] != "Décio Freire")
    ].copy()
    no_category = matched[matched["_categoria"].isna()].copy()

    print(f"   ⭐ Décio Freire (PRIORIDADE): {len(decio_df)} linhas")
    print(f"   📂 Outras categorias:         {len(other_categorized)} linhas")
    print(f"   📄 Sem categoria:             {len(no_category)} linhas")

    if len(other_categorized) > 0:
        print(f"\n   📊 Por categoria:")
        for cat, count in other_categorized["_categoria"].value_counts().items():
            print(f"      • {cat}: {count}")

    # ──────────────────────────────────────────────
    # 11. Exportar resultados
    # ──────────────────────────────────────────────
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    cols_to_drop = ["match_legalone", "_categoria"]

    # --- DÉCIO FREIRE (PRIORIDADE) ---
    decio_path = out / f"PRIORIDADE_decio_freire_{timestamp}.xlsx"
    if len(decio_df) > 0:
        _truncate_text_column(decio_df.drop(columns=cols_to_drop, errors="ignore")).to_excel(
            decio_path, index=False, sheet_name="Décio Freire", engine="openpyxl"
        )

    # --- CATEGORIAS (1 arquivo por categoria) ---
    categories_dir = out / "categorias"
    categories_dir.mkdir(parents=True, exist_ok=True)

    if len(other_categorized) > 0:
        print(f"\n   📁 Arquivos por categoria:")
        for category in sorted(other_categorized["_categoria"].unique()):
            cat_df = other_categorized[other_categorized["_categoria"] == category].copy()

            safe_name = _safe_filename(category)
            file_path = categories_dir / f"{safe_name}_{timestamp}.xlsx"

            _truncate_text_column(
                cat_df.drop(columns=cols_to_drop, errors="ignore")
            ).to_excel(
                file_path, index=False, sheet_name=category[:31], engine="openpyxl"
            )
            print(f"      • {file_path.name}  ({len(cat_df)} linhas)")

    # Consolidado de todos os categorizados
    all_categorized = pd.concat([decio_df, other_categorized], ignore_index=True)
    if len(all_categorized) > 0:
        all_cat_path = categories_dir / f"todos_classificados_{timestamp}.xlsx"
        _truncate_text_column(
            all_categorized.drop(columns=["match_legalone"], errors="ignore")
        ).to_excel(
            all_cat_path, index=False, sheet_name="classificados", engine="openpyxl"
        )
        print(f"      • {all_cat_path.name}  (consolidado: {len(all_categorized)} linhas)")

    # --- COM MATCH SEM CATEGORIA (nossos, mas genéricos) ---
    general_path = out / f"com_match_geral_{timestamp}.xlsx"
    if len(no_category) > 0:
        _truncate_text_column(
            no_category.drop(columns=cols_to_drop, errors="ignore")
        ).to_excel(
            general_path, index=False, sheet_name="com_match_geral", engine="openpyxl"
        )

    # --- LIXO (sem match = não está no Legal One) ---
    lixo_path = out / f"lixo_sem_match_{timestamp}.xlsx"
    _truncate_text_column(
        unmatched.drop(columns=cols_to_drop, errors="ignore")
    ).to_excel(
        lixo_path, index=False, sheet_name="lixo", engine="openpyxl"
    )

    # --- DUPLICATAS ---
    dup_path = out / f"duplicados_removidos_{timestamp}.xlsx"
    if len(duplicates_df) > 0:
        _truncate_text_column(duplicates_df).to_excel(
            dup_path, index=False, sheet_name="duplicados", engine="openpyxl"
        )

    # --- PROCESSOS ANTIGOS ---
    old_processes = matched[matched["processo_antigo"] == True]
    old_path = out / f"processos_antigos_{timestamp}.xlsx"
    if len(old_processes) > 0:
        _truncate_text_column(
            old_processes.drop(columns=cols_to_drop, errors="ignore")
        ).to_excel(
            old_path, index=False, sheet_name="antigos", engine="openpyxl"
        )

    # ──────────────────────────────────────────────
    # 12. Relatório resumo
    # ──────────────────────────────────────────────
    summary_path = out / f"resumo_{timestamp}.txt"

    mask_cnj = external_df["tipo_numero"] == "cnj"

    summary_lines = [
        f"Relatório de Triagem — {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"{'=' * 55}",
        f"",
        f"LEGAL ONE",
        f"  Linhas:                  {len(legalone_df)}",
        f"  Identificadores no pool: {len(legalone_pool)}",
        f"",
        f"BASES EXTERNAS (Painel + DW + WebJur)",
        f"  Linhas totais (antes):   {len(external_df) + len(duplicates_df)}",
        f"  Duplicatas removidas:    {len(duplicates_df)}",
        f"  Linhas após dedup:       {len(external_df)}",
        f"",
        f"MATCH COM LEGAL ONE",
        f"  COM match (nossos):      {len(matched)} linhas",
        f"  SEM match (lixo):        {len(unmatched)} linhas",
        f"",
        f"PROCESSOS NOSSOS — CLASSIFICAÇÃO",
        f"  ⭐ Décio Freire (PRIORIDADE): {len(decio_df)}",
    ]

    if len(other_categorized) > 0:
        for cat, count in other_categorized["_categoria"].value_counts().items():
            summary_lines.append(f"  • {cat}: {count}")

    summary_lines += [
        f"  Sem categoria (genéricos):    {len(no_category)}",
        f"",
        f"DETALHES DOS CNJs (todos)",
    ]

    if mask_cnj.sum() > 0:
        summary_lines.append(f"  Ramo da Justiça:")
        for ramo, count in external_df.loc[mask_cnj, "ramo_justica"].value_counts().items():
            if ramo:
                summary_lines.append(f"    • {ramo}: {count}")

        summary_lines.append(f"  UF (top 15):")
        for uf, count in external_df.loc[mask_cnj, "uf"].value_counts().head(15).items():
            if uf:
                summary_lines.append(f"    • {uf}: {count}")

    summary_lines += [
        f"",
        f"VALIDAÇÃO DE DÍGITO VERIFICADOR",
        f"  CNJs válidos:   {external_df.loc[mask_cnj, 'cnj_valido'].sum() if mask_cnj.sum() > 0 else 0}",
        f"  CNJs inválidos: {(mask_cnj & ~external_df['cnj_valido']).sum() if mask_cnj.sum() > 0 else 0}",
        f"",
        f"IDADE DOS PROCESSOS (corte: 2015)",
        f"  Antigos (antes de 2015): {matched['processo_antigo'].sum()}",
        f"  Recentes (2015+):        {len(matched) - matched['processo_antigo'].sum()}",
        f"",
        f"ARQUIVOS GERADOS",
    ]

    if len(decio_df) > 0:
        summary_lines.append(f"  ⭐ {decio_path.name}  (PRIORIDADE)")
    summary_lines.append(f"  {general_path.name}  (nossos sem categoria)")
    summary_lines.append(f"  {lixo_path.name}  (lixo)")
    if len(duplicates_df) > 0:
        summary_lines.append(f"  {dup_path.name}")
    if len(old_processes) > 0:
        summary_lines.append(f"  {old_path.name}  (processos antigos nossos)")
    summary_lines += [
        f"  categorias/  (1 arquivo por categoria)",
        f"  {summary_path.name}",
    ]

    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")

    # ──────────────────────────────────────────────
    # 13. Print final
    # ──────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print(f"📁 Arquivos gerados em: {out.resolve()}")
    if len(decio_df) > 0:
        print(f"   ⭐ {decio_path.name}  (PRIORIDADE — Décio Freire)")
    print(f"   • {general_path.name}  (nossos sem categoria)")
    print(f"   • {lixo_path.name}  (lixo)")
    if len(duplicates_df) > 0:
        print(f"   • {dup_path.name}  (duplicatas)")
    if len(old_processes) > 0:
        print(f"   • {old_path.name}  (processos antigos)")
    print(f"   • categorias/  (1 arquivo por categoria)")
    print(f"   • {summary_path.name}  (resumo)")
    print(f"{'═' * 60}")