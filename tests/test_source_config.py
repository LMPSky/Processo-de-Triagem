from ui.source_config import (
    SOURCE_ORDER,
    SOURCES,
    build_empty_selected_files,
    build_empty_skipped_sources,
    get_source_config,
    get_source_description,
    get_source_internal_filenames,
    get_source_label,
    get_source_max_files,
    is_source_optional,
)


def test_source_order_is_not_empty():
    assert SOURCE_ORDER
    assert isinstance(SOURCE_ORDER, list)


def test_all_source_order_keys_exist_in_sources():
    for source_key in SOURCE_ORDER:
        assert source_key in SOURCES


def test_all_sources_have_required_fields():
    required_fields = {
        "label",
        "description",
        "optional",
        "max_files",
        "internal_filenames",
    }

    for source_key in SOURCE_ORDER:
        config = get_source_config(source_key)
        assert required_fields.issubset(config.keys())


def test_all_sources_have_valid_basic_types():
    for source_key in SOURCE_ORDER:
        config = get_source_config(source_key)

        assert isinstance(config["label"], str)
        assert config["label"].strip()

        assert isinstance(config["description"], str)
        assert config["description"].strip()

        assert isinstance(config["optional"], bool)

        assert isinstance(config["max_files"], int)
        assert config["max_files"] >= 1

        assert isinstance(config["internal_filenames"], list)
        assert config["internal_filenames"]


def test_internal_filenames_match_max_files():
    for source_key in SOURCE_ORDER:
        max_files = get_source_max_files(source_key)
        internal_filenames = get_source_internal_filenames(source_key)

        assert len(internal_filenames) == max_files


def test_getters_return_expected_values():
    for source_key in SOURCE_ORDER:
        assert get_source_label(source_key) == SOURCES[source_key]["label"]
        assert get_source_description(source_key) == SOURCES[source_key]["description"]
        assert is_source_optional(source_key) == SOURCES[source_key]["optional"]
        assert get_source_max_files(source_key) == SOURCES[source_key]["max_files"]
        assert get_source_internal_filenames(source_key) == SOURCES[source_key]["internal_filenames"]


def test_build_empty_selected_files_creates_all_sources():
    result = build_empty_selected_files()

    assert isinstance(result, dict)
    assert set(result.keys()) == set(SOURCE_ORDER)

    for source_key in SOURCE_ORDER:
        assert result[source_key] == []


def test_build_empty_skipped_sources_creates_all_sources():
    result = build_empty_skipped_sources()

    assert isinstance(result, dict)
    assert set(result.keys()) == set(SOURCE_ORDER)

    for source_key in SOURCE_ORDER:
        assert result[source_key] is False