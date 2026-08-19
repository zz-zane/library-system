from backend.app.core.config import Settings


def test_settings_use_explicit_environment_values():
    settings = Settings(
        app_name="Custom Library",
        environment="testing",
        database_url="sqlite:///./custom.db",
    )

    assert settings.app_name == "Custom Library"
    assert settings.environment == "testing"
    assert settings.database_url == "sqlite:///./custom.db"
