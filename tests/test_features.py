"""Testes das funcionalidades adicionadas na continuidade do projeto:
filtros de tickets, atribuição, fechar/reabrir, troca de senha e perfil.
"""

from helpdesk.extensions import db
from helpdesk.models import Ticket


def _make_ticket(customer, title="T", status="open", priority="medium", agent_id=None):
    ticket = Ticket(
        customer_id=customer.id,
        title=title,
        status=status,
        priority=priority,
        agent_id=agent_id,
    )
    db.session.add(ticket)
    db.session.commit()
    return ticket


def _get(ticket_id):
    db.session.expire_all()
    return db.session.get(Ticket, ticket_id)


# --- filtros / busca -------------------------------------------------------
def test_filter_by_status(logged_agent, customer_user):
    _make_ticket(customer_user, title="Aberto", status="open")
    _make_ticket(customer_user, title="Fechado", status="closed")
    resp = logged_agent.get("/tickets/?status=open")
    assert resp.status_code == 200
    assert b"Aberto" in resp.data
    assert b"Fechado" not in resp.data


def test_filter_by_priority(logged_agent, customer_user):
    _make_ticket(customer_user, title="Urgente", priority="high")
    _make_ticket(customer_user, title="Tranquilo", priority="low")
    resp = logged_agent.get("/tickets/?priority=high")
    assert b"Urgente" in resp.data
    assert b"Tranquilo" not in resp.data


def test_search_by_title(logged_agent, customer_user):
    _make_ticket(customer_user, title="Problema no login")
    _make_ticket(customer_user, title="Erro de cobranca")
    resp = logged_agent.get("/tickets/?q=login")
    assert "Problema no login".encode() in resp.data
    assert "Erro de cobranca".encode() not in resp.data


def test_agent_filter_assignment_mine(logged_agent, agent_user, customer_user):
    _make_ticket(customer_user, title="Minha", agent_id=agent_user.id)
    _make_ticket(customer_user, title="De ninguem")
    resp = logged_agent.get("/tickets/?assignment=mine")
    assert b"Minha" in resp.data
    assert b"De ninguem" not in resp.data


# --- atribuir a mim --------------------------------------------------------
def test_agent_assign_to_me(logged_agent, agent_user, customer_user):
    ticket = _make_ticket(customer_user, status="open")
    resp = logged_agent.post(f"/tickets/{ticket.id}/assign")
    assert resp.status_code == 302
    updated = _get(ticket.id)
    assert updated.agent_id == agent_user.id
    assert updated.status == "in_progress"  # open -> in_progress ao assumir


def test_customer_cannot_assign(logged_customer, customer_user):
    ticket = _make_ticket(customer_user)
    resp = logged_customer.post(f"/tickets/{ticket.id}/assign")
    assert resp.status_code == 403


# --- fechar / reabrir ------------------------------------------------------
def test_customer_can_close_own_ticket(logged_customer, customer_user):
    ticket = _make_ticket(customer_user, status="open")
    resp = logged_customer.post(f"/tickets/{ticket.id}/close")
    assert resp.status_code == 302
    assert _get(ticket.id).status == "closed"


def test_customer_can_reopen_own_ticket(logged_customer, customer_user):
    ticket = _make_ticket(customer_user, status="closed")
    resp = logged_customer.post(f"/tickets/{ticket.id}/reopen")
    assert resp.status_code == 302
    assert _get(ticket.id).status == "open"


def test_customer_cannot_close_other_ticket(logged_customer, other_customer_user):
    ticket = _make_ticket(other_customer_user, status="open")
    resp = logged_customer.post(f"/tickets/{ticket.id}/close")
    assert resp.status_code == 403
    assert _get(ticket.id).status == "open"


# --- troca de senha --------------------------------------------------------
def test_change_password_success(logged_customer, customer_user):
    resp = logged_customer.post(
        "/auth/password",
        data={
            "current_password": "Senha@123",
            "new_password": "NovaSenha@456",
            "confirm_password": "NovaSenha@456",
        },
    )
    assert resp.status_code == 302
    db.session.expire_all()
    user = db.session.get(type(customer_user), customer_user.id)
    assert user.check_password("NovaSenha@456")
    assert not user.check_password("Senha@123")


def test_change_password_wrong_current(logged_customer):
    resp = logged_customer.post(
        "/auth/password",
        data={
            "current_password": "errada",
            "new_password": "NovaSenha@456",
            "confirm_password": "NovaSenha@456",
        },
    )
    assert resp.status_code == 400


def test_change_password_mismatch(logged_customer):
    resp = logged_customer.post(
        "/auth/password",
        data={
            "current_password": "Senha@123",
            "new_password": "NovaSenha@456",
            "confirm_password": "Outra@789",
        },
    )
    assert resp.status_code == 400


def test_change_password_requires_login(client):
    resp = client.get("/auth/password")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


# --- perfil ----------------------------------------------------------------
def test_account_page(logged_customer, customer_user):
    resp = logged_customer.get("/account")
    assert resp.status_code == 200
    assert customer_user.email.encode() in resp.data


def test_account_requires_login(client):
    resp = client.get("/account")
    assert resp.status_code == 302
