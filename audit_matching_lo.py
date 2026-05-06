from __future__ import annotations

import pandas as pd
from pathlib import Path
from config import AppConfig
from reader import read_source, read_all_external
from filters import remove_duplicates
from number_extractor import extract_all_numbers, normalize_number
from logger import setup_logger

logger = setup_logger("audit_matching_lo")

def build_legalone_pool(legalone_df: pd.DataFrame, extra_columns: list[str]) -> set[str]:
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

def check_match(cnj_value: str, legalone_pool: set[str]) -> bool:
    numbers = extract_all_numbers(cnj_value)
    for num in numbers:
        if num in legalone_pool:
            return True
        if normalize_number(num) in legalone_pool:
            return True
    return False

def audit_matching():
    """
    Valida se os 565 matches com Legal One estão corretos.
    """
    config = AppConfig()
    
    logger.info("🔍 AUDITORIA: MATCHING COM LEGAL ONE")
    logger.info("=" * 70)
    
    # 1. Ler Legal One
    print("\n📂 Lendo Legal One...")
    legalone_df = read_source(config.legalone, config.input_dir)
    logger.info(f"📊 Legal One: {len(legalone_df)} processos")
    
    # 2. Construir pool
    print("🔨 Construindo pool de identificadores...")
    extra_cols = config.legalone.extra_match_columns
    legalone_pool = build_legalone_pool(legalone_df, extra_cols)
    logger.info(f"📊 Pool: {len(legalone_pool)} identificadores")
    
    # 3. Ler bases externas
    print("📂 Lendo bases externas...")
    external_df = read_all_external(config)
    external_df, _ = remove_duplicates(external_df)
    logger.info(f"📊 Bases externas (após dedup): {len(external_df)}")
    
    # 4. Fazer matching
    print("🔍 Fazendo matching...")
    external_df['match_lo'] = external_df['cnj'].apply(
        lambda x: check_match(x, legalone_pool)
    )
    
    com_match = external_df[external_df['match_lo']]
    sem_match = external_df[~external_df['match_lo']]
    
    logger.info(f"\n📊 Resultados do matching:")
    logger.info(f"   Com match: {len(com_match)} processos")
    logger.info(f"   Sem match: {len(sem_match)} processos")
    logger.info(f"   Taxa de match: {len(com_match)/len(external_df)*100:.2f}%")
    
    # 5. Análise por fonte
    logger.info(f"\n📊 Matching por fonte:")
    if '_fonte' in external_df.columns:
        for fonte in external_df['_fonte'].unique():
            fonte_df = external_df[external_df['_fonte'] == fonte]
            match_taxa = (fonte_df['match_lo'].sum() / len(fonte_df) * 100) if len(fonte_df) > 0 else 0
            logger.info(f"   {fonte}: {fonte_df['match_lo'].sum()}/{len(fonte_df)} ({match_taxa:.2f}%)")
    
    # 6. Exportar relatório
    logger.info(f"\n📊 Exportando relatório...")
    output_path = Path("diagnostico_matching_lo.xlsx")
    
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # Aba 1: Resumo
        resumo = pd.DataFrame([
            {"Métrica": "Total de processos", "Valor": len(external_df)},
            {"Métrica": "Com match na LO", "Valor": len(com_match)},
            {"Métrica": "Sem match", "Valor": len(sem_match)},
            {"Métrica": "Taxa de match", "Valor": f"{len(com_match)/len(external_df)*100:.2f}%"},
        ])
        resumo.to_excel(writer, sheet_name="Resumo", index=False)
        
        # Aba 2: Com match (amostra)
        cols = ["cnj", "_fonte", "_cliente", "_data"]
        cols = [c for c in cols if c in com_match.columns]
        com_match[cols].head(100).to_excel(
            writer,
            sheet_name="Com Match (amostra)",
            index=False
        )
        
        # Aba 3: Legal One vs Externas
        lo_cnj_sample = legalone_df[['cnj']].head(50)
        lo_cnj_sample.columns = ['CNJ LO']
        ext_cnj_match = com_match[['cnj']].head(50)
        ext_cnj_match.columns = ['CNJ Externo (com match)']
        
        # Não dá pra concatenar com índices diferentes, então salva separado
        lo_cnj_sample.to_excel(
            writer,
            sheet_name="Amostra LO",
            index=False
        )
        
        ext_cnj_match.to_excel(
            writer,
            sheet_name="Amostra Match",
            index=False
        )
    
    logger.info(f"✅ Relatório salvo: {output_path}")

if __name__ == "__main__":
    audit_matching()