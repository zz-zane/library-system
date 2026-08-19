"""配置安全回归测试（依据 ``docs/system-design.md`` §12.1、§14.1 与后端安全策略）。

验证 SECRET_KEY 的安全策略：

- 显式安全 SECRET_KEY 时 ``Settings`` 可用（任何环境）；
- 缺失、空值或公开占位密钥时 ``Settings`` 启动失败
  （§12.1：无安全默认值；§14.1：不得采用默认/占位值——所有环境统一强制）；
- 测试启动前已注入仅用于测试的固定非默认密钥（见 ``conftest.py``）。
"""

import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings

DEFAULT_PLACEHOLDER = "development-only-secret-key-change-me"
SECURE_KEY = "a-strong-random-secret-2026"


def test_secure_secret_key_works_in_production():
    """显式安全 SECRET_KEY + production → Settings 可用（§12.1）。"""
    settings = Settings(environment="production", secret_key=SECURE_KEY)

    assert settings.environment == "production"
    assert settings.secret_key == SECURE_KEY


def test_secure_secret_key_works_in_non_production():
    """显式安全 SECRET_KEY + development/testing → Settings 可用。"""
    for environment in ("development", "testing"):
        settings = Settings(environment=environment, secret_key=SECURE_KEY)
        assert settings.environment == environment
        assert settings.secret_key == SECURE_KEY


def test_missing_secret_key_fails(monkeypatch):
    """缺失 SECRET_KEY（无默认值）→ 启动失败（§12.1 无安全默认值）。"""
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(environment="production")


def test_empty_secret_key_fails(monkeypatch):
    """空 SECRET_KEY → 启动失败（所有环境统一强制，§14.1）。"""
    monkeypatch.setenv("SECRET_KEY", "")

    with pytest.raises(ValidationError):
        Settings(environment="production")


def test_placeholder_secret_key_fails_in_production():
    """production 使用公开占位密钥 → 启动失败（§14.1 生产不得采用默认值）。"""
    with pytest.raises(ValidationError):
        Settings(environment="production", secret_key=DEFAULT_PLACEHOLDER)


def test_placeholder_secret_key_fails_in_development():
    """development 环境同样拒绝公开占位 SECRET_KEY（所有环境强制显式安全密钥）。"""
    with pytest.raises(ValidationError):
        Settings(environment="development", secret_key=DEFAULT_PLACEHOLDER)


def test_placeholder_secret_key_fails_in_testing():
    """testing 环境同样拒绝公开占位 SECRET_KEY。"""
    with pytest.raises(ValidationError):
        Settings(environment="testing", secret_key=DEFAULT_PLACEHOLDER)


def test_test_environment_uses_non_default_secret():
    """测试启动前注入的 SECRET_KEY 必须是固定非默认密钥（conftest 守卫）。"""
    settings = Settings(environment="testing")

    assert settings.secret_key
    assert settings.secret_key != DEFAULT_PLACEHOLDER
