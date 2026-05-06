from __future__ import annotations

import pandas as pd
from pathlib import Path
import csv
from logger import setup_logger
from config import AppConfig

logger = setup_logger("audit_missing_detailed")

def audit_missing_detailed():
    """
    Investiga quais linhas específicas estão sendo puladas.
    """
    logger.info("🔍 AUDITORIA DETALHADA: LINHAS PULADAS")
    logger.info("=" * 80)
    
    config = AppConfig()
    webjur_path = Path(config.input_dir) / "Webjur1.csv"
    
    logger.info(f"📂 Procurando arquivo em: {webjur_path}")
    
    if not webjur_path.exists():
        logger.error(f"❌ Arquivo não encontrado: {webjur_path}")
        return
    
    logger.info(f"✅ Arquivo encontrado!")
    
    # 1. Contar linhas com raw CSV reader (aumentando o limite)
    logger.info(f"\n📊 Contando linhas com CSV reader...")
    
    csv.field_size_limit(int(1e8))  # ← AUMENTAR LIMITE PARA 100MB
    
    with open(webjur_path, 'r', encoding='latin-1') as f:
        reader = csv.reader(f, delimiter=';')
        total_csv = sum(1 for row in reader)
    
    logger.info(f"   ✅ Total com CSV reader: {total_csv} linhas")
    logger.info(f"   ✅ Total de dados (sem header): {total_csv - 1} linhas")
    
    # 2. Contar com Pandas
    logger.info(f"\n📊 Contando linhas com Pandas...")
    try:
        df_pandas = pd.read_csv(
            webjur_path, 
            sep=';', 
            encoding='latin-1',
            on_bad_lines='warn'
        )
        total_pandas = len(df_pandas)
        logger.info(f"   ✅ Total com Pandas: {total_pandas} linhas")
    except Exception as e:
        logger.error(f"   ❌ Erro ao ler com Pandas: {e}")
        return
    
    # 3. Diferença
    diferenca = total_csv - 1 - total_pandas
    pct_diff = (diferenca/(total_csv-1)*100) if total_csv > 1 else 0
    
    logger.info(f"\n⚠️  DIFERENÇA: {diferenca} linhas ({pct_diff:.2f}%)")
    
    if diferenca == 0:
        logger.info(f"✅ PERFEITO! Nenhuma linha foi perdida!")
    else:
        logger.warning(f"⚠️  {diferenca} linhas não foram lidas pelo Pandas")
    
    # 4. Verificar problemas de parsing
    logger.info(f"\n🔎 Verificando colunas com NaN:")
    
    cols_with_nan = df_pandas.columns[df_pandas.isna().any()].tolist()
    if len(cols_with_nan) > 0:
        for col in cols_with_nan:
            nan_count = df_pandas[col].isna().sum()
            logger.info(f"   {col}: {nan_count} valores NaN ({nan_count/len(df_pandas)*100:.2f}%)")
    else:
        logger.info(f"   ✅ Nenhuma coluna com NaN!")
    
    # 5. Verificar coluna de Número do Processo
    logger.info(f"\n🔎 Análise da coluna 'Número do Processo':")
    cnj_col = "Número do Processo"
    
    if cnj_col in df_pandas.columns:
        nan_cnj = df_pandas[cnj_col].isna().sum()
        logger.info(f"   CNJ vazios: {nan_cnj}")
        logger.info(f"   CNJ preenchidos: {len(df_pandas) - nan_cnj}")
        
        if nan_cnj > 0:
            logger.warning(f"   ⚠️  {nan_cnj} registros sem CNJ")
        
        # Amostra de CNJs válidos
        valid_cnj = df_pandas[df_pandas[cnj_col].notna()]['Número do Processo'].head(5)
        logger.info(f"   Amostra de CNJs válidos:")
        for cnj in valid_cnj:
            logger.info(f"      {cnj}")
    
    # 6. Tamanho das colunas
    logger.info(f"\n📏 Tamanho das colunas de texto:")
    
    for col in df_pandas.columns:
        if df_pandas[col].dtype == 'object':
            max_len = df_pandas[col].fillna('').str.len().max()
            avg_len = df_pandas[col].fillna('').str.len().mean()
            logger.info(f"   {col}: max={max_len}, avg={avg_len:.0f}")
    
    # 7. Exportar análise
    logger.info(f"\n📊 Exportando relatório...")
    output_path = Path("diagnostico_missing_detailed.xlsx")
    
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # Aba 1: Resumo
        resumo = pd.DataFrame([
            {"Métrica": "Total linhas no arquivo (com header)", "Valor": total_csv},
            {"Métrica": "Total de dados (sem header)", "Valor": total_csv - 1},
            {"Métrica": "Lido pelo Pandas", "Valor": total_pandas},
            {"Métrica": "DIFERENÇA", "Valor": diferenca},
            {"Métrica": "% de linhas perdidas", "Valor": f"{pct_diff:.2f}%"},
        ])
        resumo.to_excel(writer, sheet_name="Resumo", index=False)
        
        # Aba 2: Primeiras 100 linhas
        df_pandas.head(100).to_excel(writer, sheet_name="Primeiras 100", index=False)
        
        # Aba 3: Últimas 100 linhas
        df_pandas.tail(100).to_excel(writer, sheet_name="Últimas 100", index=False)
        
        # Aba 4: Análise de NaN
        nan_analysis = pd.DataFrame([
            {"Coluna": col, "NaN": df_pandas[col].isna().sum(), "% NaN": f"{df_pandas[col].isna().sum()/len(df_pandas)*100:.2f}%"}
            for col in df_pandas.columns
        ])
        nan_analysis.to_excel(writer, sheet_name="Análise NaN", index=False)
    
    logger.info(f"✅ Relatório salvo: {output_path}")
    
    # 8. Conclusão
    logger.info(f"\n{'='*80}")
    if diferenca == 0:
        logger.info(f"✅ CONCLUSÃO: O robô está lendo CORRETAMENTE!")
        logger.info(f"   Você informou 7.941, o arquivo tem {total_csv - 1}")
        logger.info(f"   Diferença: {7941 - (total_csv - 1)} (pode ser erro de contagem manual)")
    else:
        logger.warning(f"⚠️  CONCLUSÃO: {diferenca} linhas não foram lidas")
        logger.info(f"   Causa provável: Quebra de linha ou campos problemáticos")

if __name__ == "__main__":
    audit_missing_detailed()