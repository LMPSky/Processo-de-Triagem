"""
Handlers de eventos e processamento.
"""
from __future__ import annotations

import threading
import os
import sys
import subprocess
import csv
import shutil
from pathlib import Path
from datetime import datetime
from tkinter import filedialog

import pandas as pd

from .audit_service import AuditService
from .history_service import ExecutionHistoryService
from .input_service import InputService
from .source_service import SourceService
from .webjur_service import WebjurService


class ProcessHandler:
    """Gerencia o processamento em background."""

    OUTPUT_KEYWORDS = [
        "sem_match",
        "numero_puro",
        "outro",
        "civel",
        "trabalhista",
        "match",
    ]

    CONSOLIDATED_AUDIT_GROUPS = [
        "sem_match",
        "numero_puro",
        "outro",
    ]

    HISTORY_FIELDS = [
        "timestamp",
        "status",
        "modo_diagnostico",
        "fontes_com_arquivos",
        "arquivos_selecionados",
        "arquivos_preparados",
        "arquivos_gerados",
        "novos_arquivos",
        "consolidados_gerados",
        "linhas_sem_match",
        "linhas_numero_puro",
        "linhas_outro",
        "pasta_auditoria",
        "log_execucao",
    ]

    AVERAGE_REFERENCE_WINDOW = 5

    def __init__(self, callback_progress, callback_status, callback_log, callback_complete):
        self.callback_progress = callback_progress
        self.callback_status = callback_status
        self.callback_log = callback_log
        self.callback_complete = callback_complete
        self.thread = None

        self.history_service = ExecutionHistoryService(
            average_reference_window=self.AVERAGE_REFERENCE_WINDOW
        )
        self.audit_service = AuditService(
            output_keywords=self.OUTPUT_KEYWORDS,
            consolidated_audit_groups=self.CONSOLIDATED_AUDIT_GROUPS,
            average_reference_window=self.AVERAGE_REFERENCE_WINDOW,
        )
        self.source_service = SourceService()
        self.input_service = InputService()
        self.webjur_service = WebjurService()

    def start_processing(self, selected_files, diagnostic_mode=False):
        self.thread = threading.Thread(
            target=self._process,
            args=(selected_files, diagnostic_mode),
            daemon=True
        )
        self.thread.start()

    def _safe_log(self, message, tag="info", log_file=None):
        self.callback_log(message, tag)
        if log_file:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(message + "\n")

    # =========================
    # Compatibilidade retroativa
    # =========================

    def _safe_write_json(self, path: Path, data: dict | list):
        self.audit_service.safe_write_json(path, data)

    def _safe_write_csv(self, path: Path, rows: list[dict], fieldnames: list[str]):
        self.audit_service.safe_write_csv(path, rows, fieldnames)

    def _to_int_safe(self, value) -> int:
        return self.history_service.to_int_safe(value)

    def _to_float_safe(self, value) -> float:
        return self.history_service.to_float_safe(value)

    def _find_previous_history_row(self, history_rows: list[dict], current_timestamp: str) -> dict | None:
        return self.history_service.find_previous_history_row(history_rows, current_timestamp)

    def _find_previous_n_history_rows(self, history_rows: list[dict], current_timestamp: str, n: int) -> list[dict]:
        return self.history_service.find_previous_n_history_rows(history_rows, current_timestamp, n)

    def _find_previous_n_success_history_rows(self, history_rows: list[dict], current_timestamp: str, n: int) -> list[dict]:
        return self.history_service.find_previous_n_success_history_rows(history_rows, current_timestamp, n)

    def _resolve_average_reference_rows(
        self,
        history_rows: list[dict],
        current_timestamp: str,
    ) -> tuple[list[dict], str]:
        return self.history_service.resolve_average_reference_rows(history_rows, current_timestamp)

    def _build_execution_comparison(self, current_row: dict, previous_row: dict | None) -> dict:
        return self.history_service.build_execution_comparison(current_row, previous_row)

    def _build_average_comparison(
        self,
        current_row: dict,
        reference_rows: list[dict],
        reference_criteria: str = "",
    ) -> dict:
        return self.history_service.build_average_comparison(
            current_row,
            reference_rows,
            reference_criteria,
        )

    def _build_comparison_ui_summary(self, comparison: dict) -> dict:
        return self.history_service.build_comparison_ui_summary(comparison)

    def _build_average_comparison_ui_summary(self, average_comparison: dict) -> dict:
        return self.history_service.build_average_comparison_ui_summary(average_comparison)

    def _build_regression_alerts(self, comparison: dict, average_comparison: dict) -> dict:
        return self.history_service.build_regression_alerts(comparison, average_comparison)

    def _build_execution_health_summary(
        self,
        comparison_ui: dict,
        average_comparison_ui: dict,
        alerts: dict,
    ) -> dict:
        return self.history_service.build_execution_health_summary(
            comparison_ui=comparison_ui,
            average_comparison_ui=average_comparison_ui,
            alerts=alerts,
        )

    def _build_output_index(self, output_dir: Path, output_files: list[Path]) -> list[dict]:
        return self.audit_service.build_output_index(output_dir, output_files)

    def _build_output_summary(self, index_rows: list[dict], new_files: list[Path], output_dir: Path) -> dict:
        return self.audit_service.build_output_summary(index_rows, new_files, output_dir)

    def _write_output_audit_files(
        self,
        audit_dir: Path,
        output_dir: Path,
        output_files: list[Path],
        new_files: list[Path],
    ):
        self.audit_service.write_output_audit_files(
            audit_dir=audit_dir,
            output_dir=output_dir,
            output_files=output_files,
            new_files=new_files,
        )

    def _group_output_files_by_keyword(self, output_dir: Path, output_files: list[Path]) -> dict[str, list[Path]]:
        return self.audit_service.group_output_files_by_keyword(output_dir, output_files)

    def _build_consolidated_audit_excel(
        self,
        audit_dir: Path,
        output_dir: Path,
        group_name: str,
        files: list[Path],
        log_file=None,
    ) -> dict:
        return self.audit_service.build_consolidated_audit_excel(
            audit_dir=audit_dir,
            output_dir=output_dir,
            group_name=group_name,
            files=files,
            safe_log=self._safe_log,
            log_file=log_file,
        )

    def _write_consolidated_summary_excel(self, audit_dir: Path, summary: dict, log_file=None):
        self.audit_service.write_consolidated_summary_excel(
            audit_dir=audit_dir,
            summary=summary,
            safe_log=self._safe_log,
            log_file=log_file,
        )

    def _write_consolidated_output_audits(
        self,
        audit_dir: Path,
        output_dir: Path,
        output_files: list[Path],
        log_file=None,
    ) -> dict:
        return self.audit_service.write_consolidated_output_audits(
            audit_dir=audit_dir,
            output_dir=output_dir,
            output_files=output_files,
            safe_log=self._safe_log,
            log_file=log_file,
        )

    def _build_consolidated_ui_summary(self, consolidated_summary: dict) -> dict:
        return self.audit_service.build_consolidated_ui_summary(consolidated_summary)

    def _count_selected_files(self, selected_files: dict[str, list[str]]) -> int:
        return self.source_service.count_selected_files(selected_files)

    def _build_sources_summary(self, selected_files: dict[str, list[str]]) -> dict:
        return self.source_service.build_sources_summary(selected_files)

    def _build_result_source_lists(self, selected_files: dict[str, list[str]]) -> tuple[str, str, str]:
        return self.source_service.build_result_source_lists(selected_files)

    def _remove_previous_internal_files(self, input_dir: Path, log_file=None):
        self.input_service.remove_previous_internal_files(
            input_dir=input_dir,
            safe_log=self._safe_log,
            log_file=log_file,
            remove_webjur_derivatives_func=lambda path: self.webjur_service.remove_previous_derivatives(
                path, safe_log=self._safe_log, log_file=log_file
            ),
        )

    def _copy_file_preserving_encoding(self, src: Path, dest: Path):
        self.input_service.copy_file_preserving_encoding(src, dest)

    def _copy_selected_inputs_snapshot(
        self,
        selected_files: dict[str, list[str]],
        audit_dir: Path,
        diagnostic_mode: bool,
        log_file=None,
    ):
        self.input_service.copy_selected_inputs_snapshot(
            selected_files=selected_files,
            audit_dir=audit_dir,
            diagnostic_mode=diagnostic_mode,
            safe_log=self._safe_log,
            log_file=log_file,
        )

    def _prepare_selected_sources(self, selected_files: dict[str, list[str]], input_dir: Path, log_file=None) -> list[Path]:
        return self.input_service.prepare_selected_sources(
            selected_files=selected_files,
            input_dir=input_dir,
            safe_log=self._safe_log,
            log_file=log_file,
            copy_file_func=self._copy_file_preserving_encoding,
            sanitize_webjur_func=self._sanitize_webjur_csv,
        )

    def _write_regression_alerts(self, audit_dir: Path, alerts: dict, log_file=None):
        try:
            output_path = self.audit_service.write_regression_alerts(audit_dir, alerts)

            if alerts.get("quantidade_alertas", 0) > 0:
                self._safe_log(
                    f"[ALERTAS] ⚠️ {alerts['quantidade_alertas']} alerta(s) de regressão salvo(s) em: {output_path.name}",
                    "warning",
                    log_file,
                )
            else:
                self._safe_log(
                    "[ALERTAS] ✓ Nenhum alerta de regressão detectado.",
                    "success",
                    log_file,
                )
        except Exception as e:
            self._safe_log(
                f"[ALERTAS] ⚠️ Não foi possível salvar os alertas da execução: {e}",
                "warning",
                log_file,
            )

    def _write_execution_comparison(self, audit_dir: Path, comparison: dict, log_file=None):
        try:
            output_path = self.audit_service.write_execution_comparison(audit_dir, comparison)

            if comparison.get("execucao_anterior"):
                self._safe_log(
                    f"[COMPARATIVO] ✓ Comparativo com execução anterior salvo em: {output_path.name}",
                    "success",
                    log_file,
                )
            else:
                self._safe_log(
                    "[COMPARATIVO] ℹ️ Não havia execução anterior para comparar.",
                    "info",
                    log_file,
                )
        except Exception as e:
            self._safe_log(
                f"[COMPARATIVO] ⚠️ Não foi possível salvar o comparativo com a execução anterior: {e}",
                "warning",
                log_file,
            )

    def _write_average_comparison(self, audit_dir: Path, comparison: dict, log_file=None):
        try:
            output_path = self.audit_service.write_average_comparison(audit_dir, comparison)

            if comparison.get("quantidade_execucoes_referencia", 0) > 0:
                criterio = comparison.get("criterio_referencia", "")
                criterio_texto = f" | critério: {criterio}" if criterio else ""
                self._safe_log(
                    f"[COMPARATIVO-MEDIA] ✓ Comparativo com média das últimas execuções salvo em: {output_path.name}{criterio_texto}",
                    "success",
                    log_file,
                )
            else:
                self._safe_log(
                    "[COMPARATIVO-MEDIA] ℹ️ Não havia execuções anteriores suficientes para comparação por média.",
                    "info",
                    log_file,
                )
        except Exception as e:
            self._safe_log(
                f"[COMPARATIVO-MEDIA] ⚠️ Não foi possível salvar o comparativo por média: {e}",
                "warning",
                log_file,
            )

    def _write_execution_markdown_summary(self, audit_dir: Path, result_summary: dict, log_file=None):
        try:
            output_path = self.audit_service.write_execution_markdown_summary(audit_dir, result_summary)
            self._safe_log(
                f"[AUDITORIA] ✓ Resumo Markdown da execução gerado: {output_path.name}",
                "success",
                log_file,
            )
        except Exception as e:
            self._safe_log(
                f"[AUDITORIA] ⚠️ Não foi possível gerar o resumo em Markdown: {e}",
                "warning",
                log_file,
            )

    # =========================
    # Diretórios de saída
    # =========================

    def _get_root_dir(self) -> Path:
        return Path(__file__).parent.parent

    def _get_output_root_dir(self, root_dir: Path) -> Path:
        return root_dir / "output"

    def _get_runs_dir(self, root_dir: Path) -> Path:
        return self._get_output_root_dir(root_dir) / "runs"

    def _get_latest_output_dir(self, root_dir: Path) -> Path:
        return self._get_output_root_dir(root_dir) / "latest"

    def _get_history_dir(self, root_dir: Path) -> Path:
        return self._get_output_root_dir(root_dir) / "_historico_execucoes"

    def _get_current_run_output_dir(self, root_dir: Path, timestamp: str) -> Path:
        return self._get_runs_dir(root_dir) / timestamp

    def _get_current_run_audit_dir(self, root_dir: Path, timestamp: str) -> Path:
        return self._get_current_run_output_dir(root_dir, timestamp) / "_auditoria"

    def _get_operational_output_files(self, output_root_dir: Path) -> list[Path]:
        excluded_top_dirs = {"runs", "latest", "_historico_execucoes", "_auditoria"}

        files = []
        for p in output_root_dir.rglob("*.xlsx"):
            try:
                relative = p.relative_to(output_root_dir)
                if relative.parts and relative.parts[0] in excluded_top_dirs:
                    continue
            except Exception:
                pass
            files.append(p)

        return files

    def _clean_operational_output_area(self, output_root_dir: Path, log_file=None):
        output_root_dir.mkdir(parents=True, exist_ok=True)

        preserved_names = {"runs", "latest", "_historico_execucoes"}

        for item in output_root_dir.iterdir():
            if item.name in preserved_names:
                continue

            try:
                if item.is_dir():
                    shutil.rmtree(item)
                    self._safe_log(f"[OUTPUT] Removendo diretório operacional anterior: {item.name}", "info", log_file)
                else:
                    item.unlink()
                    self._safe_log(f"[OUTPUT] Removendo arquivo operacional anterior: {item.name}", "info", log_file)
            except Exception as e:
                self._safe_log(
                    f"[OUTPUT] ⚠️ Não foi possível remover item operacional anterior '{item.name}': {e}",
                    "warning",
                    log_file,
                )

    def _copy_tree_contents(self, src_dir: Path, dest_dir: Path, log_file=None):
        if not src_dir.exists():
            return

        dest_dir.mkdir(parents=True, exist_ok=True)

        for item in src_dir.rglob("*"):
            if item.is_dir():
                continue

            relative = item.relative_to(src_dir)
            target = dest_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(item), str(target))

            if log_file:
                self._safe_log(
                    f"[OUTPUT] Copiado para snapshot: {relative}",
                    "info",
                    log_file,
                )

    def _snapshot_operational_output_to_run_and_latest(
        self,
        root_dir: Path,
        timestamp: str,
        log_file=None,
    ):
        output_root_dir = self._get_output_root_dir(root_dir)
        run_output_dir = self._get_current_run_output_dir(root_dir, timestamp)
        latest_dir = self._get_latest_output_dir(root_dir)

        if run_output_dir.exists():
            shutil.rmtree(run_output_dir, ignore_errors=True)
        run_output_dir.mkdir(parents=True, exist_ok=True)

        if latest_dir.exists():
            shutil.rmtree(latest_dir, ignore_errors=True)
        latest_dir.mkdir(parents=True, exist_ok=True)

        preserved_names = {"runs", "latest", "_historico_execucoes"}

        copied_files = []

        for item in output_root_dir.iterdir():
            if item.name in preserved_names:
                continue

            if item.is_dir():
                shutil.copytree(str(item), str(run_output_dir / item.name), dirs_exist_ok=True)
                shutil.copytree(str(item), str(latest_dir / item.name), dirs_exist_ok=True)
                copied_files.append(item.name)
            else:
                shutil.copy2(str(item), str(run_output_dir / item.name))
                shutil.copy2(str(item), str(latest_dir / item.name))
                copied_files.append(item.name)

        self._safe_log(
            f"[OUTPUT] ✓ Snapshot da execução salvo em: {run_output_dir}",
            "success",
            log_file,
        )
        self._safe_log(
            f"[OUTPUT] ✓ Pasta latest atualizada em: {latest_dir}",
            "success",
            log_file,
        )

        return run_output_dir, latest_dir, copied_files

    # =========================
    # Sanitização WebJur
    # =========================

    def _sanitize_webjur_csv(self, path: Path, log_file=None) -> bool:
        return self.webjur_service.sanitize_csv(
            path=path,
            safe_log=self._safe_log,
            log_file=log_file,
        )

    # =========================
    # Histórico e auditoria própria
    # =========================

    def _build_execution_history_row(
        self,
        timestamp: str,
        status: str,
        diagnostic_mode: bool,
        selected_files: dict[str, list[str]],
        prepared_files: list[Path],
        output_files: list[Path],
        new_files: list[Path],
        consolidated_ui: dict,
        audit_dir: Path,
        log_file: Path,
    ) -> dict:
        return {
            "timestamp": timestamp,
            "status": status,
            "modo_diagnostico": "SIM" if diagnostic_mode else "NAO",
            "fontes_com_arquivos": len([k for k, v in selected_files.items() if v]),
            "arquivos_selecionados": self._count_selected_files(selected_files),
            "arquivos_preparados": len(prepared_files),
            "arquivos_gerados": len(output_files),
            "novos_arquivos": len(new_files),
            "consolidados_gerados": consolidated_ui.get("Consolidados gerados", 0),
            "linhas_sem_match": consolidated_ui.get("Linhas consolidadas - sem_match", 0),
            "linhas_numero_puro": consolidated_ui.get("Linhas consolidadas - numero_puro", 0),
            "linhas_outro": consolidated_ui.get("Linhas consolidadas - outro", 0),
            "pasta_auditoria": str(audit_dir),
            "log_execucao": str(log_file),
        }

    def _sync_execution_history_excel(self, history_csv: Path, log_file=None):
        try:
            if not history_csv.exists():
                return

            history_xlsx = history_csv.with_suffix(".xlsx")
            df = pd.read_csv(history_csv, dtype=str, encoding="utf-8-sig").fillna("")

            with pd.ExcelWriter(history_xlsx, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="historico", index=False)

            self._safe_log(
                f"[HISTORICO] ✓ Histórico Excel sincronizado em: {history_xlsx}",
                "success",
                log_file,
            )
        except Exception as e:
            self._safe_log(
                f"[HISTORICO] ⚠️ Não foi possível sincronizar o histórico em Excel: {e}",
                "warning",
                log_file,
            )

    def _load_execution_history_rows(self, root_dir: Path) -> list[dict]:
        history_csv = self._get_history_dir(root_dir) / "historico_execucoes.csv"
        if not history_csv.exists():
            return []

        rows = []
        try:
            with open(history_csv, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception:
            return []

        return rows

    def _append_execution_history(self, root_dir: Path, row: dict, log_file=None):
        try:
            history_dir = self._get_history_dir(root_dir)
            history_dir.mkdir(parents=True, exist_ok=True)
            history_file = history_dir / "historico_execucoes.csv"

            file_exists = history_file.exists()

            with open(history_file, "a", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.HISTORY_FIELDS)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)

            self._safe_log(
                f"[HISTORICO] ✓ Histórico atualizado em: {history_file}",
                "success",
                log_file,
            )

            self._sync_execution_history_excel(history_file, log_file)

        except Exception as e:
            self._safe_log(
                f"[HISTORICO] ⚠️ Não foi possível atualizar o histórico de execuções: {e}",
                "warning",
                log_file,
            )

    def _write_execution_audit(
        self,
        audit_dir: Path,
        timestamp: str,
        diagnostic_mode: bool,
        selected_files: dict[str, list[str]],
        prepared_files: list[Path],
        output_files: list[Path],
        log_file: Path,
        status: str,
        return_code: int | None,
    ):
        fontes_utilizadas = self._build_sources_summary(selected_files)

        resumo_execucao = {
            "timestamp": timestamp,
            "status": status,
            "modo_diagnostico": diagnostic_mode,
            "return_code": return_code,
            "log_file": str(log_file),
            "audit_dir": str(audit_dir),
            "fontes_com_arquivos": len([k for k, v in selected_files.items() if v]),
            "arquivos_selecionados": self._count_selected_files(selected_files),
            "arquivos_preparados": len(prepared_files),
            "arquivos_saida_xlsx": len(output_files),
            "arquivos_preparados_nomes": [p.name for p in prepared_files],
            "arquivos_saida_nomes": [str(p) for p in output_files],
        }

        arquivos_saida = {
            "output_files": [str(p) for p in output_files],
            "output_files_relative": [str(p) for p in output_files],
        }

        self._safe_write_json(audit_dir / "resumo_execucao.json", resumo_execucao)
        self._safe_write_json(audit_dir / "fontes_utilizadas.json", fontes_utilizadas)
        self._safe_write_json(audit_dir / "arquivos_saida.json", arquivos_saida)

    # =========================
    # Helpers de finalização
    # =========================

    def _persist_history_and_comparisons(
        self,
        root_dir: Path,
        audit_dir: Path,
        history_row: dict,
        log_file=None,
    ):
        self._append_execution_history(root_dir, history_row, log_file)

        history_rows = self._load_execution_history_rows(root_dir)
        previous_row = self._find_previous_history_row(history_rows, history_row["timestamp"])
        avg_rows, avg_criteria = self._resolve_average_reference_rows(history_rows, history_row["timestamp"])

        comparison = self._build_execution_comparison(history_row, previous_row)
        average_comparison = self._build_average_comparison(history_row, avg_rows, avg_criteria)
        alerts = self._build_regression_alerts(comparison, average_comparison)

        self._write_execution_comparison(audit_dir, comparison, log_file)
        self._write_average_comparison(audit_dir, average_comparison, log_file)
        self._write_regression_alerts(audit_dir, alerts, log_file)

        return {
            "history_rows": history_rows,
            "previous_row": previous_row,
            "avg_rows": avg_rows,
            "avg_criteria": avg_criteria,
            "comparison": comparison,
            "average_comparison": average_comparison,
            "alerts": alerts,
        }

    def _handle_non_success_completion(
        self,
        *,
        root_dir: Path,
        audit_dir: Path,
        timestamp: str,
        diagnostic_mode: bool,
        selected_files: dict[str, list[str]],
        prepared_files: list[Path],
        output_files: list[Path],
        new_files: list[Path],
        consolidated_ui: dict,
        log_file: Path,
        status: str,
        return_code: int | None,
        write_output_audits: bool = False,
        output_dir: Path | None = None,
    ):
        self._write_execution_audit(
            audit_dir=audit_dir,
            timestamp=timestamp,
            diagnostic_mode=diagnostic_mode,
            selected_files=selected_files,
            prepared_files=prepared_files,
            output_files=output_files,
            log_file=log_file,
            status=status,
            return_code=return_code,
        )

        if write_output_audits and output_dir is not None:
            self._write_output_audit_files(
                audit_dir=audit_dir,
                output_dir=output_dir,
                output_files=output_files,
                new_files=new_files,
            )
            consolidated_summary = self._write_consolidated_output_audits(
                audit_dir=audit_dir,
                output_dir=output_dir,
                output_files=output_files,
                log_file=log_file,
            )
            consolidated_ui = self._build_consolidated_ui_summary(consolidated_summary)

        history_row = self._build_execution_history_row(
            timestamp=timestamp,
            status=status,
            diagnostic_mode=diagnostic_mode,
            selected_files=selected_files,
            prepared_files=prepared_files,
            output_files=output_files,
            new_files=new_files,
            consolidated_ui=consolidated_ui,
            audit_dir=audit_dir,
            log_file=log_file,
        )

        self._persist_history_and_comparisons(
            root_dir=root_dir,
            audit_dir=audit_dir,
            history_row=history_row,
            log_file=log_file,
        )

        self.callback_complete(None)

    def _build_success_result_summary(
        self,
        *,
        diagnostic_mode: bool,
        selected_files: dict[str, list[str]],
        prepared_files: list[Path],
        after_files: list[Path],
        new_files: list[Path],
        consolidated_ui: dict,
        health_summary: dict,
        comparison_ui: dict,
        average_comparison_ui: dict,
        alerts: dict,
        avg_criteria: str,
        audit_dir: Path,
        log_file: Path,
    ) -> dict:
        informed_text, absent_text, detail_text = self._build_result_source_lists(selected_files)

        return {
            "Status": "✓ Concluído",
            "Modo diagnóstico": "SIM" if diagnostic_mode else "NÃO",
            "Saúde da execução": health_summary["Saúde da execução"],
            "Tendência do sem_match": health_summary["Tendência do sem_match"],
            "Tendência dos arquivos gerados": health_summary["Tendência dos arquivos gerados"],
            "Nível de atenção": health_summary["Nível de atenção"],
            "Fontes com arquivos preparados": len([k for k, v in selected_files.items() if v]),
            "Arquivos selecionados": self._count_selected_files(selected_files),
            "Arquivos preparados": len(prepared_files),
            "Fontes informadas": informed_text,
            "Fontes ausentes": absent_text,
            "Resumo por fonte": detail_text,
            "Arquivos preparados (nomes)": ", ".join(p.name for p in prepared_files),
            "Arquivos gerados": len(after_files),
            "Novos arquivos": len(new_files),
            "Consolidados gerados": consolidated_ui["Consolidados gerados"],
            "Linhas consolidadas - sem_match": consolidated_ui["Linhas consolidadas - sem_match"],
            "Linhas consolidadas - numero_puro": consolidated_ui["Linhas consolidadas - numero_puro"],
            "Linhas consolidadas - outro": consolidated_ui["Linhas consolidadas - outro"],
            "Δ Arquivos gerados": comparison_ui["Δ Arquivos gerados"],
            "Δ Consolidados gerados": comparison_ui["Δ Consolidados gerados"],
            "Δ Linhas sem_match": comparison_ui["Δ Linhas sem_match"],
            "Δ vs média - sem_match": average_comparison_ui["Δ vs média - sem_match"],
            "Δ vs média - arquivos gerados": average_comparison_ui["Δ vs média - arquivos gerados"],
            "Quantidade de alertas": alerts["quantidade_alertas"],
            "Alertas alta severidade": alerts.get("contagem_por_severidade", {}).get("alta", 0),
            "Alertas média severidade": alerts.get("contagem_por_severidade", {}).get("media", 0),
            "Alertas baixa severidade": alerts.get("contagem_por_severidade", {}).get("baixa", 0),
            "Alertas de regressão": alerts["texto_resumo"],
            "Critério da média recente": avg_criteria or "sem referência",
            "Localização": "output/latest/",
            "Pasta da auditoria": str(audit_dir),
            "Log da execução": str(log_file),
        }

    # =========================
    # Processo principal
    # =========================

    def _process(self, selected_files, diagnostic_mode=False):
        root_dir = self._get_root_dir()
        input_dir = root_dir / "input"
        output_root_dir = self._get_output_root_dir(root_dir)
        runs_dir = self._get_runs_dir(root_dir)
        latest_dir = self._get_latest_output_dir(root_dir)
        logs_dir = root_dir / "logs_ui"
        logs_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"ui_run_{timestamp}.log"
        run_output_dir = self._get_current_run_output_dir(root_dir, timestamp)
        audit_dir = self._get_current_run_audit_dir(root_dir, timestamp)

        prepared_files: list[Path] = []
        after_files: list[Path] = []
        return_code: int | None = None
        new_files: list[Path] = []
        consolidated_ui = {
            "Consolidados gerados": 0,
            "Linhas consolidadas - sem_match": 0,
            "Linhas consolidadas - numero_puro": 0,
            "Linhas consolidadas - outro": 0,
        }

        try:
            self._safe_log("[UI] Iniciando processamento...", "info", log_file)
            if diagnostic_mode:
                self._safe_log("[DIAGNOSTICO] Execução iniciada em modo diagnóstico.", "info", log_file)

            self.callback_progress(5)
            self.callback_status("Preparando arquivos...")

            input_dir.mkdir(parents=True, exist_ok=True)
            output_root_dir.mkdir(parents=True, exist_ok=True)
            runs_dir.mkdir(parents=True, exist_ok=True)
            latest_dir.mkdir(parents=True, exist_ok=True)
            audit_dir.mkdir(parents=True, exist_ok=True)

            self._safe_log(f"[UI] 📂 Diretório raiz: {root_dir}", "info", log_file)
            self._safe_log(f"[UI] 📂 Entrada: {input_dir}", "info", log_file)
            self._safe_log(f"[UI] 📂 Saída raiz: {output_root_dir}", "info", log_file)
            self._safe_log(f"[UI] 📂 Saída da execução atual: {run_output_dir}", "info", log_file)
            self._safe_log(f"[UI] 📂 Pasta latest: {latest_dir}", "info", log_file)
            self._safe_log(f"[UI] 📝 Log desta execução: {log_file}", "info", log_file)
            self._safe_log(f"[UI] 🧾 Pasta de auditoria desta execução: {audit_dir}", "info", log_file)

            self._copy_selected_inputs_snapshot(
                selected_files=selected_files,
                audit_dir=audit_dir,
                diagnostic_mode=diagnostic_mode,
                log_file=log_file,
            )

            self.callback_progress(10)
            self.callback_status("Limpando resíduos anteriores...")
            self._safe_log("[INPUT] Limpando arquivos internos de execuções anteriores...", "info", log_file)
            self._safe_log("[INPUT] Não é necessário limpar manualmente a pasta input/ antes de rodar.", "info", log_file)
            self._remove_previous_internal_files(input_dir, log_file)

            self._safe_log("[OUTPUT] Limpando somente a área operacional do output...", "info", log_file)
            self._safe_log("[OUTPUT] Pastas preservadas: runs/, latest/, _historico_execucoes/", "info", log_file)
            self._clean_operational_output_area(output_root_dir, log_file)

            self.callback_progress(15)
            self.callback_status("Copiando arquivos por fonte...")
            self._safe_log("[INPUT] Copiando arquivos selecionados para a pasta de processamento...", "info", log_file)

            prepared_files = self._prepare_selected_sources(selected_files, input_dir, log_file)

            if not prepared_files:
                self._safe_log("[INPUT] ❌ Nenhum arquivo foi preparado para processamento.", "error", log_file)
                self._handle_non_success_completion(
                    root_dir=root_dir,
                    audit_dir=audit_dir,
                    timestamp=timestamp,
                    diagnostic_mode=diagnostic_mode,
                    selected_files=selected_files,
                    prepared_files=prepared_files,
                    output_files=[],
                    new_files=[],
                    consolidated_ui=consolidated_ui,
                    log_file=log_file,
                    status="erro_sem_arquivos_preparados",
                    return_code=None,
                )
                return

            self._safe_log("[INPUT] Arquivos atualmente em input/:", "info", log_file)
            for item in sorted(input_dir.glob("*")):
                if item.is_file():
                    self._safe_log(f"[INPUT]   • {item.name}", "info", log_file)

            self.callback_progress(20)
            self.callback_status("Executando processamento...")
            self._safe_log("[PIPELINE] Iniciando robô de classificação...", "info", log_file)

            before_files = set(str(p.resolve()) for p in self._get_operational_output_files(output_root_dir))

            try:
                cmd = [sys.executable, "-X", "utf8", "main.py"]
                self._safe_log(f"[PIPELINE] Executando comando: {' '.join(cmd)}", "info", log_file)

                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                env["PYTHONUTF8"] = "1"

                result = subprocess.run(
                    cmd,
                    cwd=str(root_dir),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=600,
                    env=env
                )

                return_code = result.returncode
                self._safe_log(f"[PIPELINE] Return code: {result.returncode}", "info", log_file)

                if result.stdout:
                    self._safe_log("[PIPELINE] === STDOUT ===", "info", log_file)
                    for line in result.stdout.splitlines():
                        if line.strip():
                            self._safe_log(line, "info", log_file)

                if result.stderr:
                    self._safe_log("[PIPELINE] === STDERR ===", "error", log_file)
                    for line in result.stderr.splitlines():
                        if line.strip():
                            self._safe_log(line, "error", log_file)

            except subprocess.TimeoutExpired:
                self._safe_log("[PIPELINE] ❌ Timeout: o processamento excedeu 10 minutos.", "error", log_file)
                self._handle_non_success_completion(
                    root_dir=root_dir,
                    audit_dir=audit_dir,
                    timestamp=timestamp,
                    diagnostic_mode=diagnostic_mode,
                    selected_files=selected_files,
                    prepared_files=prepared_files,
                    output_files=[],
                    new_files=[],
                    consolidated_ui=consolidated_ui,
                    log_file=log_file,
                    status="erro_timeout",
                    return_code=None,
                )
                return
            except Exception as e:
                self._safe_log(f"[PIPELINE] ❌ Erro ao executar main.py: {e}", "error", log_file)
                self._handle_non_success_completion(
                    root_dir=root_dir,
                    audit_dir=audit_dir,
                    timestamp=timestamp,
                    diagnostic_mode=diagnostic_mode,
                    selected_files=selected_files,
                    prepared_files=prepared_files,
                    output_files=[],
                    new_files=[],
                    consolidated_ui=consolidated_ui,
                    log_file=log_file,
                    status="erro_execucao_pipeline",
                    return_code=None,
                )
                return

            self.callback_progress(85)
            self.callback_status("Verificando arquivos gerados...")
            self._safe_log("[RESULTADO] Procurando arquivos .xlsx na área operacional de output/...", "info", log_file)

            after_files = list(self._get_operational_output_files(output_root_dir))
            after_files_set = set(str(p.resolve()) for p in after_files)
            new_files = [Path(p) for p in sorted(after_files_set - before_files)]

            self._safe_log(f"[RESULTADO] Total de .xlsx encontrados na área operacional: {len(after_files)}", "info", log_file)
            self._safe_log(f"[RESULTADO] Novos .xlsx gerados nesta execução: {len(new_files)}", "info", log_file)

            for f in sorted(after_files):
                rel = f.relative_to(output_root_dir)
                self._safe_log(f"[RESULTADO]   • {rel}", "info", log_file)

            if result.returncode != 0:
                self._safe_log("[RESULTADO] ❌ O robô terminou com erro (return code diferente de 0).", "error", log_file)
                self._handle_non_success_completion(
                    root_dir=root_dir,
                    audit_dir=audit_dir,
                    timestamp=timestamp,
                    diagnostic_mode=diagnostic_mode,
                    selected_files=selected_files,
                    prepared_files=prepared_files,
                    output_files=after_files,
                    new_files=new_files,
                    consolidated_ui=consolidated_ui,
                    log_file=log_file,
                    status="erro_return_code",
                    return_code=result.returncode,
                    write_output_audits=True,
                    output_dir=output_root_dir,
                )
                return

            if len(after_files) == 0:
                self._safe_log("[RESULTADO] ❌ O robô terminou sem gerar nenhum arquivo .xlsx em output/.", "error", log_file)
                self._handle_non_success_completion(
                    root_dir=root_dir,
                    audit_dir=audit_dir,
                    timestamp=timestamp,
                    diagnostic_mode=diagnostic_mode,
                    selected_files=selected_files,
                    prepared_files=prepared_files,
                    output_files=[],
                    new_files=[],
                    consolidated_ui=consolidated_ui,
                    log_file=log_file,
                    status="erro_sem_saida_xlsx",
                    return_code=result.returncode,
                )
                return

            self._snapshot_operational_output_to_run_and_latest(
                root_dir=root_dir,
                timestamp=timestamp,
                log_file=log_file,
            )

            run_files_for_audit = list(run_output_dir.rglob("*.xlsx"))
            run_files_for_audit = [
                p for p in run_files_for_audit
                if "_auditoria" not in p.parts and "_historico_execucoes" not in p.parts
            ]

            latest_files = list(latest_dir.rglob("*.xlsx"))
            latest_files = [
                p for p in latest_files
                if "_historico_execucoes" not in p.parts and "_auditoria" not in p.parts
            ]

            self._write_execution_audit(
                audit_dir=audit_dir,
                timestamp=timestamp,
                diagnostic_mode=diagnostic_mode,
                selected_files=selected_files,
                prepared_files=prepared_files,
                output_files=latest_files,
                log_file=log_file,
                status="sucesso",
                return_code=result.returncode,
            )

            self._write_output_audit_files(
                audit_dir=audit_dir,
                output_dir=run_output_dir,
                output_files=run_files_for_audit,
                new_files=run_files_for_audit,
            )

            consolidated_summary = self._write_consolidated_output_audits(
                audit_dir=audit_dir,
                output_dir=run_output_dir,
                output_files=run_files_for_audit,
                log_file=log_file,
            )
            consolidated_ui = self._build_consolidated_ui_summary(consolidated_summary)

            history_row = self._build_execution_history_row(
                timestamp=timestamp,
                status="sucesso",
                diagnostic_mode=diagnostic_mode,
                selected_files=selected_files,
                prepared_files=prepared_files,
                output_files=run_files_for_audit,
                new_files=run_files_for_audit,
                consolidated_ui=consolidated_ui,
                audit_dir=audit_dir,
                log_file=log_file,
            )

            persisted = self._persist_history_and_comparisons(
                root_dir=root_dir,
                audit_dir=audit_dir,
                history_row=history_row,
                log_file=log_file,
            )

            comparison = persisted["comparison"]
            average_comparison = persisted["average_comparison"]
            alerts = persisted["alerts"]
            avg_criteria = persisted["avg_criteria"]

            comparison_ui = self._build_comparison_ui_summary(comparison)
            average_comparison_ui = self._build_average_comparison_ui_summary(average_comparison)
            health_summary = self._build_execution_health_summary(
                comparison_ui=comparison_ui,
                average_comparison_ui=average_comparison_ui,
                alerts=alerts,
            )

            self.callback_progress(100)
            self.callback_status("Processo concluído com sucesso.")
            self._safe_log("[RESULTADO] ✓ Processamento concluído com sucesso!", "success", log_file)
            self._safe_log(f"[AUDITORIA] Índice, consolidados, resumo Excel, histórico, comparativos e alertas salvos em: {audit_dir}", "success", log_file)
            self._safe_log(f"[RESULTADO] Pasta da execução atual: {run_output_dir}", "success", log_file)
            self._safe_log(f"[RESULTADO] Pasta latest atualizada: {latest_dir}", "success", log_file)

            result_summary = self._build_success_result_summary(
                diagnostic_mode=diagnostic_mode,
                selected_files=selected_files,
                prepared_files=prepared_files,
                after_files=run_files_for_audit,
                new_files=run_files_for_audit,
                consolidated_ui=consolidated_ui,
                health_summary=health_summary,
                comparison_ui=comparison_ui,
                average_comparison_ui=average_comparison_ui,
                alerts=alerts,
                avg_criteria=avg_criteria,
                audit_dir=audit_dir,
                log_file=log_file,
            )

            self._write_execution_markdown_summary(audit_dir, result_summary, log_file)

            self.callback_complete(result_summary)

        except Exception as e:
            self._safe_log(f"[UI] ❌ Erro fatal: {e}", "error", log_file)
            import traceback
            self._safe_log(traceback.format_exc(), "error", log_file)

            try:
                self._handle_non_success_completion(
                    root_dir=root_dir,
                    audit_dir=audit_dir,
                    timestamp=timestamp,
                    diagnostic_mode=diagnostic_mode,
                    selected_files=selected_files,
                    prepared_files=prepared_files,
                    output_files=after_files,
                    new_files=[],
                    consolidated_ui=consolidated_ui,
                    log_file=log_file,
                    status="erro_fatal",
                    return_code=return_code,
                    write_output_audits=bool(after_files),
                    output_dir=output_root_dir if after_files else None,
                )
            except Exception:
                self.callback_complete(None)


class FileHandler:
    """Gerencia seleção de arquivos."""

    @staticmethod
    def select_files():
        files = filedialog.askopenfilenames(
            title="Selecione os arquivos para processar",
            filetypes=[
                ("Todos os arquivos", "*.csv *.xlsx"),
                ("CSV", "*.csv"),
                ("Excel", "*.xlsx"),
            ]
        )
        return list(files)

    @staticmethod
    def select_output_dir():
        folder = filedialog.askdirectory(title="Selecione a pasta de saída")
        return folder