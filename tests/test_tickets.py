"""Testes de tickets, autorização e atualizações."""

from helpdesk.extensions import db
from helpdesk.models import Ticket, TicketUpdate


def _make_ticket(customer, title="Ticket de teste", status="open", priority="medium"):
    ticket = Ticket(
        customer_id=customer.id, title=title, status=status, priority=priority
    )
    db.session.add(ticket)
    db.session.commit()
    return ticket


def _get_ticket(ticket_id):
    db.session.expire_all()
    return db.session.get(Ticket, ticket_id)


def _count_updates(ticket_id):
    db.session.expire_all()
    return db.session.scalar(
        db.select(db.func.count())
        .select_from(TicketUpdate)
        .filter_by(ticket_id=ticket_id)
    )


# --- criação ---------------------------------------------------------------
def test_customer_creates_ticket_for_self(logged_customer, customer_user):
    resp = logged_customer.post(
        "/tickets/create",
        data={"title": "Meu problema", "description": "detalhes", "priority": "high"},
    )
    assert resp.status_code == 302
    ticket = db.session.execute(
        db.select(Ticket).filter_by(title="Meu problema")
    ).scalar_one()
    assert ticket.customer_id == customer_user.id


def test_new_ticket_starts_open(logged_customer):
    logged_customer.post(
        "/tickets/create",
        data={"title": "Nasce aberto", "priority": "low"},
    )
    ticket = db.session.execute(
        db.select(Ticket).filter_by(title="Nasce aberto")
    ).scalar_one()
    assert ticket.status == "open"


def test_customer_cannot_set_other_customer_id(
    logged_customer, customer_user, other_customer_user
):
    """customer_id injetado é ignorado: ticket pertence ao usuário logado."""
    resp = logged_customer.post(
        "/tickets/create",
        data={
            "title": "Tentando injetar dono",
            "priority": "medium",
            "customer_id": str(other_customer_user.id),
            "status": "closed",
            "agent_id": "1",
        },
    )
    assert resp.status_code == 302
    ticket = db.session.execute(
        db.select(Ticket).filter_by(title="Tentando injetar dono")
    ).scalar_one()
    assert ticket.customer_id == customer_user.id
    assert ticket.customer_id != other_customer_user.id
    assert ticket.status == "open"  # status forçado pelo servidor
    assert ticket.agent_id is None  # agent_id ignorado na criação


# --- listagem / visibilidade ----------------------------------------------
def test_customer_lists_only_own_tickets(
    logged_customer, customer_user, other_customer_user
):
    _make_ticket(customer_user, title="Ticket do cliente logado")
    _make_ticket(other_customer_user, title="Ticket de outro cliente")
    resp = logged_customer.get("/tickets/")
    assert resp.status_code == 200
    assert "Ticket do cliente logado".encode() in resp.data
    assert "Ticket de outro cliente".encode() not in resp.data


def test_agent_lists_all_tickets(logged_agent, customer_user, other_customer_user):
    _make_ticket(customer_user, title="Ticket A")
    _make_ticket(other_customer_user, title="Ticket B")
    resp = logged_agent.get("/tickets/")
    assert resp.status_code == 200
    assert b"Ticket A" in resp.data
    assert b"Ticket B" in resp.data


def test_customer_cannot_view_other_ticket(logged_customer, other_customer_user):
    ticket = _make_ticket(other_customer_user, title="Privado")
    resp = logged_customer.get(f"/tickets/{ticket.id}")
    assert resp.status_code == 403


def test_agent_can_view_any_ticket(logged_agent, customer_user):
    ticket = _make_ticket(customer_user, title="Visível ao agente")
    resp = logged_agent.get(f"/tickets/{ticket.id}")
    assert resp.status_code == 200
    assert "Visível ao agente".encode() in resp.data


# --- edição administrativa (agente) ----------------------------------------
def test_agent_changes_status(logged_agent, customer_user):
    ticket = _make_ticket(customer_user)
    resp = logged_agent.post(
        f"/tickets/{ticket.id}/edit",
        data={"status": "in_progress", "priority": "medium", "agent_id": ""},
    )
    assert resp.status_code == 302
    assert _get_ticket(ticket.id).status == "in_progress"


def test_agent_can_assign_to_agent(logged_agent, customer_user, agent_user):
    ticket = _make_ticket(customer_user)
    resp = logged_agent.post(
        f"/tickets/{ticket.id}/edit",
        data={"status": "open", "priority": "medium", "agent_id": str(agent_user.id)},
    )
    assert resp.status_code == 302
    assert _get_ticket(ticket.id).agent_id == agent_user.id


def test_customer_cannot_edit_ticket(logged_customer, customer_user):
    """Cliente não acessa a edição administrativa (status/prioridade/agente)."""
    ticket = _make_ticket(customer_user)
    resp = logged_customer.post(
        f"/tickets/{ticket.id}/edit",
        data={"status": "closed", "agent_id": "1"},
    )
    assert resp.status_code == 403
    assert _get_ticket(ticket.id).status == "open"  # nada mudou


def test_agent_id_pointing_to_customer_is_rejected(logged_agent, customer_user):
    """agent_id deve apontar para um agente; um customer é rejeitado."""
    ticket = _make_ticket(customer_user)
    resp = logged_agent.post(
        f"/tickets/{ticket.id}/edit",
        data={
            "status": "open",
            "priority": "medium",
            "agent_id": str(customer_user.id),  # é customer, não agent
        },
    )
    assert resp.status_code == 400
    assert _get_ticket(ticket.id).agent_id is None


def test_agent_id_nonexistent_is_rejected(logged_agent, customer_user):
    ticket = _make_ticket(customer_user)
    resp = logged_agent.post(
        f"/tickets/{ticket.id}/edit",
        data={"status": "open", "priority": "medium", "agent_id": "999999"},
    )
    assert resp.status_code == 400
    assert _get_ticket(ticket.id).agent_id is None


# --- atualizações (mensagens) ----------------------------------------------
def test_add_update_message_works(logged_customer, customer_user):
    ticket = _make_ticket(customer_user)
    resp = logged_customer.post(
        f"/tickets/{ticket.id}/update",
        data={"message": "Alguma novidade?"},
    )
    assert resp.status_code == 302
    assert _count_updates(ticket.id) == 1


def test_empty_message_is_rejected(logged_customer, customer_user):
    ticket = _make_ticket(customer_user)
    resp = logged_customer.post(
        f"/tickets/{ticket.id}/update",
        data={"message": ""},
    )
    assert resp.status_code == 400
    assert _count_updates(ticket.id) == 0


def test_customer_cannot_update_other_ticket(logged_customer, other_customer_user):
    ticket = _make_ticket(other_customer_user)
    resp = logged_customer.post(
        f"/tickets/{ticket.id}/update",
        data={"message": "Não deveria conseguir"},
    )
    assert resp.status_code == 403
    assert _count_updates(ticket.id) == 0
