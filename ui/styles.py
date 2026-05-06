"""
Definição de cores, fontes e estilos da UI.
"""

# ═══════════════════════════════════════════════════════════
# CORES
# ═══════════════════════════════════════════════════════════

COLORS = {
    # Primárias
    "primary": "#0066CC",        # Azul
    "secondary": "#6C757D",      # Cinza
    "success": "#28A745",        # Verde
    "warning": "#FFC107",        # Amarelo
    "danger": "#DC3545",         # Vermelho
    "info": "#17A2B8",           # Ciano
    
    # Neutras
    "white": "#FFFFFF",
    "black": "#000000",
    "dark": "#1A1A1A",
    "light": "#F8F9FA",
    "gray": "#E9ECEF",
    
    # Estados
    "hover": "#004FA3",          # Azul escuro
    "active": "#003D82",
    "disabled": "#CCCCCC",
}

# ═══════════════════════════════════════════════════════════
# FONTES
# ═══════════════════════════════════════════════════════════

FONTS = {
    "title": ("Segoe UI", 16, "bold"),
    "heading": ("Segoe UI", 12, "bold"),
    "normal": ("Segoe UI", 10),
    "small": ("Segoe UI", 9),
    "mono": ("Courier New", 9),
}

# ═══════════════════════════════════════════════════════════
# DIMENSÕES
# ════════════��══════════════════════════════════════════════

DIMENSIONS = {
    "padding": 15,
    "spacing": 10,
    "border_radius": 5,
    "button_height": 40,
    "input_height": 35,
}

# ═══════════════════════════════════════════════════════════
# ESTILOS DE BOTÃO
# ═══════════════════════════════════════════════════════════

BUTTON_STYLES = {
    "primary": {
        "bg": COLORS["primary"],
        "fg": COLORS["white"],
        "activebackground": COLORS["hover"],
        "activeforeground": COLORS["white"],
        "relief": "flat",
        "bd": 0,
        "cursor": "hand2",
    },
    "success": {
        "bg": COLORS["success"],
        "fg": COLORS["white"],
        "activebackground": "#1E7E34",
        "activeforeground": COLORS["white"],
        "relief": "flat",
        "bd": 0,
        "cursor": "hand2",
    },
    "danger": {
        "bg": COLORS["danger"],
        "fg": COLORS["white"],
        "activebackground": "#C82333",
        "activeforeground": COLORS["white"],
        "relief": "flat",
        "bd": 0,
        "cursor": "hand2",
    },
    "secondary": {
        "bg": COLORS["secondary"],
        "fg": COLORS["white"],
        "activebackground": "#5A6268",
        "activeforeground": COLORS["white"],
        "relief": "flat",
        "bd": 0,
        "cursor": "hand2",
    },
}