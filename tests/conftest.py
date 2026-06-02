"""Fixtures compartilhadas da suíte de testes.

Usa SQLite em memória, cria as tabelas antes de cada teste e descarta
tudo no teardown, garantindo isolamento entre testes.
"""

import pytest

from helpdesk import create_app
from helpdesk.config import TestConfig
from helpdesk.extensions import db as _db
from helpdesk.models import ROLE_AGENT, ROLE_CUSTOMER, User

# Senha de teste conhecida (armazenada como hash pelo modelo).
TEST_PASSWORD = "Senha@123"


@pytest.fixture
def app():
    """Aplicação configurada para testes, com contexto de app ativo."""
    app = create_app(TestConfig)
    ctx = app.app_context()
    ctx.push()
    _db.create_all()
    try:
        yield app
    finally:
        _db.session.remove()
        _db.drop_all()
        ctx.pop()


@pytest.fixture
def client(app):
    return app.test_client()


def _make_user(name: str, email: str, role: str) -> User:
    user = User(name=name, email=email, role=role)
    user.set_password(TEST_PASSWORD)
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture
def customer_user(app):
    return _make_user("Cliente Um", "cliente1@example.com", ROLE_CUSTOMER)


@pytest.fixture
def other_customer_user(app):
    return _make_user("Cliente Dois", "cliente2@example.com", ROLE_CUSTOMER)


@pytest.fixture
def agent_user(app):
    return _make_user("Agente Um", "agente1@example.com", ROLE_AGENT)


def _login(client, user):
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
    return client


@pytest.fixture
def logged_customer(client, customer_user):
    return _login(client, customer_user)


@pytest.fixture
def logged_agent(client, agent_user):
    return _login(client, agent_user)
