"""
Serviço de preparação de arquivos de entrada.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .source_config import SOURCE_ORDER, get_source_internal_filenames, get_source_label


class InputService:
    def remove_previous_internal_files(
        self,
        input_dir: Path,
        safe_log=None,
        log_file=None,
        remove_webjur_derivatives_func=None,
    ):
        internal_names = []
        for source_key in SOURCE_ORDER:
            internal_names.extend(get_source_internal_filenames(source_key))

        for filename in internal_names:
            path = input_dir / filename
            try:
                if path.exists():
                    path.unlink()
                    if safe_log:
                        safe_log(f"[INPUT] Removendo arquivo interno anterior: {path.name}", "info", log_file)
            except Exception as e:
                if safe_log:
                    safe_log(f"[INPUT] ⚠️ Não foi possível remover {path.name}: {e}", "warning", log_file)

            if "webjur" in filename.lower():
                if remove_webjur_derivatives_func:
                    remove_webjur_derivatives_func(path)
                else:
                    sanitized = path.with_name(f"{path.stem}_SANITIZADO.csv")
                    ruins = path.with_name(f"{path.stem}_SANITIZADO_RUINS.csv")

                    for derived in [sanitized, ruins]:
                        try:
                            if derived.exists():
                                derived.unlink()
                                if safe_log:
                                    safe_log(f"[INPUT] Removendo derivado anterior: {derived.name}", "info", log_file)
                        except Exception as e:
                            if safe_log:
                                safe_log(f"[INPUT] ⚠️ Não foi possível remover {derived.name}: {e}", "warning", log_file)

    def copy_file_preserving_encoding(self, src: Path, dest: Path):
        if src.suffix.lower() == ".csv":
            with open(src, "r", encoding="latin-1", errors="replace") as fsrc:
                with open(dest, "w", encoding="latin-1") as fdst:
                    fdst.write(fsrc.read())
        else:
            shutil.copy2(str(src), str(dest))

    def copy_selected_inputs_snapshot(
        self,
        selected_files: dict[str, list[str]],
        audit_dir: Path,
        diagnostic_mode: bool,
        safe_log=None,
        log_file=None,
    ):
        if not diagnostic_mode:
            return

        snapshot_dir = audit_dir / "inputs_snapshot"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        if safe_log:
            safe_log("[DIAGNOSTICO] Modo diagnóstico ativo: preservando snapshot dos inputs originais...", "info", log_file)

        for source_key in SOURCE_ORDER:
            files = selected_files.get(source_key, []) or []
            if not files:
                continue

            source_dir = snapshot_dir / source_key
            source_dir.mkdir(parents=True, exist_ok=True)

            for idx, file_str in enumerate(files, start=1):
                src = Path(file_str)

                try:
                    if not src.exists():
                        if safe_log:
                            safe_log(
                                f"[DIAGNOSTICO] ⚠️ Arquivo original não encontrado para snapshot: {src}",
                                "warning",
                                log_file,
                            )
                        continue

                    dest_name = f"{idx:02d}_{src.name}"
                    dest = source_dir / dest_name
                    shutil.copy2(str(src), str(dest))

                    if safe_log:
                        safe_log(
                            f"[DIAGNOSTICO] ✓ Snapshot preservado: {src.name} -> {dest.relative_to(audit_dir)}",
                            "success",
                            log_file,
                        )
                except Exception as e:
                    if safe_log:
                        safe_log(
                            f"[DIAGNOSTICO] ⚠️ Não foi possível preservar snapshot de {src.name}: {e}",
                            "warning",
                            log_file,
                        )

    def prepare_selected_sources(
        self,
        selected_files: dict[str, list[str]],
        input_dir: Path,
        safe_log=None,
        log_file=None,
        copy_file_func=None,
        sanitize_webjur_func=None,
    ) -> list[Path]:
        prepared_files: list[Path] = []

        for source_key in SOURCE_ORDER:
            internal_targets = get_source_internal_filenames(source_key)
            source_files = selected_files.get(source_key, []) or []
            source_label = get_source_label(source_key)

            if not source_files:
                if safe_log:
                    safe_log(f"[INPUT] ℹ️ Fonte não informada nesta execução: {source_label}", "info", log_file)
                continue

            if safe_log:
                safe_log(
                    f"[INPUT] Preparando fonte '{source_label}' com {len(source_files)} arquivo(s)...",
                    "info",
                    log_file,
                )

            for idx, file_str in enumerate(source_files):
                if idx >= len(internal_targets):
                    if safe_log:
                        safe_log(
                            f"[INPUT] ⚠️ Arquivo extra ignorado para {source_label}: {Path(file_str).name}",
                            "warning",
                            log_file,
                        )
                    continue

                src = Path(file_str)
                dest = input_dir / internal_targets[idx]

                try:
                    if not src.exists():
                        if safe_log:
                            safe_log(f"[INPUT] ⚠️ Arquivo não encontrado: {src.name}", "warning", log_file)
                        continue

                    if source_key == "webjur" and "_sanitizado" in src.stem.lower():
                        if safe_log:
                            safe_log(
                                f"[INPUT] ⚠️ O arquivo selecionado já parece sanitizado ({src.name}). "
                                f"O ideal é selecionar o bruto original.",
                                "warning",
                                log_file,
                            )

                    if safe_log:
                        safe_log(
                            f"[INPUT] Copiando '{src.name}' para '{dest.name}'...",
                            "info",
                            log_file,
                        )

                    if copy_file_func:
                        copy_file_func(src, dest)
                    else:
                        self.copy_file_preserving_encoding(src, dest)

                    prepared_files.append(dest)

                    if safe_log:
                        safe_log(
                            f"[INPUT] ✓ {source_label}: {src.name} -> {dest.name}",
                            "success",
                            log_file,
                        )

                    if source_key == "webjur" and dest.suffix.lower() == ".csv" and sanitize_webjur_func:
                        sanitize_webjur_func(dest, log_file)

                except Exception as e:
                    if safe_log:
                        safe_log(
                            f"[INPUT] ❌ Erro ao preparar arquivo '{src.name}' para a fonte '{source_label}': {e}",
                            "error",
                            log_file,
                        )

        return prepared_files