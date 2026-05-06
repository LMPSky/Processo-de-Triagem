from __future__ import annotations

from pathlib import Path
from datetime import datetime
import re
import pandas as pd
from tqdm import tqdm

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
from classifiers.common import (
    rename_output_columns,
    truncate_text_column,
    sanitize_sheet_name,
    safe_filename,
)
from classifiers.trabalhista import classify_trabalhista_text
from classifiers.civel import classify_civel_record
from reporting.summary import export_summary_excel
from logger import setup_logger, log_classification_stats, log_matching_results, log_confidence_distribution

_MAX_TEXT_LENGTH = 500

TRTs_validos = {f"{i:02d}" for i in range(1, 25)}


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


def is_trabalhista(cnj: str) -> bool:
    m = re.match(r"^\d{7}-\d{2}\.\d{4}\.(\d)\.(\d{2})\.\d{4}$", cnj)
    if not m:
        return False
    j, tt = m.group(1), m.group(2)
    return j == "5" and tt in TRTs_validos


def is_trabalhista_custom(row) -> bool:
    fonte = str(row.get("_fonte") or "").strip().upper()
    if fonte in {"STJ", "STF"}:
        return False
    return is_trabalhista(row.get("cnj", ""))

    # ===================== ANÁLISE TRABALHISTA BRUTA =====================
    from reporting.summary import export_trabalhista_analysis
    
    export_trabalhista_analysis(
        summary_path=summary_path,
        sem_match_trab=sem_match_trab,
    )
    logger.info(f"✅ Análise trabalhista adicionada ao resumo")


def run_matching(config: AppConfig) -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger = setup_logger("matcher")
    
    logger.info("🚀 INICIANDO PROCESSO DE TRIAGEM")

    print("═" * 60)
    print("📂 Lendo fonte: LEGAL ONE")
    legalone_df = read_source(config.legalone, config.input_dir)
    logger.info(f"Legal One: {len(legalone_df)} linhas lidas")
    print(f"   → {len(legalone_df)} linhas no Legal One")

    extra_cols = config.legalone.extra_match_columns
    legalone_pool = _build_legalone_pool(legalone_df, extra_cols)
    logger.info(f"Legal One: {len(legalone_pool)} identificadores no pool")
    print(f"   → {len(legalone_pool)} identificadores únicos no pool de comparação")

    print("\n" + "═" * 60)
    external_df = read_all_external(config)
    logger.info(f"Bases externas: {len(external_df)} linhas lidas (antes de dedup)")
    print(f"\n   → {len(external_df)} linhas totais nas bases externas")

    print("\n" + "═" * 60)
    print("📋 Classificando tipos de número...")
    external_df = add_number_classification(external_df)

    print("\n" + "═" * 60)
    print("📋 Analisando presença em múltiplas fontes...")
    external_df = enrich_with_source_info(external_df)

    print("\n" + "═" * 60)
    print("📋 Removendo duplicatas...")
    external_df, duplicates_df = remove_duplicates(external_df)
    logger.info(f"Duplicatas removidas: {len(duplicates_df)}")

    print("\n" + "═" * 60)
    print("📋 Extraindo detalhes dos CNJs (UF, Ramo, Ano)...")
    external_df = add_cnj_details(external_df)

    print("\n" + "═" * 60)
    print("📋 Validando dígito verificador dos CNJs...")
    external_df = add_cnj_validation(external_df)

    print("\n" + "═" * 60)
    print("📋 Verificando idade dos processos...")
    external_df = add_age_flag(external_df, cutoff_year=2015)

    print("\n" + "═" * 60)
    print("🔍 Comparando com Legal One...")
    tqdm.pandas(desc="   🔍 Matching")
    external_df["match_legalone"] = external_df["cnj"].progress_apply(
        lambda x: _check_match(x, legalone_pool)
    )

    sem_match = external_df[~external_df["match_legalone"]].copy()
    com_match = external_df[external_df["match_legalone"]].copy()

    logger.info(f"Matching: {len(sem_match)} SEM MATCH, {len(com_match)} COM MATCH")
    print(f"   ➡️ SEM MATCH total:  {len(sem_match)}")
    print(f"   ➡️ COM MATCH (descartados): {len(com_match)}")

    sem_match["is_trabalhista"] = sem_match.apply(is_trabalhista_custom, axis=1)
    sem_match_trab = sem_match[sem_match["is_trabalhista"]].copy()
    sem_match_civel = sem_match[~sem_match["is_trabalhista"]].copy()

    log_matching_results(logger, len(sem_match_trab), len(sem_match_civel), len(com_match), len(external_df))
    print(f"   ➡️ Trabalhista SEM MATCH: {len(sem_match_trab)}")
    print(f"   ➡️ Cível SEM MATCH:      {len(sem_match_civel)}")

    out = Path(config.output_dir)
    trab_dir = out / "Trabalhista"
    trab_dir.mkdir(exist_ok=True, parents=True)
    civel_dir = out / "Civel"
    civel_dir.mkdir(exist_ok=True, parents=True)

        # ===================== TRABALHISTA =====================
    if not sem_match_trab.empty:
        logger.info("📋 INICIANDO CLASSIFICAÇÃO TRABALHISTA")
        
        # ✅ NOVO: Exportar BRUTO (antes de categorizar)
        trab_bruto_path = trab_dir / f"sem_match_trab_bruto_{timestamp}.xlsx"
        trab_bruto_export = rename_output_columns(truncate_text_column(sem_match_trab.copy(), _MAX_TEXT_LENGTH))
        trab_bruto_export.to_excel(
            trab_bruto_path,
            index=False,
            sheet_name=sanitize_sheet_name("Bruto"),
            engine="openpyxl",
        )
        logger.info(f"✅ Exportado BRUTO: {trab_bruto_path.name} ({len(sem_match_trab)} registros)")
        print(f"✅ Exportado BRUTO (sem filtro): {trab_bruto_path.name}")
        
        # ✅ Agora sim, categorizar
        sem_match_trab["_categoria"] = sem_match_trab["_texto"].apply(classify_trabalhista_text)
        logger.info("✅ Classificação TRABALHISTA concluída")

        print("\nCategorias atribuídas (value_counts) - Trabalhista:")
        print(sem_match_trab["_categoria"].value_counts(dropna=False))
        log_classification_stats(logger, sem_match_trab, "TRABALHISTA", "_categoria")

        exemplos_nao_classificados = sem_match_trab[sem_match_trab["_categoria"].isna()]
        if len(exemplos_nao_classificados) > 0:
            print("\nExemplos de textos trabalhistas não classificados:")
            print(
                exemplos_nao_classificados[["_texto"]].sample(
                    min(10, len(exemplos_nao_classificados)), random_state=100
                )
            )

        decio_df = sem_match_trab[sem_match_trab["_categoria"] == "Décio Freire"].copy()
        other_categorized = sem_match_trab[
            (sem_match_trab["_categoria"].notna()) & (sem_match_trab["_categoria"] != "Décio Freire")
        ].copy()
        no_category = sem_match_trab[sem_match_trab["_categoria"].isna()].copy()

        trab_prioridade_path = trab_dir / f"sem_match_trab_prioridade_{timestamp}.xlsx"
        if len(decio_df) > 0:
            decio_export = rename_output_columns(
                truncate_text_column(decio_df.drop(columns=["_categoria"], errors="ignore"), _MAX_TEXT_LENGTH)
            )
            decio_export.to_excel(
                trab_prioridade_path,
                index=False,
                sheet_name=sanitize_sheet_name("PRIORIDADE"),
                engine="openpyxl",
            )
            logger.info(f"✅ Exportado: {trab_prioridade_path.name} ({len(decio_df)} registros)")

        trab_categorias_dir = trab_dir / "sem_match_trab_categorias"
        trab_categorias_dir.mkdir(parents=True, exist_ok=True)

        if len(other_categorized) > 0:
            print(f"\n   📁 Arquivos TRABALHISTA por categoria:")
            for category in sorted(other_categorized["_categoria"].unique()):
                cat_df = other_categorized[other_categorized["_categoria"] == category].copy()
                safe_name = safe_filename(category)
                file_path = trab_categorias_dir / f"{safe_name}_{timestamp}.xlsx"
                cat_export = rename_output_columns(
                    truncate_text_column(cat_df.drop(columns=["_categoria"], errors="ignore"), _MAX_TEXT_LENGTH)
                )
                cat_export.to_excel(
                    file_path,
                    index=False,
                    sheet_name=sanitize_sheet_name(category),
                    engine="openpyxl",
                )
                logger.info(f"✅ Exportado: {file_path.name} ({len(cat_df)} registros)")
                print(f"      • {file_path.name}  ({len(cat_df)} linhas)")

        trab_todos_classificados_path = trab_categorias_dir / f"sem_match_trab_todos_classificados_{timestamp}.xlsx"
        all_categorized = pd.concat([decio_df, other_categorized], ignore_index=True)
        if len(all_categorized) > 0:
            all_export = rename_output_columns(
                truncate_text_column(all_categorized.drop(columns=["_categoria"], errors="ignore"), _MAX_TEXT_LENGTH)
            )
            all_export.to_excel(
                trab_todos_classificados_path,
                index=False,
                sheet_name=sanitize_sheet_name("classificados"),
                engine="openpyxl",
            )
            logger.info(f"✅ Exportado: {trab_todos_classificados_path.name} ({len(all_categorized)} registros)")

        trab_sem_cat_path = trab_dir / f"sem_match_trab_sem_categoria_{timestamp}.xlsx"
        if len(no_category) > 0:
            no_cat_export = rename_output_columns(
                truncate_text_column(no_category.drop(columns=["_categoria"], errors="ignore"), _MAX_TEXT_LENGTH)
            )
            no_cat_export.to_excel(
                trab_sem_cat_path,
                index=False,
                sheet_name=sanitize_sheet_name("sem_categoria"),
                engine="openpyxl",
            )
            logger.info(f"⚠️  Exportado: {trab_sem_cat_path.name} ({len(no_category)} registros sem categoria)")
    else:
        decio_df = pd.DataFrame()
        other_categorized = pd.DataFrame()
        no_category = pd.DataFrame()
        trab_bruto_path = trab_dir / f"sem_match_trab_bruto_{timestamp}.xlsx"
        trab_categorias_dir = trab_dir / "sem_match_trab_categorias"
        trab_prioridade_path = trab_dir / f"sem_match_trab_prioridade_{timestamp}.xlsx"
        trab_todos_classificados_path = trab_categorias_dir / f"sem_match_trab_todos_classificados_{timestamp}.xlsx"
        trab_sem_cat_path = trab_dir / f"sem_match_trab_sem_categoria_{timestamp}.xlsx"
        logger.info("⚠️  Nenhum processo trabalhista para classificar")

    # ===================== CÍVEL =====================
    if not sem_match_civel.empty:
        civel_class = sem_match_civel.apply(classify_civel_record, axis=1)
        sem_match_civel = pd.concat([sem_match_civel, civel_class], axis=1)
        logger.info("✅ Classificação CÍVEL concluída")

        print("\nCategorias atribuídas (value_counts) - Cível:")
        print(sem_match_civel["_categoria_civel"].value_counts(dropna=False))
        log_classification_stats(logger, sem_match_civel, "CÍVEL", "_categoria_civel")

        print("\nPrioridade cível (value_counts):")
        print(sem_match_civel["_prioridade_civel"].value_counts(dropna=False))

        print("\nConfiança cível (histograma simples):")
        print(sem_match_civel["_confidence_civel"].value_counts(dropna=False).sort_index())
        log_confidence_distribution(logger, sem_match_civel, "_confidence_civel")

        civel_path = civel_dir / f"sem_match_civel_{timestamp}.xlsx"
        civel_export = rename_output_columns(truncate_text_column(sem_match_civel.copy(), _MAX_TEXT_LENGTH))
        civel_export.to_excel(
            civel_path,
            index=False,
            sheet_name=sanitize_sheet_name("Civeis"),
            engine="openpyxl",
        )
        logger.info(f"✅ Exportado: {civel_path.name} ({len(sem_match_civel)} registros)")
        print(f"Arquivo cível exportado: {civel_path}")

        civel_prio_dir = civel_dir / "prioridade"
        civel_prio_dir.mkdir(parents=True, exist_ok=True)
        civel_prioridade_df = sem_match_civel[sem_match_civel["_prioridade_civel"] == "PRIORIDADE"].copy()
        civel_prioridade_path = civel_prio_dir / f"sem_match_civel_prioridade_{timestamp}.xlsx"
        if len(civel_prioridade_df) > 0:
            prio_export = rename_output_columns(truncate_text_column(civel_prioridade_df, _MAX_TEXT_LENGTH))
            prio_export.to_excel(
                civel_prioridade_path,
                index=False,
                sheet_name=sanitize_sheet_name("prioridade"),
                engine="openpyxl",
            )
            logger.info(f"✅ Exportado: {civel_prioridade_path.name} ({len(civel_prioridade_df)} registros prioritários)")

        civel_cat_dir = civel_dir / "sem_match_civel_categorias"
        civel_cat_dir.mkdir(parents=True, exist_ok=True)

        civeis_com_categoria = sem_match_civel[sem_match_civel["_categoria_civel"].notna()].copy()
        if len(civeis_com_categoria) > 0:
            print(f"\n   📁 Arquivos CÍVEL por categoria:")
            for category in sorted(civeis_com_categoria["_categoria_civel"].dropna().unique()):
                cat_df = civeis_com_categoria[civeis_com_categoria["_categoria_civel"] == category].copy()
                safe_name = safe_filename(category)
                file_path = civel_cat_dir / f"{safe_name}_{timestamp}.xlsx"
                cat_export = rename_output_columns(truncate_text_column(cat_df, _MAX_TEXT_LENGTH))
                cat_export.to_excel(
                    file_path,
                    index=False,
                    sheet_name=sanitize_sheet_name(safe_name),
                    engine="openpyxl",
                )
                logger.info(f"✅ Exportado: {file_path.name} ({len(cat_df)} registros)")
                print(f"      • {file_path.name}  ({len(cat_df)} linhas)")

        civel_sem_categoria = sem_match_civel[sem_match_civel["_categoria_civel"].isna()].copy()
        civel_sem_cat_path = civel_dir / f"sem_match_civel_sem_categoria_{timestamp}.xlsx"
        if len(civel_sem_categoria) > 0:
            civel_sem_cat_export = rename_output_columns(
                truncate_text_column(civel_sem_categoria, _MAX_TEXT_LENGTH)
            )
            civel_sem_cat_export.to_excel(
                civel_sem_cat_path,
                index=False,
                sheet_name=sanitize_sheet_name("sem_categoria"),
                engine="openpyxl",
            )
            logger.info(f"⚠️  Exportado: {civel_sem_cat_path.name} ({len(civel_sem_categoria)} registros sem categoria)")

    else:
        civel_path = civel_dir / f"sem_match_civel_{timestamp}.xlsx"
        civel_cat_dir = civel_dir / "sem_match_civel_categorias"
        civel_prio_dir = civel_dir / "prioridade"
        civel_prioridade_path = civel_prio_dir / f"sem_match_civel_prioridade_{timestamp}.xlsx"
        civel_sem_cat_path = civel_dir / f"sem_match_civel_sem_categoria_{timestamp}.xlsx"
        logger.info("⚠️  Nenhum processo cível para classificar")

    # ===================== COM MATCH =====================
    com_match_path = out / f"com_match_descartados_{timestamp}.xlsx"
    if len(com_match) > 0:
        com_match_export = rename_output_columns(truncate_text_column(com_match.copy(), _MAX_TEXT_LENGTH))
        com_match_export.to_excel(
            com_match_path,
            index=False,
            sheet_name=sanitize_sheet_name("descartados"),
            engine="openpyxl",
        )
        logger.info(f"✅ Exportado: {com_match_path.name} ({len(com_match)} registros descartados)")

    # ===================== RESUMO =====================
    summary_path = out / f"resumo_{timestamp}.txt"
    export_summary_excel(
        summary_path=summary_path,
        legalone_df=legalone_df,
        legalone_pool=legalone_pool,
        external_df=external_df,
        duplicates_df=duplicates_df,
        sem_match_trab=sem_match_trab,
        sem_match_civel=sem_match_civel,
        com_match=com_match,
        decio_df=decio_df,
        other_categorized=other_categorized,
        no_category=no_category,
    )
    logger.info(f"✅ Resumo exportado: {summary_path.with_suffix('.xlsx').name}")

    print(f"\n{'═' * 60}")
    print(f"📁 Arquivos gerados em: {out.resolve()}")
    if not sem_match_trab.empty:
        print(f"   • Prioridade (Décio Trabal): {trab_prioridade_path.name}")
        print(f"   • Categorias TRABALHISTA -> {trab_categorias_dir}")
        print(f"   • Todos classificados TRABALHISTA -> {trab_todos_classificados_path.name}")
        print(f"   • Sem categoria TRABALHISTA: {trab_sem_cat_path.name}")
    if not sem_match_civel.empty:
        print(f"   • CÍVEL exportado: {civel_path.name}")
        print(f"   • Categorias CÍVEL -> {civel_cat_dir}")
        print(f"   • Prioridade CÍVEL -> {civel_prioridade_path}")
        print(f"   • Sem categoria CÍVEL: {civel_sem_cat_path.name}")
    print(f"   • COM MATCH descartados: {com_match_path.name}")
    print(f"{'═' * 60}")
    
    logger.info("🎉 PROCESSO FINALIZADO COM SUCESSO")