import subprocess
from pathlib import Path

from ui.handlers import ProcessHandler


def make_handler(logs=None, completed=None, progresses=None, statuses=None):
    if logs is None:
        logs = []

    if completed is None:
        completed = []

    if progresses is None:
        progresses = []

    if statuses is None:
        statuses = []

    def callback_progress(value):
        progresses.append(value)

    def callback_status(text):
        statuses.append(text)

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
    return handler, logs, completed, progresses, statuses


def test_process_handles_no_prepared_files(monkeypatch, tmp_path):
    handler, logs, completed, _, _ = make_handler()

    calls = []

    monkeypatch.setattr(handler, "_get_root_dir", lambda: tmp_path)

    def fake_copy_selected_inputs_snapshot(*args, **kwargs):
        calls.append("copy_selected_inputs_snapshot")

    def fake_remove_previous_internal_files(*args, **kwargs):
        calls.append("remove_previous_internal_files")

    def fake_prepare_selected_sources(selected_files, input_dir, log_file=None):
        calls.append("prepare_selected_sources")
        return []

    def fake_handle_non_success_completion(**kwargs):
        calls.append(("handle_non_success_completion", kwargs["status"]))
        handler.callback_complete(None)

    monkeypatch.setattr(handler, "_copy_selected_inputs_snapshot", fake_copy_selected_inputs_snapshot)
    monkeypatch.setattr(handler, "_remove_previous_internal_files", fake_remove_previous_internal_files)
    monkeypatch.setattr(handler, "_prepare_selected_sources", fake_prepare_selected_sources)
    monkeypatch.setattr(handler, "_handle_non_success_completion", fake_handle_non_success_completion)

    selected_files = {
        "legalone": ["arquivo.csv"],
        "webjur": [],
        "dw": [],
        "painel": [],
    }

    handler._process(selected_files, diagnostic_mode=False)

    assert "prepare_selected_sources" in calls
    assert ("handle_non_success_completion", "erro_sem_arquivos_preparados") in calls
    assert completed == [None]
    assert any("Nenhum arquivo foi preparado" in msg for msg, _ in logs)


def test_process_handles_subprocess_timeout(monkeypatch, tmp_path):
    handler, logs, completed, _, _ = make_handler()

    calls = []

    monkeypatch.setattr(handler, "_get_root_dir", lambda: tmp_path)

    def fake_copy_selected_inputs_snapshot(*args, **kwargs):
        return None

    def fake_remove_previous_internal_files(*args, **kwargs):
        return None

    def fake_prepare_selected_sources(selected_files, input_dir, log_file=None):
        return [input_dir / "legalone.csv"]

    def fake_subprocess_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="python main.py", timeout=600)

    def fake_handle_non_success_completion(**kwargs):
        calls.append(("handle_non_success_completion", kwargs["status"]))
        handler.callback_complete(None)

    monkeypatch.setattr(handler, "_copy_selected_inputs_snapshot", fake_copy_selected_inputs_snapshot)
    monkeypatch.setattr(handler, "_remove_previous_internal_files", fake_remove_previous_internal_files)
    monkeypatch.setattr(handler, "_prepare_selected_sources", fake_prepare_selected_sources)
    monkeypatch.setattr(subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(handler, "_handle_non_success_completion", fake_handle_non_success_completion)

    selected_files = {
        "legalone": ["arquivo.csv"],
        "webjur": [],
        "dw": [],
        "painel": [],
    }

    handler._process(selected_files, diagnostic_mode=False)

    assert ("handle_non_success_completion", "erro_timeout") in calls
    assert completed == [None]
    assert any("Timeout" in msg for msg, _ in logs)


def test_process_handles_subprocess_generic_exception(monkeypatch, tmp_path):
    handler, logs, completed, _, _ = make_handler()

    calls = []

    monkeypatch.setattr(handler, "_get_root_dir", lambda: tmp_path)

    def fake_copy_selected_inputs_snapshot(*args, **kwargs):
        return None

    def fake_remove_previous_internal_files(*args, **kwargs):
        return None

    def fake_prepare_selected_sources(selected_files, input_dir, log_file=None):
        return [input_dir / "legalone.csv"]

    def fake_subprocess_run(*args, **kwargs):
        raise RuntimeError("falha simulada")

    def fake_handle_non_success_completion(**kwargs):
        calls.append(("handle_non_success_completion", kwargs["status"]))
        handler.callback_complete(None)

    monkeypatch.setattr(handler, "_copy_selected_inputs_snapshot", fake_copy_selected_inputs_snapshot)
    monkeypatch.setattr(handler, "_remove_previous_internal_files", fake_remove_previous_internal_files)
    monkeypatch.setattr(handler, "_prepare_selected_sources", fake_prepare_selected_sources)
    monkeypatch.setattr(subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(handler, "_handle_non_success_completion", fake_handle_non_success_completion)

    selected_files = {
        "legalone": ["arquivo.csv"],
        "webjur": [],
        "dw": [],
        "painel": [],
    }

    handler._process(selected_files, diagnostic_mode=False)

    assert ("handle_non_success_completion", "erro_execucao_pipeline") in calls
    assert completed == [None]
    assert any("Erro ao executar main.py" in msg for msg, _ in logs)


def test_process_success_complete_flow(monkeypatch, tmp_path):
    handler, logs, completed, progresses, statuses = make_handler()

    root_dir = tmp_path
    input_dir = root_dir / "input"
    output_dir = root_dir / "output"
    logs_dir = root_dir / "logs_ui"

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    calls = []

    class FakeCompletedProcess:
        def __init__(self):
            self.returncode = 0
            self.stdout = "processamento finalizado"
            self.stderr = ""

    monkeypatch.setattr(handler, "_get_root_dir", lambda: root_dir)

    def fake_copy_selected_inputs_snapshot(*args, **kwargs):
        calls.append("copy_selected_inputs_snapshot")

    def fake_remove_previous_internal_files(*args, **kwargs):
        calls.append("remove_previous_internal_files")

    def fake_prepare_selected_sources(selected_files, input_dir, log_file=None):
        calls.append("prepare_selected_sources")
        prepared = input_dir / "legalone.csv"
        prepared.write_text("conteudo", encoding="utf-8")
        return [prepared]

    def fake_subprocess_run(*args, **kwargs):
        calls.append("subprocess_run")
        generated = output_dir / "resultado_sem_match.xlsx"
        generated.write_bytes(b"xlsx-content")
        return FakeCompletedProcess()

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
            },
            "numero_puro": {
                "linhas_consolidadas": 2,
                "arquivo_saida": "audit/numero_puro.xlsx",
            },
            "outro": {
                "linhas_consolidadas": 1,
                "arquivo_saida": "audit/outro.xlsx",
            },
        }

    def fake_build_consolidated_ui_summary(summary):
        calls.append("build_consolidated_ui_summary")
        return {
            "Consolidados gerados": 3,
            "Linhas consolidadas - sem_match": 10,
            "Linhas consolidadas - numero_puro": 2,
            "Linhas consolidadas - outro": 1,
        }

    def fake_persist_history_and_comparisons(**kwargs):
        calls.append("persist_history_and_comparisons")
        return {
            "comparison": {
                "execucao_anterior": "20260424_110000",
                "comparacoes": {},
            },
            "average_comparison": {
                "quantidade_execucoes_referencia": 2,
                "comparacoes": {},
            },
            "alerts": {
                "quantidade_alertas": 0,
                "texto_resumo": "Nenhum alerta",
                "contagem_por_severidade": {
                    "alta": 0,
                    "media": 0,
                    "baixa": 0,
                },
            },
            "avg_criteria": "ultimas_execucoes_com_sucesso",
        }

    def fake_build_comparison_ui_summary(comparison):
        calls.append("build_comparison_ui_summary")
        return {
            "Δ Arquivos gerados": "+1",
            "Δ Consolidados gerados": "+1",
            "Δ Linhas sem_match": "-1",
        }

    def fake_build_average_comparison_ui_summary(average_comparison):
        calls.append("build_average_comparison_ui_summary")
        return {
            "Δ vs média - sem_match": "-0.50",
            "Δ vs média - arquivos gerados": "+1.00",
        }

    def fake_build_execution_health_summary(**kwargs):
        calls.append("build_execution_health_summary")
        return {
            "Saúde da execução": "Saudável",
            "Tendência do sem_match": "Estável/Melhorando",
            "Tendência dos arquivos gerados": "Estável/Melhorando",
            "Nível de atenção": "Baixo",
        }

    def fake_build_success_result_summary(**kwargs):
        calls.append("build_success_result_summary")
        return {
            "Status": "✓ Concluído",
            "Modo diagnóstico": "NÃO",
            "Saúde da execução": "Saudável",
            "Quantidade de alertas": 0,
            "Pasta da auditoria": str(root_dir / "output" / "_auditoria" / "fake"),
            "Log da execução": str(root_dir / "logs_ui" / "fake.log"),
        }

    def fake_write_execution_markdown_summary(audit_dir, result_summary, log_file=None):
        calls.append("write_execution_markdown_summary")

    monkeypatch.setattr(handler, "_copy_selected_inputs_snapshot", fake_copy_selected_inputs_snapshot)
    monkeypatch.setattr(handler, "_remove_previous_internal_files", fake_remove_previous_internal_files)
    monkeypatch.setattr(handler, "_prepare_selected_sources", fake_prepare_selected_sources)
    monkeypatch.setattr(subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(handler, "_write_execution_audit", fake_write_execution_audit)
    monkeypatch.setattr(handler, "_write_output_audit_files", fake_write_output_audit_files)
    monkeypatch.setattr(handler, "_write_consolidated_output_audits", fake_write_consolidated_output_audits)
    monkeypatch.setattr(handler, "_build_consolidated_ui_summary", fake_build_consolidated_ui_summary)
    monkeypatch.setattr(handler, "_persist_history_and_comparisons", fake_persist_history_and_comparisons)
    monkeypatch.setattr(handler, "_build_comparison_ui_summary", fake_build_comparison_ui_summary)
    monkeypatch.setattr(handler, "_build_average_comparison_ui_summary", fake_build_average_comparison_ui_summary)
    monkeypatch.setattr(handler, "_build_execution_health_summary", fake_build_execution_health_summary)
    monkeypatch.setattr(handler, "_build_success_result_summary", fake_build_success_result_summary)
    monkeypatch.setattr(handler, "_write_execution_markdown_summary", fake_write_execution_markdown_summary)

    selected_files = {
        "legalone": ["arquivo.csv"],
        "webjur": [],
        "dw": [],
        "painel": [],
    }

    handler._process(selected_files, diagnostic_mode=False)

    expected_calls = {
        "copy_selected_inputs_snapshot",
        "remove_previous_internal_files",
        "prepare_selected_sources",
        "subprocess_run",
        "write_execution_audit",
        "write_output_audit_files",
        "write_consolidated_output_audits",
        "build_consolidated_ui_summary",
        "persist_history_and_comparisons",
        "build_comparison_ui_summary",
        "build_average_comparison_ui_summary",
        "build_execution_health_summary",
        "build_success_result_summary",
        "write_execution_markdown_summary",
    }

    assert expected_calls.issubset(set(calls))
    assert len(completed) == 1
    assert completed[0]["Status"] == "✓ Concluído"
    assert any("Processamento concluído com sucesso" in msg for msg, _ in logs)
    assert 100 in progresses
    assert "Processo concluído com sucesso." in statuses