"""Testes de gestão de usuários e proteção contra mass assignment."""

from helpdesk.extensions import db
from helpdesk.models import User


def _get_user(email):
    db.session.expire_all()
    return db.session.execute(
        db.select(User).filter_by(email=email)
    ).scalar_one_or_none()


def test_agent_can_list_users(logged_agent):
    resp = logged_agent.get("/users/")
    assert resp.status_code == 200
    assert b"Usu" in resp.data  # "Usuários"


def test_customer_cannot_list_users(logged_customer):
    resp = logged_customer.get("/users/")
    assert resp.status_code == 403


def test_anonymous_cannot_list_users(client):
    resp = client.get("/users/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_create_user_with_valid_data(logged_agent):
    resp = logged_agent.post(
        "/users/create",
        data={
            "name": "Novo Cliente",
            "email": "novo@example.com",
            "password": "Senha@123",
        },
    )
    assert resp.status_code == 302
    user = _get_user("novo@example.com")
    assert user is not None
    assert user.role == "customer"
    # Senha nunca é armazenada em texto puro.
    assert user.password_hash != "Senha@123"
    assert user.check_password("Senha@123")


def test_create_user_rejects_invalid_email(logged_agent):
    resp = logged_agent.post(
        "/users/create",
        data={"name": "Fulano", "email": "nao-eh-email", "password": "Senha@123"},
    )
    assert resp.status_code == 400
    assert _get_user("nao-eh-email") is None


def test_create_user_rejects_short_name(logged_agent):
    resp = logged_agent.post(
        "/users/create",
        data={"name": "A", "email": "curto@example.com", "password": "Senha@123"},
    )
    assert resp.status_code == 400
    assert _get_user("curto@example.com") is None


def test_create_user_requires_password(logged_agent):
    resp = logged_agent.post(
        "/users/create",
        data={"name": "Sem Senha", "email": "semsenha@example.com"},
    )
    assert resp.status_code == 400
    assert _get_user("semsenha@example.com") is None


def test_mass_assignment_role_is_ignored(logged_agent):
    """Enviar role=agent não transforma o novo usuário em agente."""
    resp = logged_agent.post(
        "/users/create",
        data={
            "name": "Tentativa Escalada",
            "email": "escalada@example.com",
            "password": "Senha@123",
            "role": "agent",
        },
    )
    assert resp.status_code == 302
    user = _get_user("escalada@example.com")
    assert user is not None
    assert user.role == "customer"  # role controlada pelo servidor


def test_mass_assignment_internal_fields_ignored(logged_agent):
    """id, created_at e password_hash enviados pelo cliente são ignorados."""
    resp = logged_agent.post(
        "/users/create",
        data={
            "name": "Cliente Hack",
            "email": "hack@example.com",
            "password": "Senha@123",
            "id": "999999",
            "created_at": "1999-01-01T00:00:00",
            "password_hash": "fake-hash",
            "is_admin": "true",
        },
    )
    assert resp.status_code == 302
    user = _get_user("hack@example.com")
    assert user is not None
    assert user.id != 999999  # id é gerado pelo banco
    assert user.password_hash != "fake-hash"  # hash real, não o injetado
    assert user.check_password("Senha@123")
    assert not hasattr(user, "is_admin")
