from pathlib import Path


def test_write_execution_markdown_summary_creates_markdown_file(handler, tmp_path):
    audit_dir = tmp_path / "output" / "_auditoria" / "20260424_130000"
    audit_dir.mkdir(parents=True, exist_ok=True)

    result_summary = {
        "Status": "✓ Concluído",
        "Modo diagnóstico": "NÃO",
        "Saúde da execução": "Saudável",
        "Nível de atenção": "Baixo",
        "Quantidade de alertas": 2,
        "Alertas alta severidade": 1,
        "Alertas média severidade": 1,
        "Alertas baixa severidade": 0,
        "Critério da média recente": "ultimas_execucoes_com_sucesso",
        "Δ Arquivos gerados": "+2",
        "Δ Consolidados gerados": "0",
        "Δ Linhas sem_match": "-1",
        "Δ vs média - sem_match": "-0.50",
        "Δ vs média - arquivos gerados": "+1.00",
        "Fontes com arquivos preparados": 2,
        "Arquivos selecionados": 3,
        "Arquivos preparados": 3,
        "Arquivos gerados": 8,
        "Novos arquivos": 2,
        "Consolidados gerados": 3,
        "Fontes informadas": "Base Legal One, WebJur",
        "Fontes ausentes": "DW, Painel",
        "Resumo por fonte": "Base Legal One: 1 arquivo(s)\nWebJur: 2 arquivo(s)",
        "Linhas consolidadas - sem_match": 10,
        "Linhas consolidadas - numero_puro": 4,
        "Linhas consolidadas - outro": 1,
        "Alertas de regressão": "• [ALTA] sem_match acima da média recente",
        "Localização": "output/",
        "Pasta da auditoria": str(audit_dir),
        "Log da execução": str(tmp_path / "logs_ui" / "ui_run_20260424_130000.log"),
    }

    handler._write_execution_markdown_summary(audit_dir, result_summary)

    output_file = audit_dir / "resumo_execucao.md"
    assert output_file.exists()

    content = output_file.read_text(encoding="utf-8")

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
    assert "Saudável" in content
    assert "ultimas_execucoes_com_sucesso" in content
    assert "Base Legal One, WebJur" in content
    assert "• [ALTA] sem_match acima da média recente" in content


def test_write_execution_markdown_summary_handles_missing_fields(handler, tmp_path):
    audit_dir = tmp_path / "output" / "_auditoria" / "20260424_131000"
    audit_dir.mkdir(parents=True, exist_ok=True)

    result_summary = {
        "Status": "✓ Concluído",
    }

    handler._write_execution_markdown_summary(audit_dir, result_summary)

    output_file = audit_dir / "resumo_execucao.md"
    assert output_file.exists()

    content = output_file.read_text(encoding="utf-8")

    assert "# Resumo da Execução" in content
    assert "**Status:** ✓ Concluído" in content
    assert "**Modo diagnóstico:** -" in content
    assert "**Saúde da execução:** -" in content
    assert "**Log da execução:** -" in content