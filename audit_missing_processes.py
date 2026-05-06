from __future__ import annotations

import pandas as pd
from pathlib import Path
from config import AppConfig
from reader import read_source, read_all_external
from logger import setup_logger

logger = setup_logger("audit_missing")

def audit_missing_records():
    """
    Investiga os 484 processos que entraram no WebJur 
    mas não foram lidos pelo robô.
    """
    config = AppConfig()
    
    logger.info("🔍 AUDITORIA: PROCESSOS PERDIDOS NA LEITURA")
    logger.info("=" * 70)
    
    # 1. Ler WebJur bruto (sem processamento)
    print("\n📂 Lendo WebJur bruto...")
    webjur_path = Path(config.input_dir) / "Webjur1.csv"
    
    try:
        # Tenta diferentes encodings
        for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
            try:
                webjur_raw = pd.read_csv(webjur_path, sep=";", encoding=encoding)
                logger.info(f"✅ Lido com encoding: {encoding}")
                break
            except:
                continue
        else:
            logger.error("❌ Não foi possível ler o arquivo com nenhum encoding")
            return
    except Exception as e:
        logger.error(f"❌ Erro ao ler WebJur: {e}")
        return
    
    total_webjur = len(webjur_raw)
    logger.info(f"📊 Total de linhas no WebJur: {total_webjur}")
    
    # 2. Ler pelo reader do robô
    print("📂 Lendo WebJur via reader do robô...")
    try:
        webjur_robot = read_source(config.webjur, config.input_dir)
        total_robot = len(webjur_robot)
        logger.info(f"📊 Total lido pelo robô: {total_robot}")
    except Exception as e:
        logger.error(f"❌ Erro ao ler via reader: {e}")
        return
    
    # 3. Investigar diferença
    diferenca = total_webjur - total_robot
    logger.info(f"\n⚠️  DIFERENÇA: {diferenca} processos ({diferenca/total_webjur*100:.2f}%)")
    
    # 4. Análise de colunas
    logger.info(f"\n📋 Análise de colunas:")
    logger.info(f"   Colunas no WebJur bruto: {list(webjur_raw.columns)}")
    logger.info(f"   Colunas após robô: {list(webjur_robot.columns)}")
    
    # 5. Procurar por NaN/valores vazios
    logger.info(f"\n🔎 Procurando registros problemáticos no WebJur bruto:")
    
    # Verificar linhas completamente vazias
    empty_rows = webjur_raw.dropna(how='all')
    logger.info(f"   Linhas completamente vazias: {len(webjur_raw) - len(empty_rows)}")
    
    # Verificar se CNJ está vazio
    cnj_col = config.webjur.cnj_column
    if cnj_col in webjur_raw.columns:
        empty_cnj = webjur_raw[webjur_raw[cnj_col].isna() | (webjur_raw[cnj_col] == "")]
        logger.info(f"   Linhas com CNJ vazio: {len(empty_cnj)}")
        
        if len(empty_cnj) > 0:
            logger.warning(f"   ⚠️  Exemplos de CNJ vazios:")
            print(empty_cnj.head(10))
    
    # 6. Verificar tamanho de arquivo
    file_size = webjur_path.stat().st_size
    logger.info(f"\n📏 Informações do arquivo:")
    logger.info(f"   Tamanho: {file_size / (1024*1024):.2f} MB")
    logger.info(f"   Linhas por MB: {total_webjur / (file_size / (1024*1024)):.0f}")
    
    # 7. Exportar relatório de diagnóstico
    logger.info(f"\n📊 Exportando diagnóstico...")
    output_path = Path("diagnostico_missing_processes.xlsx")
    
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # Aba 1: Resumo
        resumo = pd.DataFrame([
            {"Métrica": "Total no WebJur (bruto)", "Valor": total_webjur},
            {"Métrica": "Total lido pelo robô", "Valor": total_robot},
            {"Métrica": "Diferença", "Valor": diferenca},
            {"Métrica": "Percentual perdido", "Valor": f"{diferenca/total_webjur*100:.2f}%"},
        ])
        resumo.to_excel(writer, sheet_name="Resumo", index=False)
        
        # Aba 2: Primeiras linhas (pode ter problema de encoding)
        webjur_raw.head(20).to_excel(writer, sheet_name="Primeiras Linhas", index=False)
        
        # Aba 3: Últimas linhas
        webjur_raw.tail(20).to_excel(writer, sheet_name="Últimas Linhas", index=False)
        
        # Aba 4: Problemas potenciais
        if cnj_col in webjur_raw.columns:
            problemas = webjur_raw[webjur_raw[cnj_col].isna() | (webjur_raw[cnj_col] == "")].head(50)
            problemas.to_excel(writer, sheet_name="CNJ Vazios", index=False)
    
    logger.info(f"✅ Diagnóstico salvo: {output_path}")
    
    # 8. Hipóteses
    logger.info(f"\n💡 HIPÓTESES POSSÍVEIS:")
    logger.info(f"   1. Encoding do arquivo diferente")
    logger.info(f"   2. Linhas com CNJ inválido/vazio")
    logger.info(f"   3. Problema no separador (;)")
    logger.info(f"   4. Caracteres especiais causando erro de parse")
    logger.info(f"   5. Linhas corrompidas no meio do arquivo")

if __name__ == "__main__":
    audit_missing_records()