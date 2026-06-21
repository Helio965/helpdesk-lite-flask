"""Testes dos comandos de CLI (seed, create-agent) e da função seed_data."""

from helpdesk.cli import seed_data
from helpdesk.extensions import db
from helpdesk.models import Ticket, TicketUpdate, User


def _count(model):
    return db.session.scalar(db.select(db.func.count()).select_from(model))


def test_seed_data_populates(app):
    seed_data()
    assert _count(User) == 3
    assert _count(Ticket) == 3
    assert _count(TicketUpdate) == 2


def test_seed_data_is_idempotent(app):
    seed_data()
    seed_data()
    assert _count(User) == 3
    assert _count(Ticket) == 3


def test_seed_passwords_are_hashed(app):
    seed_data()
    user = db.session.execute(
        db.select(User).filter_by(email="agente@helpdesk.local")
    ).scalar_one()
    assert user.password_hash != "Senha@123"
    assert user.check_password("Senha@123")
    assert user.role == "agent"


def test_seed_cli_command(app):
    result = app.test_cli_runner().invoke(args=["seed"])
    assert result.exit_code == 0
    assert "Seed" in result.output
    assert _count(User) == 3


def test_create_agent_cli_command(app):
    result = app.test_cli_runner().invoke(
        args=[
            "create-agent",
            "Novo Agente",
            "novoagente@example.com",
            "--password",
            "Senha@123",
        ]
    )
    assert result.exit_code == 0
    user = db.session.execute(
        db.select(User).filter_by(email="novoagente@example.com")
    ).scalar_one_or_none()
    assert user is not None
    assert user.role == "agent"
    assert user.check_password("Senha@123")


def test_create_agent_cli_rejects_duplicate(app, agent_user):
    result = app.test_cli_runner().invoke(
        args=[
            "create-agent",
            "Outro",
            agent_user.email,
            "--password",
            "Senha@123",
        ]
    )
    assert result.exit_code != 0
