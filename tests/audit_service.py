from pathlib import Path

import pandas as pd

from ui.audit_service import AuditService


def test_safe_write_json_creates_file(tmp_path):
    service = AuditService()

    output_file = tmp_path / "audit" / "data.json"
    payload = {"status": "ok", "total": 3}

    service.safe_write_json(output_file, payload)

    assert output_file.exists()
    assert output_file.read_text(encoding="utf-8")


def test_safe_write_csv_creates_file(tmp_path):
    service = AuditService()

    output_file = tmp_path / "audit" / "data.csv"
    rows = [
        {"col1": "a", "col2": "1"},
        {"col1": "b", "col2": "2"},
    ]

    service.safe_write_csv(output_file, rows, fieldnames=["col1", "col2"])

    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8-sig")
    assert "col1,col2" in content
    assert "a,1" in content
    assert "b,2" in content


def test_build_output_index_returns_expected_rows(tmp_path):
    service = AuditService()

    output_dir = tmp_path / "output"
    pasta = output_dir / "sem_match"
    pasta.mkdir(parents=True)

    file_path = pasta / "arquivo_teste.xlsx"
    file_path.write_bytes(b"conteudo")

    rows = service.build_output_index(output_dir, [file_path])

    assert len(rows) == 1
    assert rows[0]["arquivo"] == "arquivo_teste.xlsx"
    assert rows[0]["pasta_topo"] == "sem_match"
    assert rows[0]["tamanho_bytes"] == len(b"conteudo")


def test_build_output_summary_counts_by_folder_and_keyword(tmp_path):
    service = AuditService(
        output_keywords=["sem_match", "outro", "match"]
    )

    output_dir = tmp_path / "output"
    file1 = output_dir / "sem_match" / "arquivo_sem_match.xlsx"
    file2 = output_dir / "outro" / "arquivo_outro.xlsx"

    file1.parent.mkdir(parents=True)
    file2.parent.mkdir(parents=True)

    file1.write_bytes(b"a")
    file2.write_bytes(b"b")

    index_rows = service.build_output_index(output_dir, [file1, file2])
    summary = service.build_output_summary(index_rows, [file1], output_dir)

    assert summary["total_xlsx_output"] == 2
    assert summary["total_novos_xlsx"] == 1
    assert summary["contagem_por_pasta_topo"]["sem_match"] == 1
    assert summary["contagem_por_pasta_topo"]["outro"] == 1
    assert summary["contagem_por_palavra_chave"]["sem_match"] >= 1
    assert summary["contagem_por_palavra_chave"]["outro"] >= 1


def test_write_output_audit_files_creates_expected_files(tmp_path):
    service = AuditService()

    audit_dir = tmp_path / "audit"
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True)

    file1 = output_dir / "sem_match.xlsx"
    file1.write_bytes(b"abc")

    service.write_output_audit_files(
        audit_dir=audit_dir,
        output_dir=output_dir,
        output_files=[file1],
        new_files=[file1],
    )

    assert (audit_dir / "auditoria_arquivos_gerados.json").exists()
    assert (audit_dir / "auditoria_resumo_output.json").exists()
    assert (audit_dir / "auditoria_xlsx_index.csv").exists()


def test_group_output_files_by_keyword(tmp_path):
    service = AuditService(
        consolidated_audit_groups=["sem_match", "numero_puro", "outro"]
    )

    output_dir = tmp_path / "output"
    file1 = output_dir / "a" / "planilha_sem_match.xlsx"
    file2 = output_dir / "b" / "planilha_numero_puro.xlsx"
    file3 = output_dir / "c" / "planilha_outro.xlsx"

    for file_path in [file1, file2, file3]:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"x")

    grouped = service.group_output_files_by_keyword(output_dir, [file1, file2, file3])

    assert len(grouped["sem_match"]) == 1
    assert len(grouped["numero_puro"]) == 1
    assert len(grouped["outro"]) == 1


def test_build_consolidated_ui_summary_counts_generated_files():
    service = AuditService(
        consolidated_audit_groups=["sem_match", "numero_puro", "outro"]
    )

    consolidated_summary = {
        "sem_match": {
            "linhas_consolidadas": 10,
            "arquivo_saida": "audit/sem_match.xlsx",
        },
        "numero_puro": {
            "linhas_consolidadas": 4,
            "arquivo_saida": "audit/numero_puro.xlsx",
        },
        "outro": {
            "linhas_consolidadas": 0,
            "arquivo_saida": "",
        },
    }

    result = service.build_consolidated_ui_summary(consolidated_summary)

    assert result["Consolidados gerados"] == 2
    assert result["Linhas consolidadas - sem_match"] == 10
    assert result["Linhas consolidadas - numero_puro"] == 4
    assert result["Linhas consolidadas - outro"] == 0


def test_write_execution_comparison_creates_json(tmp_path):
    service = AuditService()

    audit_dir = tmp_path / "audit"
    payload = {"execucao_atual": "20260424_100000"}

    output_path = service.write_execution_comparison(audit_dir, payload)

    assert output_path.exists()
    assert output_path.name == "comparativo_execucao_anterior.json"


def test_write_average_comparison_creates_json(tmp_path):
    service = AuditService()

    audit_dir = tmp_path / "audit"
    payload = {"janela_referencia": 5}

    output_path = service.write_average_comparison(audit_dir, payload)

    assert output_path.exists()
    assert output_path.name == "comparativo_media_ultimas_execucoes.json"


def test_write_regression_alerts_creates_json(tmp_path):
    service = AuditService()

    audit_dir = tmp_path / "audit"
    payload = {"quantidade_alertas": 2}

    output_path = service.write_regression_alerts(audit_dir, payload)

    assert output_path.exists()
    assert output_path.name == "alertas_execucao.json"


def test_write_execution_markdown_summary_creates_markdown(tmp_path):
    service = AuditService()

    audit_dir = tmp_path / "audit"
    result_summary = {
        "Status": "✓ Concluído",
        "Modo diagnóstico": "NÃO",
        "Saúde da execução": "Saudável",
        "Nível de atenção": "Baixo",
        "Quantidade de alertas": 0,
        "Alertas alta severidade": 0,
        "Alertas média severidade": 0,
        "Alertas baixa severidade": 0,
        "Critério da média recente": "ultimas_execucoes_com_sucesso",
        "Δ Arquivos gerados": "+1",
        "Δ Consolidados gerados": "0",
        "Δ Linhas sem_match": "-1",
        "Δ vs média - sem_match": "-0.50",
        "Δ vs média - arquivos gerados": "+1.00",
        "Fontes com arquivos preparados": 2,
        "Arquivos selecionados": 2,
        "Arquivos preparados": 2,
        "Arquivos gerados": 4,
        "Novos arquivos": 2,
        "Consolidados gerados": 2,
        "Fontes informadas": "Legal One, WebJur",
        "Fontes ausentes": "DW, Painel",
        "Resumo por fonte": "Legal One: 1 arquivo(s)\nWebJur: 1 arquivo(s)",
        "Linhas consolidadas - sem_match": 10,
        "Linhas consolidadas - numero_puro": 2,
        "Linhas consolidadas - outro": 1,
        "Alertas de regressão": "Nenhum alerta",
        "Localização": "output/",
        "Pasta da auditoria": str(audit_dir),
        "Log da execução": "logs_ui/ui_run.log",
    }

    output_path = service.write_execution_markdown_summary(audit_dir, result_summary)

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "# Resumo da Execução" in content
    assert "## Identificação" in content
    assert "## Visão executiva" in content
    assert "## Comparativos" in content
    assert "## Volumetria" in content
    assert "## Fontes" in content
    assert "## Consolidados" in content
    assert "## Alertas" in content
    assert "## Caminhos" in content
    assert "✓ Concluído" in content


def test_build_consolidated_audit_excel_generates_xlsx(tmp_path):
    service = AuditService()

    audit_dir = tmp_path / "audit"
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True)

    source_file = output_dir / "sem_match_teste.xlsx"

    df = pd.DataFrame([
        {"coluna1": "a", "coluna2": "1"},
        {"coluna1": "b", "coluna2": "2"},
    ])
    df.to_excel(source_file, index=False, engine="openpyxl")

    metadata = service.build_consolidated_audit_excel(
        audit_dir=audit_dir,
        output_dir=output_dir,
        group_name="sem_match",
        files=[source_file],
    )

    assert metadata["grupo"] == "sem_match"
    assert metadata["arquivos_origem"] == 1
    assert metadata["linhas_consolidadas"] == 2
    assert metadata["arquivo_saida"]
    assert Path(metadata["arquivo_saida"]).exists()


def test_write_consolidated_summary_excel_creates_workbook(tmp_path):
    service = AuditService()

    audit_dir = tmp_path / "audit"
    summary = {
        "sem_match": {
            "arquivos_origem": 1,
            "linhas_consolidadas": 10,
            "arquivo_saida": "audit/sem_match.xlsx",
            "linhas_por_arquivo": {"origem1.xlsx": 10},
            "colunas": ["a", "b"],
        },
        "numero_puro": {
            "arquivos_origem": 1,
            "linhas_consolidadas": 4,
            "arquivo_saida": "audit/numero_puro.xlsx",
            "linhas_por_arquivo": {"origem2.xlsx": 4},
            "colunas": ["x", "y"],
        },
    }

    service.write_consolidated_summary_excel(audit_dir, summary)

    output_file = audit_dir / "auditoria_resumo_consolidados.xlsx"
    assert output_file.exists()


def test_write_consolidated_output_audits_creates_json_and_excel(tmp_path):
    service = AuditService(
        consolidated_audit_groups=["sem_match", "numero_puro", "outro"]
    )

    audit_dir = tmp_path / "audit"
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True)

    file1 = output_dir / "planilha_sem_match.xlsx"
    file2 = output_dir / "planilha_numero_puro.xlsx"

    pd.DataFrame([{"a": 1}]).to_excel(file1, index=False, engine="openpyxl")
    pd.DataFrame([{"b": 2}]).to_excel(file2, index=False, engine="openpyxl")

    summary = service.write_consolidated_output_audits(
        audit_dir=audit_dir,
        output_dir=output_dir,
        output_files=[file1, file2],
    )

    assert isinstance(summary, dict)
    assert (audit_dir / "auditoria_resumo_consolidados.json").exists()
    assert (audit_dir / "auditoria_resumo_consolidados.xlsx").exists()