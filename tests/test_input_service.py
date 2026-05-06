from pathlib import Path

from ui.input_service import InputService
from ui.source_config import SOURCE_ORDER, get_source_internal_filenames


def test_copy_file_preserving_encoding_csv(tmp_path):
    service = InputService()

    src = tmp_path / "origem.csv"
    dest = tmp_path / "destino.csv"

    src.write_text("coluna\nação\n", encoding="latin-1")

    service.copy_file_preserving_encoding(src, dest)

    assert dest.exists()
    assert dest.read_text(encoding="latin-1") == "coluna\nação\n"


def test_copy_file_preserving_encoding_non_csv(tmp_path):
    service = InputService()

    src = tmp_path / "origem.xlsx"
    dest = tmp_path / "destino.xlsx"

    src.write_bytes(b"fake-binary-content")

    service.copy_file_preserving_encoding(src, dest)

    assert dest.exists()
    assert dest.read_bytes() == b"fake-binary-content"


def test_remove_previous_internal_files_removes_files_and_calls_webjur_cleanup(tmp_path):
    service = InputService()

    input_dir = tmp_path / "input"
    input_dir.mkdir()

    created_files = []
    webjur_expected_names = set()

    for source_key in SOURCE_ORDER:
        for filename in get_source_internal_filenames(source_key):
            path = input_dir / filename
            path.write_text("teste", encoding="utf-8")
            created_files.append(path)

            if "webjur" in filename.lower():
                webjur_expected_names.add(filename)

    called_paths = []

    def remove_webjur_derivatives(path):
        called_paths.append(path)

    service.remove_previous_internal_files(
        input_dir=input_dir,
        remove_webjur_derivatives_func=remove_webjur_derivatives,
    )

    for path in created_files:
        assert not path.exists()

    called_names = {path.name for path in called_paths}
    assert webjur_expected_names.issubset(called_names)


def test_copy_selected_inputs_snapshot_creates_snapshot_files(tmp_path):
    service = InputService()

    original = tmp_path / "arquivo.csv"
    original.write_text("conteudo", encoding="utf-8")

    audit_dir = tmp_path / "audit"

    selected_files = {
        "legalone": [str(original)],
        "webjur": [],
        "dw": [],
        "painel": [],
    }

    service.copy_selected_inputs_snapshot(
        selected_files=selected_files,
        audit_dir=audit_dir,
        diagnostic_mode=True,
    )

    snapshot_file = audit_dir / "inputs_snapshot" / "legalone" / "01_arquivo.csv"
    assert snapshot_file.exists()
    assert snapshot_file.read_text(encoding="utf-8") == "conteudo"


def test_copy_selected_inputs_snapshot_does_nothing_when_diagnostic_disabled(tmp_path):
    service = InputService()

    original = tmp_path / "arquivo.csv"
    original.write_text("conteudo", encoding="utf-8")

    audit_dir = tmp_path / "audit"

    selected_files = {
        "legalone": [str(original)],
        "webjur": [],
        "dw": [],
        "painel": [],
    }

    service.copy_selected_inputs_snapshot(
        selected_files=selected_files,
        audit_dir=audit_dir,
        diagnostic_mode=False,
    )

    snapshot_dir = audit_dir / "inputs_snapshot"
    assert not snapshot_dir.exists()


def test_prepare_selected_sources_copies_and_sanitizes_webjur(tmp_path):
    service = InputService()

    input_dir = tmp_path / "input"
    input_dir.mkdir()

    legalone_src = tmp_path / "legalone.csv"
    webjur_src = tmp_path / "webjur.csv"

    legalone_src.write_text("legal", encoding="latin-1")
    webjur_src.write_text("webjur", encoding="latin-1")

    copied = []
    sanitized = []

    def copy_file(src, dest):
        copied.append((src.name, dest.name))
        dest.write_text(src.read_text(encoding="latin-1"), encoding="latin-1")

    def sanitize_webjur(dest, log_file=None):
        sanitized.append(dest.name)

    selected_files = {
        "legalone": [str(legalone_src)],
        "webjur": [str(webjur_src)],
        "dw": [],
        "painel": [],
    }

    prepared = service.prepare_selected_sources(
        selected_files=selected_files,
        input_dir=input_dir,
        copy_file_func=copy_file,
        sanitize_webjur_func=sanitize_webjur,
    )

    assert len(prepared) >= 2
    assert any(src == "legalone.csv" for src, _ in copied)
    assert any(src == "webjur.csv" for src, _ in copied)
    assert len(sanitized) == 1


def test_prepare_selected_sources_ignores_missing_file(tmp_path):
    service = InputService()

    input_dir = tmp_path / "input"
    input_dir.mkdir()

    selected_files = {
        "legalone": [str(tmp_path / "nao_existe.csv")],
        "webjur": [],
        "dw": [],
        "painel": [],
    }

    prepared = service.prepare_selected_sources(
        selected_files=selected_files,
        input_dir=input_dir,
    )

    assert prepared == []