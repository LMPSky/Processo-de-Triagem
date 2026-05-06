"""
Serviço de apoio para seleção, contagem e resumo de fontes.
"""
from __future__ import annotations

from pathlib import Path

from .source_config import SOURCE_ORDER, get_source_label


class SourceService:
    def count_selected_files(self, selected_files: dict[str, list[str]]) -> int:
        return sum(len(files or []) for files in selected_files.values())

    def build_sources_summary(self, selected_files: dict[str, list[str]]) -> dict:
        summary = {}
        for source_key in SOURCE_ORDER:
            files = selected_files.get(source_key, []) or []
            summary[source_key] = {
                "label": get_source_label(source_key),
                "count": len(files),
                "files": [str(Path(f)) for f in files],
            }
        return summary

    def build_result_source_lists(self, selected_files: dict[str, list[str]]) -> tuple[str, str, str]:
        informed = []
        absent = []
        detail_lines = []

        for source_key in SOURCE_ORDER:
            label = get_source_label(source_key)
            files = selected_files.get(source_key, []) or []

            if files:
                informed.append(label)
                detail_lines.append(f"{label}: {len(files)} arquivo(s)")
            else:
                absent.append(label)
                detail_lines.append(f"{label}: ausente")

        informed_text = ", ".join(informed) if informed else "Nenhuma"
        absent_text = ", ".join(absent) if absent else "Nenhuma"
        detail_text = "\n".join(detail_lines)

        return informed_text, absent_text, detail_text