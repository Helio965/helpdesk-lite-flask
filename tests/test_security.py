"""Testes das proteções de segurança: CSRF, rate limit e headers."""

import pytest

from helpdesk import create_app
from helpdesk.extensions import db
from helpdesk.models import ROLE_CUSTOMER, User

BASE_TEST_CONFIG = {
    "TESTING": True,
    "SECRET_KEY": "security-tests-secret-key-min-32-characters",
    "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
}


def _make_app(**overrides):
    config = {**BASE_TEST_CONFIG, **overrides}
    app = create_app(config)
    with app.app_context():
        db.create_all()
    return app


def test_security_headers_present(client):
    resp = client.get("/")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in resp.headers


def test_csrf_blocks_post_without_token():
    """Com CSRF ativo, POST sem token é rejeitado (400)."""
    app = _make_app(WTF_CSRF_ENABLED=True, RATELIMIT_ENABLED=False)
    client = app.test_client()
    resp = client.post(
        "/auth/login", data={"email": "a@b.com", "password": "x"}
    )
    assert resp.status_code == 400


def test_login_rate_limit_returns_429():
    """Excesso de tentativas de login retorna 429."""
    app = _make_app(
        WTF_CSRF_ENABLED=False,
        RATELIMIT_ENABLED=True,
        LOGIN_RATE_LIMIT="3 per minute",
    )
    client = app.test_client()
    last = None
    for _ in range(5):
        last = client.post(
            "/auth/login",
            data={"email": "naoexiste@example.com", "password": "errada"},
        )
    assert last.status_code == 429


def test_get_login_not_rate_limited():
    """O GET da página de login não é limitado (só o POST)."""
    app = _make_app(
        WTF_CSRF_ENABLED=False,
        RATELIMIT_ENABLED=True,
        LOGIN_RATE_LIMIT="2 per minute",
    )
    client = app.test_client()
    for _ in range(5):
        resp = client.get("/auth/login")
    assert resp.status_code == 200
