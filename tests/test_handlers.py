import csv
from pathlib import Path

from ui.handlers import ProcessHandler


def make_handler(logs=None, completed=None):
    if logs is None:
        logs = []

    if completed is None:
        completed = []

    def callback_progress(value):
        return None

    def callback_status(text):
        return None

    def callback_log(message, tag="info"):
        logs.append((message, tag))

    def callback_complete(result):
        completed.append(result)

    handler = ProcessHandler(
        callback_progress=callback_progress,
        callback_status=callback_status,
        callback_log=callback_log,
        callback_complete=callback_complete,
    )
    return handler, logs, completed


def test_safe_log_calls_callback_and_writes_file(tmp_path):
    handler, logs, _ = make_handler()

    log_file = tmp_path / "execucao.log"

    handler._safe_log("mensagem de teste", "warning", log_file)

    assert logs == [("mensagem de teste", "warning")]
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "mensagem de teste" in content


def test_load_execution_history_rows_returns_empty_when_file_does_not_exist(tmp_path):
    handler, _, _ = make_handler()

    result = handler._load_execution_history_rows(tmp_path)

    assert result == []


def test_load_execution_history_rows_reads_existing_csv(tmp_path):
    handler, _, _ = make_handler()

    history_dir = tmp_path / "output" / "_historico_execucoes"
    history_dir.mkdir(parents=True)

    history_file = history_dir / "historico_execucoes.csv"

    with open(history_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=handler.HISTORY_FIELDS)
        writer.writeheader()
        writer.writerow({
            "timestamp": "20260424_100000",
            "status": "sucesso",
            "modo_diagnostico": "NAO",
            "fontes_com_arquivos": "2",
            "arquivos_selecionados": "2",
            "arquivos_preparados": "2",
            "arquivos_gerados": "4",
            "novos_arquivos": "2",
            "consolidados_gerados": "2",
            "linhas_sem_match": "10",
            "linhas_numero_puro": "1",
            "linhas_outro": "0",
            "pasta_auditoria": "audit/1",
            "log_execucao": "logs/1.log",
        })

    result = handler._load_execution_history_rows(tmp_path)

    assert len(result) == 1
    assert result[0]["timestamp"] == "20260424_100000"
    assert result[0]["status"] == "sucesso"


def test_append_execution_history_creates_csv_and_excel(tmp_path):
    handler, logs, _ = make_handler()

    row = {
        "timestamp": "20260424_100000",
        "status": "sucesso",
        "modo_diagnostico": "NAO",
        "fontes_com_arquivos": 2,
        "arquivos_selecionados": 2,
        "arquivos_preparados": 2,
        "arquivos_gerados": 4,
        "novos_arquivos": 2,
        "consolidados_gerados": 2,
        "linhas_sem_match": 10,
        "linhas_numero_puro": 1,
        "linhas_outro": 0,
        "pasta_auditoria": "audit/1",
        "log_execucao": "logs/1.log",
    }

    handler._append_execution_history(tmp_path, row)

    history_dir = tmp_path / "output" / "_historico_execucoes"
    csv_file = history_dir / "historico_execucoes.csv"
    xlsx_file = history_dir / "historico_execucoes.xlsx"

    assert csv_file.exists()
    assert xlsx_file.exists()

    content = csv_file.read_text(encoding="utf-8-sig")
    assert "20260424_100000" in content
    assert "sucesso" in content

    assert any("Histórico atualizado" in msg for msg, _ in logs)


def test_write_execution_audit_creates_expected_json_files(tmp_path):
    handler, _, _ = make_handler()

    audit_dir = tmp_path / "audit"
    log_file = tmp_path / "execucao.log"

    selected_files = {
        "legalone": ["C:/tmp/legalone.csv"],
        "webjur": ["C:/tmp/webjur.csv"],
        "dw": [],
        "painel": [],
    }

    prepared_files = [Path("input/legalone.csv"), Path("input/webjur.csv")]
    output_files = [Path("output/a.xlsx"), Path("output/b.xlsx")]

    handler._write_execution_audit(
        audit_dir=audit_dir,
        timestamp="20260424_120000",
        diagnostic_mode=False,
        selected_files=selected_files,
        prepared_files=prepared_files,
        output_files=output_files,
        log_file=log_file,
        status="sucesso",
        return_code=0,
    )

    assert (audit_dir / "resumo_execucao.json").exists()
    assert (audit_dir / "fontes_utilizadas.json").exists()
    assert (audit_dir / "arquivos_saida.json").exists()


def test_persist_history_and_comparisons_calls_expected_steps(tmp_path, monkeypatch):
    handler, _, _ = make_handler()

    calls = []

    history_row = {
        "timestamp": "20260424_120000",
        "status": "sucesso",
    }

    def fake_append_execution_history(root_dir, row, log_file=None):
        calls.append(("append", row["timestamp"]))

    def fake_load_execution_history_rows(root_dir):
        calls.append(("load_history", str(root_dir)))
        return [
            {"timestamp": "20260424_110000", "status": "sucesso"},
            {"timestamp": "20260424_120000", "status": "sucesso"},
        ]

    def fake_find_previous_history_row(rows, timestamp):
        calls.append(("find_previous", timestamp))
        return {"timestamp": "20260424_110000", "status": "sucesso"}

    def fake_resolve_average_reference_rows(rows, timestamp):
        calls.append(("resolve_average_reference", timestamp))
        return ([{"timestamp": "20260424_110000", "status": "sucesso"}], "ultimas_execucoes_com_sucesso")

    def fake_build_execution_comparison(current_row, previous_row):
        calls.append(("build_execution_comparison", current_row["timestamp"]))
        return {"execucao_anterior": "20260424_110000", "comparacoes": {}}

    def fake_build_average_comparison(current_row, avg_rows, avg_criteria):
        calls.append(("build_average_comparison", avg_criteria))
        return {"quantidade_execucoes_referencia": 1, "comparacoes": {}}

    def fake_build_regression_alerts(comparison, average_comparison):
        calls.append(("build_regression_alerts", None))
        return {"quantidade_alertas": 0, "texto_resumo": "Nenhum alerta"}

    def fake_write_execution_comparison(audit_dir, comparison, log_file=None):
        calls.append(("write_execution_comparison", str(audit_dir)))

    def fake_write_average_comparison(audit_dir, comparison, log_file=None):
        calls.append(("write_average_comparison", str(audit_dir)))

    def fake_write_regression_alerts(audit_dir, alerts, log_file=None):
        calls.append(("write_regression_alerts", str(audit_dir)))

    monkeypatch.setattr(handler, "_append_execution_history", fake_append_execution_history)
    monkeypatch.setattr(handler, "_load_execution_history_rows", fake_load_execution_history_rows)
    monkeypatch.setattr(handler, "_find_previous_history_row", fake_find_previous_history_row)
    monkeypatch.setattr(handler, "_resolve_average_reference_rows", fake_resolve_average_reference_rows)
    monkeypatch.setattr(handler, "_build_execution_comparison", fake_build_execution_comparison)
    monkeypatch.setattr(handler, "_build_average_comparison", fake_build_average_comparison)
    monkeypatch.setattr(handler, "_build_regression_alerts", fake_build_regression_alerts)
    monkeypatch.setattr(handler, "_write_execution_comparison", fake_write_execution_comparison)
    monkeypatch.setattr(handler, "_write_average_comparison", fake_write_average_comparison)
    monkeypatch.setattr(handler, "_write_regression_alerts", fake_write_regression_alerts)

    result = handler._persist_history_and_comparisons(
        root_dir=tmp_path,
        audit_dir=tmp_path / "audit",
        history_row=history_row,
    )

    assert result["comparison"]["execucao_anterior"] == "20260424_110000"
    assert result["average_comparison"]["quantidade_execucoes_referencia"] == 1
    assert result["alerts"]["quantidade_alertas"] == 0

    expected_steps = {
        "append",
        "load_history",
        "find_previous",
        "resolve_average_reference",
        "build_execution_comparison",
        "build_average_comparison",
        "build_regression_alerts",
        "write_execution_comparison",
        "write_average_comparison",
        "write_regression_alerts",
    }

    assert expected_steps.issubset({name for name, _ in calls})


def test_build_success_result_summary_returns_expected_keys(tmp_path):
    handler, _, _ = make_handler()

    selected_files = {
        "legalone": ["legalone.csv"],
        "webjur": ["webjur.csv"],
        "dw": [],
        "painel": [],
    }

    prepared_files = [Path("input/legalone.csv"), Path("input/webjur.csv")]
    after_files = [Path("output/a.xlsx"), Path("output/b.xlsx")]
    new_files = [Path("output/b.xlsx")]

    consolidated_ui = {
        "Consolidados gerados": 2,
        "Linhas consolidadas - sem_match": 10,
        "Linhas consolidadas - numero_puro": 2,
        "Linhas consolidadas - outro": 1,
    }

    health_summary = {
        "Saúde da execução": "Saudável",
        "Tendência do sem_match": "Estável/Melhorando",
        "Tendência dos arquivos gerados": "Estável/Melhorando",
        "Nível de atenção": "Baixo",
    }

    comparison_ui = {
        "Δ Arquivos gerados": "+1",
        "Δ Consolidados gerados": "0",
        "Δ Linhas sem_match": "-1",
    }

    average_comparison_ui = {
        "Δ vs média - sem_match": "-0.50",
        "Δ vs média - arquivos gerados": "+1.00",
    }

    alerts = {
        "quantidade_alertas": 0,
        "texto_resumo": "Nenhum alerta",
        "contagem_por_severidade": {
            "alta": 0,
            "media": 0,
            "baixa": 0,
        },
    }

    result = handler._build_success_result_summary(
        diagnostic_mode=False,
        selected_files=selected_files,
        prepared_files=prepared_files,
        after_files=after_files,
        new_files=new_files,
        consolidated_ui=consolidated_ui,
        health_summary=health_summary,
        comparison_ui=comparison_ui,
        average_comparison_ui=average_comparison_ui,
        alerts=alerts,
        avg_criteria="ultimas_execucoes_com_sucesso",
        audit_dir=tmp_path / "audit",
        log_file=tmp_path / "execucao.log",
    )

    assert result["Status"] == "✓ Concluído"
    assert result["Modo diagnóstico"] == "NÃO"
    assert result["Saúde da execução"] == "Saudável"
    assert result["Quantidade de alertas"] == 0
    assert result["Arquivos preparados"] == 2
    assert result["Arquivos gerados"] == 2
    assert result["Novos arquivos"] == 1
    assert "Pasta da auditoria" in result
    assert "Log da execução" in result


def test_handle_non_success_completion_without_output_audits_calls_expected_steps(tmp_path, monkeypatch):
    handler, _, completed = make_handler()

    calls = []

    def fake_write_execution_audit(**kwargs):
        calls.append("write_execution_audit")

    def fake_build_execution_history_row(**kwargs):
        calls.append("build_execution_history_row")
        return {
            "timestamp": kwargs["timestamp"],
            "status": kwargs["status"],
        }

    def fake_persist_history_and_comparisons(root_dir, audit_dir, history_row, log_file=None):
        calls.append("persist_history_and_comparisons")
        return {}

    monkeypatch.setattr(handler, "_write_execution_audit", fake_write_execution_audit)
    monkeypatch.setattr(handler, "_build_execution_history_row", fake_build_execution_history_row)
    monkeypatch.setattr(handler, "_persist_history_and_comparisons", fake_persist_history_and_comparisons)

    handler._handle_non_success_completion(
        root_dir=tmp_path,
        audit_dir=tmp_path / "audit",
        timestamp="20260424_120000",
        diagnostic_mode=False,
        selected_files={"legalone": ["a.csv"]},
        prepared_files=[],
        output_files=[],
        new_files=[],
        consolidated_ui={"Consolidados gerados": 0},
        log_file=tmp_path / "execucao.log",
        status="erro_timeout",
        return_code=None,
        write_output_audits=False,
    )

    assert "write_execution_audit" in calls
    assert "build_execution_history_row" in calls
    assert "persist_history_and_comparisons" in calls
    assert completed == [None]


def test_handle_non_success_completion_with_output_audits_calls_expected_steps(tmp_path, monkeypatch):
    handler, _, completed = make_handler()

    calls = []

    def fake_write_execution_audit(**kwargs):
        calls.append("write_execution_audit")

    def fake_write_output_audit_files(**kwargs):
        calls.append("write_output_audit_files")

    def fake_write_consolidated_output_audits(**kwargs):
        calls.append("write_consolidated_output_audits")
        return {
            "sem_match": {
                "linhas_consolidadas": 10,
                "arquivo_saida": "audit/sem_match.xlsx",
            }
        }

    def fake_build_consolidated_ui_summary(summary):
        calls.append("build_consolidated_ui_summary")
        return {
            "Consolidados gerados": 1,
            "Linhas consolidadas - sem_match": 10,
            "Linhas consolidadas - numero_puro": 0,
            "Linhas consolidadas - outro": 0,
        }

    def fake_build_execution_history_row(**kwargs):
        calls.append("build_execution_history_row")
        return {
            "timestamp": kwargs["timestamp"],
            "status": kwargs["status"],
        }

    def fake_persist_history_and_comparisons(root_dir, audit_dir, history_row, log_file=None):
        calls.append("persist_history_and_comparisons")
        return {}

    monkeypatch.setattr(handler, "_write_execution_audit", fake_write_execution_audit)
    monkeypatch.setattr(handler, "_write_output_audit_files", fake_write_output_audit_files)
    monkeypatch.setattr(handler, "_write_consolidated_output_audits", fake_write_consolidated_output_audits)
    monkeypatch.setattr(handler, "_build_consolidated_ui_summary", fake_build_consolidated_ui_summary)
    monkeypatch.setattr(handler, "_build_execution_history_row", fake_build_execution_history_row)
    monkeypatch.setattr(handler, "_persist_history_and_comparisons", fake_persist_history_and_comparisons)

    handler._handle_non_success_completion(
        root_dir=tmp_path,
        audit_dir=tmp_path / "audit",
        timestamp="20260424_120000",
        diagnostic_mode=False,
        selected_files={"legalone": ["a.csv"]},
        prepared_files=[],
        output_files=[tmp_path / "output.xlsx"],
        new_files=[tmp_path / "output.xlsx"],
        consolidated_ui={"Consolidados gerados": 0},
        log_file=tmp_path / "execucao.log",
        status="erro_return_code",
        return_code=1,
        write_output_audits=True,
        output_dir=tmp_path / "output",
    )

    assert "write_execution_audit" in calls
    assert "write_output_audit_files" in calls
    assert "write_consolidated_output_audits" in calls
    assert "build_consolidated_ui_summary" in calls
    assert "build_execution_history_row" in calls
    assert "persist_history_and_comparisons" in calls
    assert completed == [None]