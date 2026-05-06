import json

import pytest

from ui.handlers import ProcessHandler


@pytest.fixture
def handler():
    instance = ProcessHandler(
        callback_progress=lambda value: None,
        callback_status=lambda text: None,
        callback_log=lambda message, tag="info": None,
        callback_complete=lambda result: None,
    )

    def _load_json(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    setattr(instance, "_load_json", _load_json)
    return instance