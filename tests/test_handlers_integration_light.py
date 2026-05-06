import csv
from pathlib import Path

import pandas as pd


def test_append_execution_history_creates_csv_and_xlsx(handler, tmp_path):
    root_dir = tmp_path

    audit_dir = root_dir / "output" / "_auditoria" / "20260424_120000"
    audit_dir.mkdir(parents=True, exist_ok=True)

    log_file = root_dir / "logs_ui" / "ui_run_20260424_120000.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text("log teste", encoding="utf-8")

    row = {
        "timestamp": "20260424_120000",
        "status": "sucesso",
        "modo_diagnostico": "NAO",
        "fontes_com_arquivos": 2,
        "arquivos_selecionados": 3,
        "arquivos_preparados": 3,
        "arquivos_gerados": 8,
        "novos_arquivos": 2,
        "consolidados_gerados": 3,
        "linhas_sem_match": 10,
        "linhas_numero_puro": 4,
        "linhas_outro": 1,
        "pasta_auditoria": str(audit_dir),
        "log_execucao": str(log_file),
    }

    handler._append_execution_history(root_dir, row)

    history_dir = root_dir / "output" / "_historico_execucoes"
    history_csv = history_dir / "historico_execucoes.csv"
    history_xlsx = history_dir / "historico_execucoes.xlsx"

    assert history_csv.exists()
    assert history_xlsx.exists()

    with open(history_csv, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 1
    assert rows[0]["timestamp"] == "20260424_120000"
    assert rows[0]["status"] == "sucesso"

    df = pd.read_excel(history_xlsx, dtype=str, engine="openpyxl").fillna("")
    assert len(df) == 1
    assert df.iloc[0]["timestamp"] == "20260424_120000"
    assert df.iloc[0]["status"] == "sucesso"


def test_write_execution_comparison_creates_json(handler, tmp_path):
    audit_dir = tmp_path / "output" / "_auditoria" / "20260424_121000"
    audit_dir.mkdir(parents=True, exist_ok=True)

    comparison = {
        "execucao_atual": "20260424_121000",
        "execucao_anterior": "20260424_120000",
        "status_execucao_atual": "sucesso",
        "status_execucao_anterior": "sucesso",
        "comparacoes": {
            "arquivos_gerados": {
                "anterior": 8,
                "atual": 10,
                "delta": 2,
            }
        },
    }

    handler._write_execution_comparison(audit_dir, comparison)

    output_file = audit_dir / "comparativo_execucao_anterior.json"
    assert output_file.exists()

    saved = handler._load_json(output_file)
    assert saved["execucao_atual"] == "20260424_121000"
    assert saved["comparacoes"]["arquivos_gerados"]["delta"] == 2


def test_write_average_comparison_creates_json(handler, tmp_path):
    audit_dir = tmp_path / "output" / "_auditoria" / "20260424_122000"
    audit_dir.mkdir(parents=True, exist_ok=True)

    comparison = {
        "execucao_atual": "20260424_122000",
        "janela_referencia": 5,
        "quantidade_execucoes_referencia": 3,
        "execucoes_referencia": [
            "20260424_110000",
            "20260424_111000",
            "20260424_112000",
        ],
        "comparacoes": {
            "linhas_sem_match": {
                "media_referencia": 7.33,
                "atual": 10,
                "delta_vs_media": 2.67,
            }
        },
    }

    handler._write_average_comparison(audit_dir, comparison)

    output_file = audit_dir / "comparativo_media_ultimas_execucoes.json"
    assert output_file.exists()

    saved = handler._load_json(output_file)
    assert saved["quantidade_execucoes_referencia"] == 3
    assert saved["comparacoes"]["linhas_sem_match"]["delta_vs_media"] == 2.67


def test_write_regression_alerts_creates_json(handler, tmp_path):
    audit_dir = tmp_path / "output" / "_auditoria" / "20260424_123000"
    audit_dir.mkdir(parents=True, exist_ok=True)

    alerts = {
        "quantidade_alertas": 2,
        "alertas": [
            {
                "tipo": "aumento_sem_match_vs_anterior",
                "mensagem": "Aumento de sem_match em 5 linha(s) em relação à execução anterior."
            },
            {
                "tipo": "queda_arquivos_gerados_vs_media",
                "mensagem": "Arquivos gerados estão 2.50 abaixo da média recente."
            },
        ],
        "texto_resumo": "• alerta 1\n• alerta 2",
        "considera_execucao_anterior": True,
        "considera_media_recente": True,
    }

    handler._write_regression_alerts(audit_dir, alerts)

    output_file = audit_dir / "alertas_execucao.json"
    assert output_file.exists()

    saved = handler._load_json(output_file)
    assert saved["quantidade_alertas"] == 2
    assert len(saved["alertas"]) == 2
    assert saved["considera_media_recente"] is True


def test_write_execution_audit_creates_main_audit_files(handler, tmp_path):
    audit_dir = tmp_path / "output" / "_auditoria" / "20260424_124000"
    audit_dir.mkdir(parents=True, exist_ok=True)

    log_file = tmp_path / "logs_ui" / "ui_run_20260424_124000.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text("log teste", encoding="utf-8")

    selected_files = {
        "legalone": ["C:/fake/Base LO.xlsx"],
        "webjur": ["C:/fake/Webjur1.csv"],
        "dw": [],
        "painel": [],
        "modo_legalone_intimacoes": [],
    }

    prepared_files = [
        tmp_path / "input" / "Base LO.xlsx",
        tmp_path / "input" / "Webjur1.csv",
    ]
    for file in prepared_files:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("dummy", encoding="utf-8")

    output_files = [
        tmp_path / "output" / "resultado1.xlsx",
        tmp_path / "output" / "resultado2.xlsx",
    ]
    for file in output_files:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("dummy", encoding="utf-8")

    handler._write_execution_audit(
        audit_dir=audit_dir,
        timestamp="20260424_124000",
        diagnostic_mode=False,
        selected_files=selected_files,
        prepared_files=prepared_files,
        output_files=output_files,
        log_file=log_file,
        status="sucesso",
        return_code=0,
    )

    resumo = audit_dir / "resumo_execucao.json"
    fontes = audit_dir / "fontes_utilizadas.json"
    saida = audit_dir / "arquivos_saida.json"

    assert resumo.exists()
    assert fontes.exists()
    assert saida.exists()

    resumo_data = handler._load_json(resumo)
    fontes_data = handler._load_json(fontes)
    saida_data = handler._load_json(saida)

    assert resumo_data["status"] == "sucesso"
    assert resumo_data["arquivos_preparados"] == 2
    assert resumo_data["arquivos_saida_xlsx"] == 2

    assert fontes_data["legalone"]["count"] == 1
    assert fontes_data["webjur"]["count"] == 1

    assert len(saida_data["output_files"]) == 2