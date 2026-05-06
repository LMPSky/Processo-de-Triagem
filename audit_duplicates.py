from __future__ import annotations

import pandas as pd
from pathlib import Path
from config import AppConfig
from reader import read_source, read_all_external
from filters import remove_duplicates
from logger import setup_logger
from number_extractor import extract_all_numbers, normalize_number

logger = setup_logger("audit_duplicates")

def audit_duplicates():
    """
    Valida se as 1.744 duplicatas removidas estão corretas.
    """
    config = AppConfig()
    
    logger.info("🔍 AUDITORIA: DUPLICATAS REMOVIDAS")
    logger.info("=" * 70)
    
    # 1. Ler e processar
    print("\n📂 Lendo bases externas...")
    external_df = read_all_external(config)
    total_antes = len(external_df)
    logger.info(f"📊 Total antes de dedup: {total_antes}")
    
    # 2. Remover duplicatas
    print("🔄 Removendo duplicatas...")
    external_df_dedup, duplicates_df = remove_duplicates(external_df)
    total_dedup = len(duplicates_df)
    logger.info(f"📊 Duplicatas removidas: {total_dedup}")
    
    # 3. Análise das duplicatas
    logger.info(f"\n📊 Análise das duplicatas:")
    
    # Por CNJ
    if len(duplicates_df) > 0:
        cnj_counts = duplicates_df['cnj'].value_counts()
        logger.info(f"   CNJs únicos com duplicata: {len(cnj_counts)}")
        logger.info(f"   Máximo de duplicatas para um CNJ: {cnj_counts.max()}")
        logger.info(f"   Mínimo de duplicatas para um CNJ: {cnj_counts.min()}")
        
        # Top 10 CNJs mais duplicados
        logger.info(f"\n   Top 10 CNJs mais duplicados:")
        for cnj, count in cnj_counts.head(10).items():
            logger.info(f"      {cnj}: {count} duplicatas")
        
        # Por fonte
        logger.info(f"\n   Duplicatas por fonte:")
        if '_fonte' in duplicates_df.columns:
            fonte_counts = duplicates_df['_fonte'].value_counts()
            for fonte, count in fonte_counts.items():
                logger.info(f"      {fonte}: {count} duplicatas")
    
    # 4. Validação: as duplicatas são realmente duplicatas?
    logger.info(f"\n🔎 Validando qualidade das duplicatas:")
    
    sample_duplicates = duplicates_df.sample(min(10, len(duplicates_df)))
    for idx, row in sample_duplicates.iterrows():
        cnj = row['cnj']
        # Procurar registros do mesmo CNJ
        same_cnj = external_df[external_df['cnj'] == cnj]
        if len(same_cnj) > 1:
            logger.info(f"   ✅ CNJ {cnj}: {len(same_cnj)} registros encontrados")
        else:
            logger.warning(f"   ⚠️  CNJ {cnj}: Apenas 1 registro? Pode ser erro!")
    
    # 5. Exportar relatório
    logger.info(f"\n📊 Exportando relatório...")
    output_path = Path("diagnostico_duplicatas.xlsx")
    
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # Aba 1: Resumo
        resumo = pd.DataFrame([
            {"Métrica": "Total antes de dedup", "Valor": total_antes},
            {"Métrica": "Total duplicatas", "Valor": total_dedup},
            {"Métrica": "Taxa de duplicação", "Valor": f"{total_dedup/total_antes*100:.2f}%"},
            {"Métrica": "Após dedup", "Valor": len(external_df_dedup)},
        ])
        resumo.to_excel(writer, sheet_name="Resumo", index=False)
        
        # Aba 2: Top CNJs duplicados
        if len(duplicates_df) > 0:
            cnj_dup = duplicates_df['cnj'].value_counts().head(100).reset_index()
            cnj_dup.columns = ["CNJ", "Quantidade"]
            cnj_dup.to_excel(writer, sheet_name="Top CNJs Duplicados", index=False)
        
        # Aba 3: Amostra de duplicatas
        if len(duplicates_df) > 0:
            cols = ["cnj", "_fonte", "_cliente", "_data"]
            cols = [c for c in cols if c in duplicates_df.columns]
            duplicates_df[cols].head(100).to_excel(
                writer, 
                sheet_name="Amostra Duplicatas",
                index=False
            )
    
    logger.info(f"✅ Relatório salvo: {output_path}")

if __name__ == "__main__":
    audit_duplicates()