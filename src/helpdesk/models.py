"""Modelos ORM do HelpDesk Lite (Flask-SQLAlchemy).

Tabelas: ``users``, ``tickets`` e ``ticket_updates``.

A persistência da aplicação é feita exclusivamente via ORM + migrations.
Nenhum SQL manual é usado como camada principal.
"""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

# ---------------------------------------------------------------------------
# Valores controlados (enums lógicos). Centralizados para uso em models,
# schemas, rotas e templates, evitando "magic strings" espalhadas.
# ---------------------------------------------------------------------------
ROLE_CUSTOMER = "customer"
ROLE_AGENT = "agent"
ROLES = (ROLE_CUSTOMER, ROLE_AGENT)

STATUS_OPEN = "open"
STATUS_IN_PROGRESS = "in_progress"
STATUS_RESOLVED = "resolved"
STATUS_CLOSED = "closed"
TICKET_STATUSES = (STATUS_OPEN, STATUS_IN_PROGRESS, STATUS_RESOLVED, STATUS_CLOSED)

PRIORITY_LOW = "low"
PRIORITY_MEDIUM = "medium"
PRIORITY_HIGH = "high"
TICKET_PRIORITIES = (PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH)


def _utcnow() -> datetime:
    """Horário atual em UTC (timezone-aware)."""
    return datetime.now(timezone.utc)


def _sql_in(column, allowed) -> str:
    """Monta a expressão SQL ``coluna IN ('a', 'b', ...)`` para CheckConstraint."""
    values = ", ".join(f"'{value}'" for value in allowed)
    return f"{column} IN ({values})"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_CUSTOMER)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    __table_args__ = (CheckConstraint(_sql_in("role", ROLES), name="ck_users_role"),)

    # Tickets em que o usuário é o cliente (autor do chamado).
    tickets_as_customer = db.relationship(
        "Ticket",
        back_populates="customer",
        foreign_keys="Ticket.customer_id",
    )
    # Tickets atribuídos a este usuário como agente responsável.
    tickets_as_agent = db.relationship(
        "Ticket",
        back_populates="agent",
        foreign_keys="Ticket.agent_id",
    )
    # Atualizações (mensagens) escritas por este usuário.
    updates = db.relationship("TicketUpdate", back_populates="author")

    # --- senha (sempre armazenada como hash) ------------------------------
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    # --- helpers ----------------------------------------------------------
    @property
    def is_agent(self) -> bool:
        return self.role == ROLE_AGENT

    @property
    def is_customer(self) -> bool:
        return self.role == ROLE_CUSTOMER

    def to_dict(self) -> dict:
        """Serialização segura: nunca expõe ``password_hash``."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - apenas depuração
        return f"<User {self.id} {self.email} ({self.role})>"


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_OPEN)
    priority = db.Column(db.String(20), nullable=False, default=PRIORITY_MEDIUM)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        CheckConstraint(_sql_in("status", TICKET_STATUSES), name="ck_tickets_status"),
        CheckConstraint(
            _sql_in("priority", TICKET_PRIORITIES), name="ck_tickets_priority"
        ),
    )

    customer = db.relationship(
        "User", foreign_keys=[customer_id], back_populates="tickets_as_customer"
    )
    agent = db.relationship(
        "User", foreign_keys=[agent_id], back_populates="tickets_as_agent"
    )
    updates = db.relationship(
        "TicketUpdate",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketUpdate.created_at",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "agent_id": self.agent_id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - apenas depuração
        return f"<Ticket {self.id} {self.title!r} status={self.status}>"


class TicketUpdate(db.Model):
    __tablename__ = "ticket_updates"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    ticket = db.relationship("Ticket", back_populates="updates")
    author = db.relationship("User", back_populates="updates")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "author_id": self.author_id,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - apenas depuração
        return f"<TicketUpdate {self.id} ticket={self.ticket_id}>"
