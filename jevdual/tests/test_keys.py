import os

from jevdual import keys


def test_load_keys_from_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(keys, "KEY_DIR", tmp_path)
    for var in (
        "TYPESAFE_API_KEY",
        "MODEL_API_KEY",
        "OPENAI_API_KEY",
        "JEVDUAL_TEXT_BASE_URL",
        "JEVDUAL_TEXT_API_KEY",
        "JEVDUAL_TEXT_MODEL",
    ):
        monkeypatch.delenv(var, raising=False)
    (tmp_path / "META_MODEL_API_KEY").write_text("abc123\n")
    present = keys.load_keys()
    assert present == {"TYPESAFE_API_KEY": False, "MODEL_API_KEY": True, "OPENAI_API_KEY": False}
    assert os.environ["MODEL_API_KEY"] == "abc123"
    assert os.environ["JEVDUAL_TEXT_BASE_URL"] == keys.META_BASE_URL
    assert os.environ["JEVDUAL_TEXT_MODEL"] == keys.MUSE_CONTRIBUTOR
