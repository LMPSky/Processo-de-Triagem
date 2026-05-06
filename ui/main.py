"""
Aplicação principal com Tkinter.
"""
from __future__ import annotations

import tkinter as tk
from typing import TypedDict
from tkinter import messagebox
from pathlib import Path
import subprocess
import sys
import os

from tkinterdnd2 import TkinterDnD

from .styles import COLORS, FONTS, DIMENSIONS
from .widgets import CustomButton, DragDropFrame, ProgressPanel, ResultPanel
from .handlers import ProcessHandler, FileHandler
from .result_visuals import (
    severity_colors,
    health_card_colors,
    extract_alert_lines,
)
from .source_config import (
    SOURCE_ORDER,
    build_empty_selected_files,
    build_empty_skipped_sources,
    get_source_description,
    get_source_label,
    get_source_max_files,
    is_source_optional,
)


def _font(name: str, fallback):
    return FONTS.get(name, fallback)


def _color(name: str, fallback: str):
    return COLORS.get(name, fallback)


def _dim(name: str, fallback: int):
    return DIMENSIONS.get(name, fallback)

class SourceWidgetGroup(TypedDict):
    card: tk.Frame
    status: tk.Label
    drop: DragDropFrame
    files: tk.Label
    skip_button: CustomButton | None

class ProcessTriageApp(TkinterDnD.Tk):
    """Aplicação principal."""

    def __init__(self):
        super().__init__()

        self.title("🔄 Processo de Triagem - Robô de Classificação")
        self.geometry("1380x980")
        self.minsize(1180, 820)
        self.resizable(True, True)
        self.config(bg=_color("white", "#ffffff"))

        try:
            self.state("zoomed")
        except Exception:
            pass

        try:
            self.iconbitmap("icon.ico")
        except Exception:
            pass

        self.processing = False
        self.last_audit_dir: str | None = None
        self.last_log_file: str | None = None
        self.last_markdown_summary_file: str | None = None
        self.diagnostic_mode_var = tk.BooleanVar(value=False)

        self.selected_files: dict[str, list[str]] = build_empty_selected_files()
        self.source_skipped: dict[str, bool] = build_empty_skipped_sources()

        self.source_widgets: dict[str, SourceWidgetGroup] = {}

        self.process_handler = ProcessHandler(
            callback_progress=self._update_progress,
            callback_status=self._update_status,
            callback_log=self._add_log,
            callback_complete=self._on_complete,
        )

        self._build_ui()

    def _build_ui(self):
        header = tk.Frame(self, bg=_color("primary", "#2563eb"), height=84)
        header.pack(fill="x")
        header.pack_propagate(False)

        header_left = tk.Frame(header, bg=_color("primary", "#2563eb"))
        header_left.pack(side="left", fill="y", padx=_dim("padding", 16), pady=_dim("padding", 16))

        tk.Label(
            header_left,
            text="🔄 Processo de Triagem - Robô",
            font=_font("title", ("Segoe UI", 16, "bold")),
            bg=_color("primary", "#2563eb"),
            fg=_color("white", "#ffffff"),
        ).pack(anchor="w")

        tk.Label(
            header_left,
            text="Selecione cada base por tipo — sem depender do nome do arquivo",
            font=_font("small", ("Segoe UI", 9)),
            bg=_color("primary", "#2563eb"),
            fg=_color("white", "#ffffff"),
        ).pack(anchor="w")

        canvas_frame = tk.Frame(self, bg=_color("white", "#ffffff"))
        canvas_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            canvas_frame,
            bg=_color("white", "#ffffff"),
            highlightthickness=0,
        )
        self.v_scroll = tk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.h_scroll = tk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)

        self.scrollable_frame = tk.Frame(self.canvas, bg=_color("white", "#ffffff"))

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.configure(
            yscrollcommand=self.v_scroll.set,
            xscrollcommand=self.h_scroll.set,
        )

        self.canvas.pack(side="left", fill="both", expand=True)
        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll.pack(fill="x")

        def _resize_scrollable_frame(event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)

        self.canvas.bind("<Configure>", _resize_scrollable_frame)

        def _on_mousewheel(event):
            try:
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self.main_frame = self.scrollable_frame
        self.main_frame.config(
            padx=_dim("padding", 16),
            pady=_dim("padding", 16),
        )

        self.upload_frame = tk.Frame(self.main_frame, bg=_color("white", "#ffffff"))
        self.upload_frame.pack(fill="both", expand=True)

        tk.Label(
            self.upload_frame,
            text="1. Informe as bases a processar",
            font=_font("heading", ("Segoe UI", 12, "bold")),
            bg=_color("white", "#ffffff"),
            fg=_color("dark", "#111827"),
        ).pack(anchor="w", pady=(0, 8))

        tk.Label(
            self.upload_frame,
            text="Selecione cada base no bloco correto. O robô cuidará dos nomes internos automaticamente.",
            font=_font("small", ("Segoe UI", 9)),
            bg=_color("white", "#ffffff"),
            fg=_color("secondary", "#6b7280"),
        ).pack(anchor="w", pady=(0, 14))

        info_box = tk.Frame(
            self.upload_frame,
            bg="#eff6ff",
            relief="solid",
            bd=1,
            highlightbackground="#bfdbfe",
            highlightthickness=1,
        )
        info_box.pack(fill="x", pady=(0, 16))

        tk.Label(
            info_box,
            text="ℹ️ Como funciona esta etapa",
            font=_font("normal", ("Segoe UI", 10, "bold")),
            bg="#eff6ff",
            fg="#1d4ed8",
        ).pack(anchor="w", padx=12, pady=(10, 6))

        info_text = (
            "• Não é necessário renomear os arquivos manualmente.\n"
            "• Basta inserir cada arquivo no bloco correspondente ao tipo da base.\n"
            "• Não é necessário limpar manualmente a pasta input/ antes de cada execução.\n"
            "• O robô substitui automaticamente os arquivos internos da execução anterior.\n"
            "• A saída agora é versionada automaticamente em output/runs/ e output/latest/.\n"
            "• A Base Legal One é obrigatória. As demais podem ser informadas ou marcadas como ausentes."
        )

        tk.Label(
            info_box,
            text=info_text,
            font=_font("small", ("Segoe UI", 9)),
            bg="#eff6ff",
            fg="#1e3a8a",
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=14, pady=(0, 10))

        for source_key in SOURCE_ORDER:
            self._build_source_card(source_key)

        self.summary_frame = tk.Frame(
            self.upload_frame,
            bg=_color("light", "#f3f4f6"),
            relief="solid",
            bd=1,
        )
        self.summary_frame.pack(fill="x", pady=(16, 8))

        tk.Label(
            self.summary_frame,
            text="📋 Resumo da seleção",
            font=_font("normal", ("Segoe UI", 10, "bold")),
            bg=_color("light", "#f3f4f6"),
            fg=_color("dark", "#111827"),
        ).pack(anchor="w", padx=12, pady=(10, 4))

        self.global_summary = tk.Label(
            self.summary_frame,
            text="Nenhuma base selecionada.",
            font=_font("small", ("Segoe UI", 9)),
            bg=_color("light", "#f3f4f6"),
            fg=_color("secondary", "#6b7280"),
            justify="left",
            anchor="w",
        )
        self.global_summary.pack(fill="x", padx=16, pady=(0, 10))

        actions_frame = tk.Frame(self.upload_frame, bg=_color("white", "#ffffff"))
        actions_frame.pack(fill="x", pady=10)

        CustomButton(
            actions_frame,
            text="🗑️ Limpar Tudo",
            style="secondary",
            command=self._clear_all_sources,
        ).pack(side="left", padx=(0, 8))

        execution_frame = tk.Frame(self.upload_frame, bg=_color("white", "#ffffff"))
        execution_frame.pack(fill="x", pady=20)

        tk.Label(
            execution_frame,
            text="2. Iniciar processamento",
            font=_font("heading", ("Segoe UI", 12, "bold")),
            bg=_color("white", "#ffffff"),
            fg=_color("dark", "#111827"),
        ).pack(anchor="w", pady=(0, 10))

        diagnostic_box = tk.Frame(
            execution_frame,
            bg="#f8fafc",
            relief="solid",
            bd=1,
            highlightbackground="#e2e8f0",
            highlightthickness=1,
        )
        diagnostic_box.pack(fill="x", pady=(0, 12))

        tk.Checkbutton(
            diagnostic_box,
            text="Executar em modo diagnóstico",
            variable=self.diagnostic_mode_var,
            bg="#f8fafc",
            fg="#0f172a",
            activebackground="#f8fafc",
            activeforeground="#0f172a",
            selectcolor="#ffffff",
            font=_font("normal", ("Segoe UI", 10, "bold")),
            anchor="w",
            command=self._update_global_summary,
        ).pack(anchor="w", padx=12, pady=(10, 4))

        tk.Label(
            diagnostic_box,
            text=(
                "Quando ativado, o robô preserva mais evidências da execução, "
                "incluindo snapshot dos arquivos de entrada na pasta de auditoria."
            ),
            font=_font("small", ("Segoe UI", 9)),
            bg="#f8fafc",
            fg="#475569",
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=14, pady=(0, 10))

        self.run_button = CustomButton(
            execution_frame,
            text="▶️ INICIAR PROCESSAMENTO",
            style="success",
            command=self._on_run,
        )
        self.run_button.pack(fill="x", pady=(0, 10))

        tk.Label(
            execution_frame,
            text="A Base Legal One é obrigatória. As demais são opcionais.",
            font=_font("small", ("Segoe UI", 9)),
            bg=_color("white", "#ffffff"),
            fg=_color("secondary", "#6b7280"),
        ).pack(anchor="w")

        self.progress_frame = ProgressPanel(self.main_frame)
        self.progress_frame.pack(fill="both", expand=True)
        self.progress_frame.pack_forget()

        self.result_frame = ResultPanel(self.main_frame, path_click_callback=self._handle_result_path_click)
        self.result_frame.pack(fill="both", expand=True)
        self.result_frame.pack_forget()

        footer = tk.Frame(self, bg=_color("gray", "#e5e7eb"), height=42)
        footer.pack(fill="x")
        footer.pack_propagate(False)

        tk.Label(
            footer,
            text="✓ Robô validado e pronto para produção | v1.0",
            font=_font("small", ("Segoe UI", 9)),
            bg=_color("gray", "#e5e7eb"),
            fg=_color("secondary", "#6b7280"),
        ).pack(side="left", padx=_dim("padding", 16), pady=10)

        self._refresh_all_source_cards()
        self._update_global_summary()

    def _build_source_card(self, source_key: str):
        card = tk.Frame(
            self.upload_frame,
            bg=_color("white", "#ffffff"),
            relief="solid",
            bd=1,
            highlightbackground=_color("gray", "#d1d5db"),
            highlightthickness=1,
        )
        card.pack(fill="x", pady=8)

        top = tk.Frame(card, bg=_color("white", "#ffffff"))
        top.pack(fill="x", padx=12, pady=(12, 6))

        title = get_source_label(source_key)
        if not is_source_optional(source_key):
            title += " *"

        tk.Label(
            top,
            text=title,
            font=_font("heading", ("Segoe UI", 11, "bold")),
            bg=_color("white", "#ffffff"),
            fg=_color("dark", "#111827"),
        ).pack(anchor="w")

        tk.Label(
            top,
            text=get_source_description(source_key),
            font=_font("small", ("Segoe UI", 9)),
            bg=_color("white", "#ffffff"),
            fg=_color("secondary", "#6b7280"),
        ).pack(anchor="w", pady=(4, 0))

        status_label = tk.Label(
            card,
            text="",
            font=_font("small", ("Segoe UI", 9, "bold")),
            bg=_color("white", "#ffffff"),
            fg=_color("secondary", "#6b7280"),
            anchor="w",
            justify="left",
        )
        status_label.pack(fill="x", padx=12, pady=(0, 4))

        drop = DragDropFrame(
            card,
            callback=lambda files=None, sk=source_key: self._on_select_source_files(sk, files),
            label=f"Arraste aqui os arquivos de {get_source_label(source_key)} ou clique",
            height=150,
        )
        drop.pack(fill="x", padx=12, pady=(0, 8))

        files_label = tk.Label(
            card,
            text="Nenhum arquivo informado.",
            font=_font("small", ("Segoe UI", 9)),
            bg=_color("white", "#ffffff"),
            fg=_color("secondary", "#6b7280"),
            justify="left",
            anchor="w",
        )
        files_label.pack(fill="x", padx=14, pady=(0, 8))

        buttons = tk.Frame(card, bg=_color("white", "#ffffff"))
        buttons.pack(fill="x", padx=12, pady=(0, 12))

        add_text = "Selecionar arquivo" if get_source_max_files(source_key) == 1 else "Adicionar arquivo(s)"
        CustomButton(
            buttons,
            text=f"📂 {add_text}",
            style="primary",
            command=lambda sk=source_key: self._on_select_source_files(sk),
        ).pack(side="left", padx=(0, 8))

        CustomButton(
            buttons,
            text="🗑️ Limpar",
            style="secondary",
            command=lambda sk=source_key: self._clear_source(sk),
        ).pack(side="left", padx=(0, 8))

        skip_button = None
        if is_source_optional(source_key):
            skip_button = CustomButton(
                buttons,
                text="🚫 Não tenho essa base",
                style="secondary",
                command=lambda sk=source_key: self._skip_source(sk),
            )
            skip_button.pack(side="left", padx=(0, 8))

        self.source_widgets[source_key] = {
            "card": card,
            "status": status_label,
            "drop": drop,
            "files": files_label,
            "skip_button": skip_button,
        }

    def _on_select_source_files(self, source_key: str, dropped_files=None):
        if dropped_files:
            files = dropped_files
        else:
            files = FileHandler.select_files()

        if not files:
            return

        limit = get_source_max_files(source_key)
        current = list(self.selected_files[source_key])

        for f in files:
            if f not in current:
                current.append(f)

        if len(current) > limit:
            current = current[:limit]
            messagebox.showinfo(
                "Limite de arquivos",
                f"A fonte '{get_source_label(source_key)}' aceita no máximo {limit} arquivo(s)."
            )

        self.selected_files[source_key] = current
        self.source_skipped[source_key] = False

        self._refresh_source_card(source_key)
        self._update_global_summary()

    def _clear_source(self, source_key: str):
        self.selected_files[source_key] = []
        self.source_skipped[source_key] = False
        self._refresh_source_card(source_key)
        self._update_global_summary()

    def _skip_source(self, source_key: str):
        self.selected_files[source_key] = []
        self.source_skipped[source_key] = True
        self._refresh_source_card(source_key)
        self._update_global_summary()

    def _clear_all_sources(self):
        self.selected_files = build_empty_selected_files()
        self.source_skipped = build_empty_skipped_sources()

        self._refresh_all_source_cards()
        self._update_global_summary()

    def _refresh_all_source_cards(self):
        for key in SOURCE_ORDER:
            self._refresh_source_card(key)

    def _refresh_source_card(self, source_key: str):
        widgets = self.source_widgets[source_key]
        files = self.selected_files[source_key]
        skipped = self.source_skipped[source_key]
        limit = get_source_max_files(source_key)

        if skipped:
            status_text = "Status: AUSENTE NESTA EXECUÇÃO"
            status_fg = _color("warning", "#d97706")
            files_text = "Esta base foi marcada como não informada."
            files_fg = _color("warning", "#d97706")
            widgets["drop"].set_files([])
        elif files:
            status_text = f"Status: {len(files)}/{limit} arquivo(s) informado(s)"
            status_fg = _color("success", "#16a34a")
            files_text = "\n".join([f"  ✓ {Path(f).name}" for f in files])
            files_fg = _color("dark", "#111827")
            widgets["drop"].set_files(files)
        else:
            if is_source_optional(source_key):
                status_text = "Status: opcional, ainda não informado"
                status_fg = _color("secondary", "#6b7280")
            else:
                status_text = "Status: obrigatório, aguardando arquivo"
                status_fg = _color("danger", "#dc2626")

            files_text = "Nenhum arquivo informado."
            files_fg = _color("secondary", "#6b7280")
            widgets["drop"].set_files([])

        widgets["status"].config(text=status_text, fg=status_fg)
        widgets["files"].config(text=files_text, fg=files_fg)

    def _update_global_summary(self):
        lines = []
        total_files = 0

        for key in SOURCE_ORDER:
            label = get_source_label(key)
            files = self.selected_files[key]
            skipped = self.source_skipped[key]

            if skipped:
                lines.append(f"• {label}: AUSENTE NESTA EXECUÇÃO")
            elif files:
                total_files += len(files)
                lines.append(f"• {label}: {len(files)} arquivo(s)")
            else:
                if is_source_optional(key):
                    lines.append(f"• {label}: não informado")
                else:
                    lines.append(f"• {label}: obrigatório pendente")

        lines.append(f"\nTotal de arquivos selecionados: {total_files}")
        lines.append(f"Modo diagnóstico: {'ATIVADO' if self.diagnostic_mode_var.get() else 'desativado'}")
        self.global_summary.config(text="\n".join(lines))

    def _validate_before_run(self) -> bool:
        if not self.selected_files["legalone"]:
            messagebox.showwarning(
                "Aviso",
                "A Base Legal One é obrigatória. Selecione um arquivo antes de continuar."
            )
            return False

        total_selected = sum(len(v) for v in self.selected_files.values())
        if total_selected == 0:
            messagebox.showwarning(
                "Aviso",
                "Nenhum arquivo foi selecionado para processamento."
            )
            return False

        return True

    def _build_run_preview(self) -> str:
        lines = []

        for key in SOURCE_ORDER:
            label = get_source_label(key)
            files = self.selected_files[key]
            skipped = self.source_skipped[key]

            if skipped:
                lines.append(f"- {label}: AUSENTE")
            elif files:
                names = ", ".join(Path(f).name for f in files)
                lines.append(f"- {label}: {names}")
            else:
                lines.append(f"- {label}: não informado")

        lines.append("")
        lines.append(f"Modo diagnóstico: {'SIM' if self.diagnostic_mode_var.get() else 'NÃO'}")
        return "\n".join(lines)

    def _on_run(self):
        if self.processing:
            return

        if not self._validate_before_run():
            return

        preview = self._build_run_preview()

        response = messagebox.askyesno(
            "Confirmar",
            f"Deseja iniciar o processamento com as seguintes bases?\n\n{preview}"
        )
        if not response:
            return

        self.processing = True
        self.run_button.config(state="disabled")
        self.last_audit_dir = None
        self.last_log_file = None
        self.last_markdown_summary_file = None

        self.result_frame.clear_results()
        self.progress_frame.clear_logs()
        self.progress_frame.update_progress(0)
        self.progress_frame.update_status("Iniciando...")

        self.upload_frame.pack_forget()
        self.result_frame.pack_forget()
        self.progress_frame.pack(fill="both", expand=True)
        self.update_idletasks()
        self.canvas.yview_moveto(0)
        self.after(10, lambda: self.canvas.yview_moveto(0))

        self.process_handler.start_processing(
            self.selected_files,
            diagnostic_mode=self.diagnostic_mode_var.get(),
        )

    def _update_progress(self, value):
        self.progress_frame.update_progress(value)

    def _update_status(self, text):
        self.progress_frame.update_status(text)

    def _add_log(self, message, tag="info"):
        self.progress_frame.add_log(message, tag)

    def _render_executive_cards(self, parent, results: dict):
        container = tk.Frame(parent, bg="#ffffff")
        container.pack(fill="x", pady=(0, 12))

        title = tk.Label(
            container,
            text="📌 Resumo executivo",
            font=_font("heading", ("Segoe UI", 11, "bold")),
            bg="#ffffff",
            fg="#111827",
        )
        title.pack(anchor="w", pady=(0, 8))

        cards_row = tk.Frame(container, bg="#ffffff")
        cards_row.pack(fill="x")

        def create_card(parent_frame, title_text, value_text, bg, fg, border):
            card = tk.Frame(
                parent_frame,
                bg=bg,
                relief="solid",
                bd=1,
                highlightbackground=border,
                highlightthickness=1,
            )
            card.pack(side="left", fill="both", expand=True, padx=(0, 8), ipadx=8, ipady=6)

            tk.Label(
                card,
                text=title_text,
                font=_font("small", ("Segoe UI", 9, "bold")),
                bg=bg,
                fg=fg,
                anchor="w",
            ).pack(anchor="w", padx=12, pady=(10, 2))

            tk.Label(
                card,
                text=str(value_text),
                font=_font("title", ("Segoe UI", 15, "bold")),
                bg=bg,
                fg=fg,
                anchor="w",
            ).pack(anchor="w", padx=12, pady=(0, 10))

            return card

        saude = results.get("Saúde da execução", "-")
        alta = results.get("Alertas alta severidade", 0)
        media = results.get("Alertas média severidade", 0)
        baixa = results.get("Alertas baixa severidade", 0)

        bg, fg, border = health_card_colors(saude)
        create_card(cards_row, "Saúde da execução", saude, bg, fg, border)
        create_card(cards_row, "Alertas alta severidade", alta, "#fef2f2", "#b91c1c", "#fecaca")
        create_card(cards_row, "Alertas média severidade", media, "#fff7ed", "#c2410c", "#fdba74")
        create_card(cards_row, "Alertas baixa severidade", baixa, "#fefce8", "#a16207", "#fde68a")

    def _render_alerts_panel(self, parent, results: dict):
        alert_text = results.get("Alertas de regressão", "")
        alert_count = results.get("Quantidade de alertas", 0)

        panel = tk.Frame(
            parent,
            bg="#ffffff",
            relief="solid",
            bd=1,
            highlightbackground="#d1d5db",
            highlightthickness=1,
        )
        panel.pack(fill="x", pady=(0, 12))

        header = tk.Frame(panel, bg="#ffffff")
        header.pack(fill="x", padx=12, pady=(10, 8))

        tk.Label(
            header,
            text="🚨 Alertas da execução",
            font=_font("heading", ("Segoe UI", 11, "bold")),
            bg="#ffffff",
            fg="#111827",
        ).pack(side="left")

        count_bg = "#e5e7eb"
        count_fg = "#374151"

        try:
            count_num = int(alert_count)
        except Exception:
            count_num = 0

        if count_num > 0:
            count_bg = "#fee2e2"
            count_fg = "#991b1b"

        tk.Label(
            header,
            text=f"{count_num} alerta(s)",
            font=_font("small", ("Segoe UI", 9, "bold")),
            bg=count_bg,
            fg=count_fg,
            padx=8,
            pady=3,
        ).pack(side="right")

        lines = extract_alert_lines(alert_text)

        if not lines:
            empty = tk.Label(
                panel,
                text="Nenhum alerta relevante para exibir.",
                font=_font("small", ("Segoe UI", 9)),
                bg="#ffffff",
                fg="#6b7280",
                anchor="w",
                justify="left",
            )
            empty.pack(fill="x", padx=14, pady=(0, 12))
            return

        for sev, text in lines:
            bg, fg, border = severity_colors(sev)

            item = tk.Frame(
                panel,
                bg=bg,
                relief="solid",
                bd=1,
                highlightbackground=border,
                highlightthickness=1,
            )
            item.pack(fill="x", padx=12, pady=(0, 8))

            left = tk.Frame(item, bg=bg)
            left.pack(fill="both", expand=True, padx=10, pady=8)

            badge_text = sev.upper() if sev in {"alta", "media", "baixa"} else "INFO"

            badge = tk.Label(
                left,
                text=badge_text,
                font=_font("small", ("Segoe UI", 8, "bold")),
                bg=fg,
                fg="#ffffff",
                padx=8,
                pady=2,
            )
            badge.pack(anchor="w", pady=(0, 6))

            tk.Label(
                left,
                text=text,
                font=_font("small", ("Segoe UI", 9)),
                bg=bg,
                fg=fg,
                anchor="w",
                justify="left",
                wraplength=1100,
            ).pack(fill="x")

    def _on_complete(self, results):
        self.processing = False
        self.run_button.config(state="normal")

        if results:
            self.last_audit_dir = results.get("Pasta da auditoria")
            self.last_log_file = results.get("Log da execução")

            if self.last_audit_dir:
                markdown_path = Path(self.last_audit_dir) / "resumo_execucao.md"
                self.last_markdown_summary_file = str(markdown_path) if markdown_path.exists() else None
            else:
                self.last_markdown_summary_file = None

            self.progress_frame.pack_forget()
            self._show_results(results)
        else:
            messagebox.showerror(
                "Erro",
                "Houve um erro no processamento. Verifique os logs e tente novamente."
            )
            self.progress_frame.pack_forget()
            self.upload_frame.pack(fill="both", expand=True)

    def _show_results(self, results):
        self.update_idletasks()
        self.canvas.yview_moveto(0)
        self.after(10, lambda: self.canvas.yview_moveto(0))
        self.result_frame.clear_results()
        self.result_frame.pack(fill="both", expand=True)

        self._render_executive_cards(self.result_frame, results)
        self._render_alerts_panel(self.result_frame, results)

        if isinstance(results, dict):
            self.result_frame.set_summary_cards(results)
            for key, value in results.items():
                self.result_frame.add_result(key, value)

        for widget in self.result_frame.button_frame.winfo_children():
            widget.destroy()

        actions_row = tk.Frame(self.result_frame.button_frame, bg=_color("white", "#ffffff"))
        actions_row.pack(fill="x", pady=(0, 10))

        reset_row = tk.Frame(self.result_frame.button_frame, bg=_color("white", "#ffffff"))
        reset_row.pack(fill="x")

        CustomButton(
            actions_row,
            text="📂 Abrir Resultado Atual",
            style="primary",
            command=self._open_output,
        ).pack(side="left", padx=(0, 8), pady=4)

        CustomButton(
            actions_row,
            text="🗂️ Abrir Histórico de Resultados",
            style="secondary",
            command=self._open_runs_dir,
        ).pack(side="left", padx=(0, 8), pady=4)

        CustomButton(
            actions_row,
            text="📁 Abrir Pasta da Auditoria",
            style="primary",
            command=self._open_audit_dir,
        ).pack(side="left", padx=(0, 8), pady=4)

        CustomButton(
            actions_row,
            text="📄 Abrir Resumo Markdown",
            style="secondary",
            command=self._open_markdown_summary,
        ).pack(side="left", padx=(0, 8), pady=4)

        CustomButton(
            actions_row,
            text="📝 Abrir Log da Execução",
            style="secondary",
            command=self._open_log_file,
        ).pack(side="left", padx=(0, 8), pady=4)

        CustomButton(
            actions_row,
            text="🗂️ Abrir Pasta do Histórico Técnico",
            style="secondary",
            command=self._open_history_dir,
        ).pack(side="left", padx=(0, 8), pady=4)

        CustomButton(
            actions_row,
            text="📊 Abrir Histórico Excel",
            style="secondary",
            command=self._open_history_file,
        ).pack(side="left", padx=(0, 8), pady=4)

        CustomButton(
            reset_row,
            text="🔄 Novo Processamento",
            style="success",
            command=self._reset,
        ).pack(anchor="e", pady=4)

    def _open_path(self, path_str: str | None):
        if not path_str:
            messagebox.showwarning("Aviso", "Caminho não disponível para esta execução.")
            return

        path = Path(path_str)
        if not path.exists():
            messagebox.showerror("Erro", f"O caminho não foi encontrado:\n{path}")
            return

        try:
            if sys.platform == "win32":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir o caminho:\n{e}")

    def _get_output_root_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent / "output"

    def _get_latest_output_dir(self) -> Path:
        return self._get_output_root_dir() / "latest"

    def _get_runs_dir(self) -> Path:
        return self._get_output_root_dir() / "runs"

    def _get_history_dir(self) -> Path:
        return self._get_output_root_dir() / "_historico_execucoes"

    def _get_history_excel_file(self) -> Path:
        return self._get_history_dir() / "historico_execucoes.xlsx"

    def _get_history_csv_file(self) -> Path:
        return self._get_history_dir() / "historico_execucoes.csv"

    def _open_runs_dir(self):
        runs_dir = self._get_runs_dir()
        runs_dir.mkdir(parents=True, exist_ok=True)
        self._open_path(str(runs_dir))

    def _open_history_dir(self):
        history_dir = self._get_history_dir()
        history_dir.mkdir(parents=True, exist_ok=True)
        self._open_path(str(history_dir))

    def _open_history_file(self):
        history_xlsx = self._get_history_excel_file()
        history_csv = self._get_history_csv_file()

        if history_xlsx.exists():
            self._open_path(str(history_xlsx))
            return

        if history_csv.exists():
            self._open_path(str(history_csv))
            return

        messagebox.showwarning(
            "Aviso",
            "Nenhum arquivo de histórico foi encontrado ainda. Execute o robô ao menos uma vez."
        )

    def _open_audit_dir(self):
        self._open_path(self.last_audit_dir)

    def _open_log_file(self):
        self._open_path(self.last_log_file)

    def _open_markdown_summary(self):
        self._open_path(self.last_markdown_summary_file)

    def _open_output(self):
        latest_dir = self._get_latest_output_dir()
        latest_dir.mkdir(parents=True, exist_ok=True)
        self._open_path(str(latest_dir))

    def _handle_result_path_click(self, label, value):
        key = str(label).strip().lower()

        if "pasta da auditoria" in key:
            self._open_audit_dir()
        elif "log da execução" in key:
            self._open_log_file()
        elif "localização" in key:
            self._open_output()

    def _reset(self):
        self.update_idletasks()
        self.canvas.yview_moveto(0)
        self.after(10, lambda: self.canvas.yview_moveto(0))
        self.result_frame.pack_forget()
        self.progress_frame.pack_forget()

        self.last_audit_dir = None
        self.last_log_file = None
        self.last_markdown_summary_file = None
        self.diagnostic_mode_var.set(False)

        self.selected_files = build_empty_selected_files()
        self.source_skipped = build_empty_skipped_sources()

        self._refresh_all_source_cards()
        self._update_global_summary()

        self.upload_frame.pack(fill="both", expand=True)


def run_app():
    app = ProcessTriageApp()
    app.mainloop()