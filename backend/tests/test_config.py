import importlib
import sys


def test_groq_settings_have_expected_defaults(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.delenv("CHAT_MAX_TOKENS", raising=False)

    # Settings values are read once when app.config is imported (module-level
    # `os.getenv(...)` class attributes), and app.config calls load_dotenv() on
    # import -- which would just reload a real GROQ_API_KEY from .env and
    # undo the delenv above. Stub load_dotenv out for this reimport so the
    # patched (deleted) environment actually sticks.
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)
    sys.modules.pop("app.config", None)
    config = importlib.import_module("app.config")
    try:
        config.get_settings.cache_clear()
        settings = config.get_settings()

        assert settings.GROQ_API_KEY == ""
        assert settings.GROQ_MODEL == "llama-3.3-70b-versatile"
        assert settings.CHAT_MAX_TOKENS == 512
    finally:
        config.get_settings.cache_clear()
        sys.modules.pop("app.config", None)
        importlib.import_module("app.config")
