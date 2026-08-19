"""配置安全回归测试（依据 ``docs/system-design.md`` §12.1、§14.1）。

验证 SECRET_KEY 的安全策略：

- 显式安全 SECRET_KEY 时 ``Settings`` 可用；
- production 下缺失、空值或公开占位密钥时 ``Settings`` 启动失败
  （§12.1：production 缺少安全 SECRET_KEY 应启动失败，而非生成临时密钥）；
- 测试启动前已注入仅用于测试的固定非默认密钥（见 ``conftest.py``）。
"""

import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings

DEFAULT_PLACEHOLDER = "development-only-secret-key-change-me"


def test_secure_secret_key_works_in_production():
    """显式安全 SECRET_KEY + production → Settings 可用（§12.1）。"""
    settings = Settings(environment="production", secret_key="a-strong-random-secret-2026")

    assert settings.environment == "production"
    assert settings.secret_key == "a-strong-random-secret-2026"


def test_missing_secret_key_fails_in_production(monkeypatch):
    """production 缺失 SECRET_KEY → 启动失败（无安全默认值，§12.1）。"""
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(environment="production")


def test_empty_secret_key_fails_in_production(monkeypatch):
    """production 空 SECRET_KEY → 启动失败（§12.1 不得生成临时密钥）。"""
    monkeypatch.setenv("SECRET_KEY", "")

    with pytest.raises(ValidationError):
        Settings(environment="production")


def test_placeholder_secret_key_fails_in_production():
    """production 使用公开占位密钥 → 启动失败（§14.1 生产环境不得采用默认值）。"""
    with pytest.raises(ValidationError):
        Settings(environment="production", secret_key=DEFAULT_PLACEHOLDER)


def test_placeholder_secret_key_allowed_in_non_production():
    """非 production 环境不强制安全密钥，默认开发体验不被破坏。"""
    settings = Settings(environment="development", secret_key=DEFAULT_PLACEHOLDER)

    assert settings.environment == "development"


def test_test_environment_uses_non_default_secret():
    """测试启动前注入的 SECRET_KEY 必须是固定非默认密钥（conftest 守卫）。"""
    settings = Settings(environment="testing")

    assert settings.secret_key
    assert settings.secret_key != DEFAULT_PLACEHOLDER
