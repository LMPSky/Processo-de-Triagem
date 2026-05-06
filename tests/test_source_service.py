from ui.source_service import SourceService


def test_count_selected_files():
    service = SourceService()

    selected_files = {
        "legalone": ["a.csv"],
        "webjur": ["b.csv", "c.csv"],
        "dw": [],
        "painel": None,
    }

    result = service.count_selected_files(selected_files)

    assert result == 3


def test_build_sources_summary_includes_counts_and_labels():
    service = SourceService()

    selected_files = {
        "legalone": ["C:/tmp/legalone.csv"],
        "webjur": ["C:/tmp/webjur1.csv", "C:/tmp/webjur2.csv"],
        "dw": [],
        "painel": [],
    }

    result = service.build_sources_summary(selected_files)

    assert "legalone" in result
    assert "webjur" in result
    assert result["legalone"]["count"] == 1
    assert result["webjur"]["count"] == 2
    assert result["dw"]["count"] == 0
    assert isinstance(result["legalone"]["label"], str)

    normalized_files = [path.replace("\\", "/") for path in result["legalone"]["files"]]
    assert normalized_files == ["C:/tmp/legalone.csv"]


def test_build_result_source_lists_returns_informed_absent_and_details():
    service = SourceService()

    selected_files = {
        "legalone": ["legalone.csv"],
        "webjur": ["webjur.csv"],
        "dw": [],
        "painel": [],
    }

    informed_text, absent_text, detail_text = service.build_result_source_lists(selected_files)

    assert isinstance(informed_text, str)
    assert isinstance(absent_text, str)
    assert isinstance(detail_text, str)
    assert "arquivo(s)" in detail_text
    assert "ausente" in detail_text