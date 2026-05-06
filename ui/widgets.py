"""
Componentes reutilizáveis da interface.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Any, Callable

from tkinterdnd2 import DND_FILES

from .styles import COLORS, FONTS, DIMENSIONS



def _font(name: str, fallback):
    return FONTS.get(name, fallback)


def _color(name: str, fallback: str):
    return COLORS.get(name, fallback)


def _dim(name: str, fallback: int):
    return DIMENSIONS.get(name, fallback)


def _resolve_button_color(style: str | None) -> str:
    style = (style or "primary").lower()
    if style == "success":
        return _color("success", "#16a34a")
    if style == "secondary":
        return _color("secondary", "#6b7280")
    if style == "danger":
        return _color("danger", "#dc2626")
    return _color("primary", "#2563eb")


class CustomButton(tk.Button):
    """Botão customizado compatível com style='primary|secondary|success|danger'."""

    def __init__(
        self,
        parent,
        text: str,
        command: Any = None,
        style: str = "primary",
        color: str | None = None,
        **kwargs,
    ):
        bg = color or _resolve_button_color(style)

        super().__init__(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=_color("white", "#ffffff"),
            activebackground=bg,
            activeforeground=_color("white", "#ffffff"),
            font=_font("button", ("Segoe UI", 10, "bold")),
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            padx=18,
            pady=10,
            **kwargs,
        )

class DragDropFrame(tk.Frame):
    """
    Área de seleção/listagem de arquivos com suporte a drag-and-drop.
    """

    def __init__(self, parent, callback=None, label="Arraste os arquivos aqui ou clique", height=180, **kwargs):
        super().__init__(parent, bg=_color("white", "#ffffff"), height=height, **kwargs)

        self.callback = callback
        self.files: list[str] = []
        self.pack_propagate(False)

        self.outer = tk.Frame(
            self,
            bg=_color("light", "#f3f4f6"),
            bd=1,
            relief="solid",
            highlightbackground=_color("primary", "#2563eb"),
            highlightthickness=1,
        )
        self.outer.pack(fill="both", expand=True)

        self.inner = tk.Frame(self.outer, bg=_color("light", "#f3f4f6"))
        self.inner.pack(fill="both", expand=True, padx=20, pady=20)

        self.icon_label = tk.Label(
            self.inner,
            text="📂",
            font=("Segoe UI Emoji", 28),
            bg=_color("light", "#f3f4f6"),
            fg=_color("primary", "#2563eb"),
        )
        self.icon_label.pack(pady=(10, 5))

        self.label_widget = tk.Label(
            self.inner,
            text=label,
            font=_font("normal", ("Segoe UI", 10)),
            bg=_color("light", "#f3f4f6"),
            fg=_color("dark", "#111827"),
        )
        self.label_widget.pack(pady=(0, 6))

        self.sub_label = tk.Label(
            self.inner,
            text="Formatos aceitos: .csv e .xlsx",
            font=_font("small", ("Segoe UI", 9)),
            bg=_color("light", "#f3f4f6"),
            fg=_color("secondary", "#6b7280"),
        )
        self.sub_label.pack()

        self.files_preview = tk.Label(
            self.inner,
            text="",
            font=_font("small", ("Segoe UI", 9)),
            bg=_color("light", "#f3f4f6"),
            fg=_color("primary", "#2563eb"),
            justify="left",
        )
        self.files_preview.pack(pady=(12, 0))

        self.clickable_widgets = [
            self,
            self.outer,
            self.inner,
            self.icon_label,
            self.label_widget,
            self.sub_label,
            self.files_preview,
        ]

        for widget in self.clickable_widgets:
            widget.bind("<Button-1>", self._handle_click)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

        self._register_dnd()

    def _register_dnd(self):
        for widget in self.clickable_widgets:
            try:
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<DropEnter>>", self._on_drop_enter)
                widget.dnd_bind("<<DropLeave>>", self._on_drop_leave)
                widget.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass

    def _handle_click(self, event=None):
        if callable(self.callback):
            self.callback()

    def _on_enter(self, event=None):
        self.outer.config(
            highlightbackground=_color("success", "#16a34a"),
            highlightthickness=2,
        )

    def _on_leave(self, event=None):
        self.outer.config(
            highlightbackground=_color("primary", "#2563eb"),
            highlightthickness=1,
        )

    def _on_drop_enter(self, event=None):
        self.outer.config(
            highlightbackground=_color("success", "#16a34a"),
            highlightthickness=3,
        )
        return event.action if event else None

    def _on_drop_leave(self, event=None):
        self.outer.config(
            highlightbackground=_color("primary", "#2563eb"),
            highlightthickness=1,
        )
        return event.action if event else None

    def _parse_dropped_files(self, data: str) -> list[str]:
        if not data:
            return []

        files = []
        current = ""
        in_braces = False

        for ch in data:
            if ch == "{":
                in_braces = True
                if current.strip():
                    files.append(current.strip())
                    current = ""
            elif ch == "}":
                in_braces = False
                if current.strip():
                    files.append(current.strip())
                    current = ""
            elif ch == " " and not in_braces:
                if current.strip():
                    files.append(current.strip())
                    current = ""
            else:
                current += ch

        if current.strip():
            files.append(current.strip())

        cleaned = []
        for f in files:
            f = f.strip().strip('"').strip()
            if f:
                cleaned.append(str(Path(f)))

        return cleaned

    def _filter_supported_files(self, files: list[str]) -> list[str]:
        supported = []
        for f in files:
            suffix = Path(f).suffix.lower()
            if suffix in [".csv", ".xlsx"]:
                supported.append(f)
        return supported

    def _on_drop(self, event):
        self.outer.config(
            highlightbackground=_color("primary", "#2563eb"),
            highlightthickness=1,
        )

        raw_data = getattr(event, "data", "")
        dropped_files = self._parse_dropped_files(raw_data)
        dropped_files = self._filter_supported_files(dropped_files)

        if dropped_files and callable(self.callback):
            self.callback(dropped_files)

        return event.action

    def set_files(self, files: list[str]):
        self.files = files or []

        if not self.files:
            self.files_preview.config(text="")
            return

        names = []
        for file in self.files[:5]:
            try:
                names.append(f"• {Path(file).name}")
            except Exception:
                names.append(f"• {str(file)}")

        text = "\n".join(names)

        if len(self.files) > 5:
            text += f"\n... e mais {len(self.files) - 5} arquivo(s)"

        self.files_preview.config(text=text)

    def clear_files(self):
        self.files = []
        self.files_preview.config(text="")


class ProgressPanel(tk.Frame):
    """Seção de progresso e logs."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=_color("white", "#ffffff"), **kwargs)

        self.title = tk.Label(
            self,
            text="Processando...",
            font=_font("heading", ("Segoe UI", 12, "bold")),
            bg=_color("white", "#ffffff"),
            fg=_color("primary", "#2563eb"),
        )
        self.title.pack(anchor="w", padx=_dim("padding", 16), pady=(_dim("padding", 16), 8))

        self.progress = ttk.Progressbar(
            self,
            orient="horizontal",
            mode="determinate",
            length=400,
        )
        self.progress.pack(fill="x", padx=_dim("padding", 16), pady=(0, 8))

        self.status = tk.Label(
            self,
            text="Aguardando...",
            font=_font("normal", ("Segoe UI", 10)),
            bg=_color("white", "#ffffff"),
            fg=_color("secondary", "#6b7280"),
            anchor="w",
        )
        self.status.pack(fill="x", padx=_dim("padding", 16), pady=(0, 8))

        self.percent = tk.Label(
            self,
            text="0%",
            font=_font("normal", ("Segoe UI", 10)),
            bg=_color("white", "#ffffff"),
            fg=_color("primary", "#2563eb"),
            anchor="e",
        )
        self.percent.pack(fill="x", padx=_dim("padding", 16), pady=(0, 8))

        log_container = tk.Frame(self, bg=_color("white", "#ffffff"))
        log_container.pack(fill="both", expand=True, padx=_dim("padding", 16), pady=(0, _dim("padding", 16)))

        self.log_text = tk.Text(
            log_container,
            height=20,
            wrap="none",
            font=("Consolas", 10),
            bg="#111111",
            fg="#f0f0f0",
            insertbackground="#f0f0f0",
            relief="flat",
            borderwidth=0,
        )

        self.log_scroll_y = tk.Scrollbar(log_container, orient="vertical", command=self.log_text.yview)
        self.log_scroll_x = tk.Scrollbar(self, orient="horizontal", command=self.log_text.xview)

        self.log_text.configure(
            yscrollcommand=self.log_scroll_y.set,
            xscrollcommand=self.log_scroll_x.set,
        )

        self.log_text.pack(side="left", fill="both", expand=True)
        self.log_scroll_y.pack(side="right", fill="y")
        self.log_scroll_x.pack(fill="x", padx=_dim("padding", 16))

        self.log_text.tag_configure("info", foreground="#6ad1ff")
        self.log_text.tag_configure("success", foreground="#48d96f")
        self.log_text.tag_configure("warning", foreground="#ffd166")
        self.log_text.tag_configure("error", foreground="#ff6b6b")

    def update_progress(self, value: int):
        self.progress["value"] = value
        self.percent.config(text=f"{value}%")
        self.update_idletasks()

    def set_progress(self, value: int):
        self.update_progress(value)

    def update_status(self, text: str):
        self.status.config(text=text)
        self.update_idletasks()

    def set_status(self, text: str):
        self.update_status(text)

    def add_log(self, message: str, tag: str = "info"):
        self.log_text.insert(tk.END, f"• {message}\n", tag)
        self.log_text.see(tk.END)
        self.update_idletasks()

    def clear_logs(self):
        self.log_text.delete("1.0", tk.END)


class ResultPanel(tk.Frame):
    """Painel com resultados."""

    def __init__(self, parent, path_click_callback=None, **kwargs):
        super().__init__(parent, bg=_color("white", "#ffffff"), **kwargs)

        self.path_click_callback = path_click_callback

        self.title = tk.Label(
            self,
            text="✓ Processamento Concluído!",
            font=_font("heading", ("Segoe UI", 12, "bold")),
            bg=_color("white", "#ffffff"),
            fg=_color("success", "#16a34a"),
        )
        self.title.pack(anchor="w", padx=_dim("padding", 16), pady=_dim("padding", 16))

        self.results_container = tk.Frame(self, bg=_color("light", "#f3f4f6"))
        self.results_container.pack(fill="both", expand=True, padx=_dim("padding", 16), pady=_dim("padding", 16))

        self.canvas = tk.Canvas(
            self.results_container,
            bg=_color("light", "#f3f4f6"),
            highlightthickness=0,
        )
        self.scrollbar_y = tk.Scrollbar(self.results_container, orient="vertical", command=self.canvas.yview)
        self.scrollbar_x = tk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)

        self.content_frame = tk.Frame(self.canvas, bg=_color("light", "#f3f4f6"))

        self.content_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

        def _resize_content_frame(event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)

        self.canvas.bind("<Configure>", _resize_content_frame)

        self.canvas.configure(
            yscrollcommand=self.scrollbar_y.set,
            xscrollcommand=self.scrollbar_x.set,
        )

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar_y.pack(side="right", fill="y")
        self.scrollbar_x.pack(fill="x")

        self.summary_cards_frame = tk.Frame(self.content_frame, bg=_color("white", "#ffffff"))
        self.summary_cards_frame.pack(fill="x", padx=0, pady=(0, 8))

        self.results_frame = tk.Frame(self.content_frame, bg=_color("light", "#f3f4f6"))
        self.results_frame.pack(fill="both", expand=True)

        self.button_frame = tk.Frame(self.content_frame, bg=_color("white", "#ffffff"))
        self.button_frame.pack(fill="x", pady=(16, 0))

    def clear_results(self):
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        for widget in self.summary_cards_frame.winfo_children():
            widget.destroy()
        for widget in self.button_frame.winfo_children():
            widget.destroy()

    def _resolve_delta_card_style(self, value) -> tuple[str, str]:
        text = str(value).strip()

        if text.upper() == "N/D":
            return "#f3f4f6", "#6b7280"

        try:
            delta = float(text.replace("+", ""))
        except Exception:
            return "#f3f4f6", "#6b7280"

        if delta > 0:
            return "#fef2f2", "#b91c1c"
        if delta < 0:
            return "#ecfdf5", "#166534"
        return "#f3f4f6", "#374151"

    def _resolve_alert_card_style(self, value) -> tuple[str, str]:
        try:
            count = int(str(value).strip())
        except Exception:
            count = 0

        if count > 0:
            return "#fef2f2", "#b91c1c"
        return "#ecfdf5", "#166534"

    def _resolve_health_card_style(self, value) -> tuple[str, str]:
        value_text = str(value).strip().lower()

        if "saudável" in value_text:
            return "#ecfdf5", "#166534"
        if "atenção" in value_text:
            return "#fffbeb", "#b45309"
        if "crítica" in value_text:
            return "#fef2f2", "#b91c1c"

        return "#eef2ff", "#3730a3"

    def set_summary_cards(self, results: dict):
        for widget in self.summary_cards_frame.winfo_children():
            widget.destroy()

        health_value = results.get("Saúde da execução", "-")
        health_bg, health_fg = self._resolve_health_card_style(health_value)

        delta_sem_match = results.get("Δ Linhas sem_match", "N/D")
        delta_bg, delta_fg = self._resolve_delta_card_style(delta_sem_match)

        alert_count = results.get("Quantidade de alertas", 0)
        alert_bg, alert_fg = self._resolve_alert_card_style(alert_count)

        cards_data = [
            ("Status", results.get("Status", "-"), "#ecfdf5", "#166534"),
            ("Saúde", str(health_value), health_bg, health_fg),
            ("Alertas", str(alert_count), alert_bg, alert_fg),
            ("Δ sem_match", str(delta_sem_match), delta_bg, delta_fg),
        ]

        for idx, (title, value, bg, fg) in enumerate(cards_data):
            card = tk.Frame(
                self.summary_cards_frame,
                bg=bg,
                relief="flat",
                bd=0,
                highlightbackground="#e5e7eb",
                highlightthickness=1,
            )
            card.pack(side="left", fill="both", expand=True, padx=(0 if idx == 0 else 10, 0), pady=(0, 8))

            tk.Label(
                card,
                text=title,
                font=_font("small", ("Segoe UI", 9, "bold")),
                bg=bg,
                fg=fg,
                anchor="w",
            ).pack(anchor="w", padx=12, pady=(10, 4))

            tk.Label(
                card,
                text=str(value),
                font=_font("heading", ("Segoe UI", 11, "bold")),
                bg=bg,
                fg=fg,
                anchor="w",
                justify="left",
                wraplength=260,
            ).pack(anchor="w", padx=12, pady=(0, 10))

    def _is_alert_label(self, label: str) -> bool:
        key = str(label).strip().lower()
        return "alertas de regressão" in key or "quantidade de alertas" in key

    def _is_health_label(self, label: str) -> bool:
        key = str(label).strip().lower()
        return (
            "saúde da execução" in key
            or "tendência do sem_match" in key
            or "tendência dos arquivos gerados" in key
            or "nível de atenção" in key
        )

    def _resolve_health_style(self, label: str, value: object | None) -> tuple[str, str, str]:
        key = str(label).strip().lower()
        value_text = str(value).strip().lower()

        if "saúde da execução" in key:
            if "saudável" in value_text:
                return "#ecfdf5", "#166534", "#14532d"
            if "atenção" in value_text:
                return "#fffbeb", "#b45309", "#92400e"
            if "crítica" in value_text:
                return "#fef2f2", "#b91c1c", "#991b1b"

        if "nível de atenção" in key:
            if "baixo" in value_text:
                return "#ecfdf5", "#166534", "#14532d"
            if "moderado" in value_text:
                return "#fffbeb", "#b45309", "#92400e"
            if "alto" in value_text:
                return "#fef2f2", "#b91c1c", "#991b1b"

        if "tendência do sem_match" in key or "tendência dos arquivos gerados" in key:
            if "estável/melhorando" in value_text:
                return "#ecfdf5", "#166534", "#14532d"
            if "atenção" in value_text:
                return "#fffbeb", "#b45309", "#92400e"
            if "piora consistente" in value_text or "queda consistente" in value_text:
                return "#fef2f2", "#b91c1c", "#991b1b"
            if "sem base comparativa" in value_text:
                return "#f3f4f6", "#6b7280", "#4b5563"

        return "#eef2ff", "#3730a3", "#312e81"

    def _resolve_result_value_color(self, label: str, value=None) -> str:
        key = str(label).strip().lower()

        if self._is_health_label(label):
            _, _, value_fg = self._resolve_health_style(label, value)
            return value_fg

        if "status" in key:
            return _color("success", "#16a34a")
        if "fontes ausentes" in key:
            return "#d97706"
        if "pasta da auditoria" in key or "log da execução" in key or "localização" in key:
            return _color("primary", "#2563eb")
        if "fontes informadas" in key:
            return _color("success", "#16a34a")
        if "consolidados gerados" in key:
            return "#6d28d9"
        if "linhas consolidadas - sem_match" in key:
            return "#b45309"
        if "δ " in key or "Δ ".lower() in key.lower():
            return "#b45309"
        if self._is_alert_label(label):
            return "#b91c1c"

        return _color("dark", "#111827")

    def _resolve_result_label_color(self, label: str, value=None) -> str:
        key = str(label).strip().lower()

        if self._is_health_label(label):
            _, label_fg, _ = self._resolve_health_style(label, value)
            return label_fg

        if "status" in key:
            return _color("success", "#16a34a")
        if "fontes ausentes" in key:
            return "#b45309"
        if "pasta da auditoria" in key or "log da execução" in key or "localização" in key:
            return _color("primary", "#2563eb")
        if "consolidados gerados" in key:
            return "#6d28d9"
        if "linhas consolidadas - sem_match" in key:
            return "#b45309"
        if "δ " in key or "Δ ".lower() in key.lower():
            return "#92400e"
        if self._is_alert_label(label):
            return "#991b1b"

        return _color("secondary", "#6b7280")

    def _resolve_row_bg(self, label: str, value=None) -> str:
        key = str(label).strip().lower()

        if self._is_health_label(label):
            row_bg, _, _ = self._resolve_health_style(label, value)
            return row_bg

        if "status" in key:
            return "#ecfdf5"
        if "fontes ausentes" in key:
            return "#fffbeb"
        if "pasta da auditoria" in key or "log da execução" in key or "localização" in key:
            return "#eff6ff"
        if "consolidados gerados" in key:
            return "#f5f3ff"
        if "linhas consolidadas - sem_match" in key:
            return "#fffbeb"
        if "δ " in key or "Δ ".lower() in key.lower():
            return "#fff7ed"
        if self._is_alert_label(label):
            return "#fef2f2"

        return _color("light", "#f3f4f6")

    def _is_clickable_path_label(self, label: str) -> bool:
        key = str(label).strip().lower()
        return (
            "pasta da auditoria" in key
            or "log da execução" in key
            or "localização" in key
        )

    def add_result(self, label, value):
        row_bg = self._resolve_row_bg(label, value)
        label_fg = self._resolve_result_label_color(label, value)
        value_fg = self._resolve_result_value_color(label, value)
        is_clickable = self._is_clickable_path_label(label)
        is_alert = self._is_alert_label(label)
        is_health = self._is_health_label(label)

        row = tk.Frame(
            self.results_frame,
            bg=row_bg,
            relief="flat",
            bd=0,
            highlightbackground="#e5e7eb",
            highlightthickness=1,
        )
        row.pack(fill="x", pady=6, padx=10)

        inner = tk.Frame(row, bg=row_bg)
        inner.pack(fill="x", padx=12, pady=10)

        label_widget = tk.Label(
            inner,
            text=f"{label}:",
            font=_font("normal", ("Segoe UI", 10, "bold")),
            bg=row_bg,
            fg=label_fg,
            anchor="nw",
            justify="left",
            width=30,
        )
        label_widget.pack(side="left", anchor="nw")

        value_font = _font("normal", ("Segoe UI", 10))
        if is_alert or is_health:
            value_font = ("Segoe UI", 10, "bold")
        if is_clickable:
            value_font = ("Segoe UI", 10, "underline")

        value_widget = tk.Label(
            inner,
            text=str(value),
            font=value_font,
            bg=row_bg,
            fg=value_fg,
            anchor="w",
            justify="left",
            wraplength=900,
            cursor="hand2" if is_clickable else "arrow",
        )
        value_widget.pack(side="left", fill="x", expand=True)

        callback = self.path_click_callback
        if is_clickable and callback is not None:
            value_widget.bind(
                "<Button-1>",
                lambda e, lbl=label, val=value, cb=callback: cb(lbl, val)
            )
            value_widget.bind(
                "<Enter>",
                lambda e, w=value_widget: w.config(fg="#1d4ed8")
            )
            value_widget.bind(
                "<Leave>",
                lambda e, w=value_widget, color=value_fg: w.config(fg=color)
            )