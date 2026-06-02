"""Testes de fumaça: a aplicação sobe e a home responde."""

from helpdesk import create_app
from helpdesk.config import TestConfig


def test_app_factory_creates_app():
    app = create_app(TestConfig)
    assert app is not None
    assert app.config["TESTING"] is True


def test_app_factory_accepts_dict_config():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "x" * 32,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )
    assert app.config["TESTING"] is True


def test_home_anonymous_returns_200(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"HelpDesk Lite" in resp.data


def test_home_authenticated_returns_200(logged_customer):
    resp = logged_customer.get("/")
    assert resp.status_code == 200
    assert "Resumo dos tickets".encode() in resp.data
