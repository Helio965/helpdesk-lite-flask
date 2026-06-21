"""Testes da configuração Twelve-Factor (_require, _as_bool, Config)."""

import pytest

from helpdesk.config import Config, _as_bool, _require


def test_require_missing_raises(monkeypatch):
    monkeypatch.delenv("HD_TEST_VAR", raising=False)
    with pytest.raises(RuntimeError):
        _require("HD_TEST_VAR")


def test_require_too_short_raises(monkeypatch):
    monkeypatch.setenv("HD_TEST_VAR", "abc")
    with pytest.raises(RuntimeError):
        _require("HD_TEST_VAR", min_len=10)


def test_require_ok(monkeypatch):
    monkeypatch.setenv("HD_TEST_VAR", "abcdefghij")
    assert _require("HD_TEST_VAR", min_len=5) == "abcdefghij"


def test_as_bool_variants():
    assert _as_bool("1") is True
    assert _as_bool("true") is True
    assert _as_bool("YES") is True
    assert _as_bool("0") is False
    assert _as_bool("False") is False
    assert _as_bool(None, default=True) is True
    assert _as_bool(None) is False


def test_config_requires_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///x.db")
    with pytest.raises(RuntimeError):
        Config()


def test_config_rejects_short_secret_key(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "short")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///x.db")
    with pytest.raises(RuntimeError):
        Config()


def test_config_ok(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///x.db")
    monkeypatch.setenv("TICKETS_PER_PAGE", "25")
    cfg = Config()
    assert cfg.SQLALCHEMY_DATABASE_URI == "sqlite:///x.db"
    assert cfg.TICKETS_PER_PAGE == 25
    assert cfg.SQLALCHEMY_TRACK_MODIFICATIONS is False
