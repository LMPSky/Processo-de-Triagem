"""
Helpers visuais para renderização de resultados e alertas.
"""


def severity_colors(severity: str) -> tuple[str, str, str]:
    sev = str(severity).strip().lower()

    if sev == "alta":
        return ("#fef2f2", "#dc2626", "#fecaca")
    if sev == "media":
        return ("#fff7ed", "#ea580c", "#fdba74")
    if sev == "baixa":
        return ("#fefce8", "#a16207", "#fde68a")

    return ("#f8fafc", "#475569", "#cbd5e1")


def health_card_colors(health: str) -> tuple[str, str, str]:
    value = str(health).strip().lower()

    if value == "saudável":
        return ("#ecfdf5", "#047857", "#a7f3d0")
    if value == "atenção":
        return ("#fff7ed", "#c2410c", "#fdba74")
    if value == "crítica":
        return ("#fef2f2", "#b91c1c", "#fecaca")

    return ("#f8fafc", "#475569", "#cbd5e1")


def extract_alert_lines(alert_text: str) -> list[tuple[str, str]]:
    lines = []
    raw_lines = str(alert_text or "").splitlines()

    for line in raw_lines:
        cleaned = line.strip()
        if not cleaned:
            continue

        sev = "info"
        upper = cleaned.upper()

        if "[ALTA]" in upper:
            sev = "alta"
        elif "[MEDIA]" in upper:
            sev = "media"
        elif "[BAIXA]" in upper:
            sev = "baixa"

        lines.append((sev, cleaned))

    return lines