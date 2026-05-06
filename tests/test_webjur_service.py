from pathlib import Path

from ui.webjur_service import WebjurService


def test_remove_previous_derivatives_removes_sanitized_and_ruins(tmp_path):
    service = WebjurService()

    original = tmp_path / "webjur.csv"
    sanitized = tmp_path / "webjur_SANITIZADO.csv"
    ruins = tmp_path / "webjur_SANITIZADO_RUINS.csv"

    original.write_text("original", encoding="utf-8")
    sanitized.write_text("sanitizado", encoding="utf-8")
    ruins.write_text("ruins", encoding="utf-8")

    service.remove_previous_derivatives(original)

    assert not sanitized.exists()
    assert not ruins.exists()
    assert original.exists()


def test_sanitize_csv_returns_false_when_exception_occurs(monkeypatch, tmp_path):
    service = WebjurService()

    file_path = tmp_path / "webjur.csv"
    file_path.write_text("conteudo", encoding="utf-8")

    def fake_sanitize_webjur_file(path, sanitized_path):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr("ui.webjur_service.sanitize_webjur_file", fake_sanitize_webjur_file)

    result = service.sanitize_csv(file_path)

    assert result is False


def test_sanitize_csv_returns_true_and_creates_expected_flow(monkeypatch, tmp_path):
    service = WebjurService()

    file_path = tmp_path / "webjur.csv"
    file_path.write_text("conteudo", encoding="utf-8")

    def fake_sanitize_webjur_file(path, sanitized_path):
        sanitized_path.write_text("sanitizado", encoding="utf-8")
        ruins_path = path.with_name(f"{path.stem}_SANITIZADO_RUINS.csv")
        ruins_path.write_text("linha ruim", encoding="utf-8")
        return {
            "metricas_colunas": [
                {"coluna": "data", "datas_detectadas": 10}
            ],
            "linhas_totais": 12,
            "col_data_idx": 0,
            "col_data_nome": "data",
            "linhas_validas": 10,
            "linhas_ruins": 2,
            "ruins_path": str(ruins_path),
        }

    monkeypatch.setattr("ui.webjur_service.sanitize_webjur_file", fake_sanitize_webjur_file)

    messages = []

    def fake_log(message, tag="info", log_file=None):
        messages.append((message, tag))

    result = service.sanitize_csv(file_path, safe_log=fake_log)

    assert result is True
    assert (tmp_path / "webjur_SANITIZADO.csv").exists()
    assert (tmp_path / "webjur_SANITIZADO_RUINS.csv").exists()
    assert any("Sanitizado" in message for message, _ in messages)
    assert any("Coluna real de data" in message for message, _ in messages)