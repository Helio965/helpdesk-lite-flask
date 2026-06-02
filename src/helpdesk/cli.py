"""Comandos de linha de comando (Flask CLI).

Disponibiliza ``flask seed`` para popular dados iniciais de desenvolvimento e
``flask create-agent`` para criar um agente de forma controlada (a role é
validada pelo servidor, não via payload de formulário).
"""

import click
from flask import Flask
from flask.cli import with_appcontext

from .extensions import db
from .models import (
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    ROLE_AGENT,
    ROLE_CUSTOMER,
    ROLES,
    STATUS_IN_PROGRESS,
    STATUS_OPEN,
    Ticket,
    TicketUpdate,
    User,
)

# Senha usada apenas em ambiente de desenvolvimento. Armazenada como HASH.
DEV_PASSWORD = "Senha@123"


def _get_or_create_user(name: str, email: str, role: str) -> User:
    user = db.session.execute(
        db.select(User).filter_by(email=email)
    ).scalar_one_or_none()
    if user is None:
        user = User(name=name, email=email, role=role)
        user.set_password(DEV_PASSWORD)
        db.session.add(user)
    return user


def seed_data() -> None:
    """Popula o banco com dados mínimos de desenvolvimento (idempotente)."""
    agent = _get_or_create_user("Ana Agente", "agente@helpdesk.local", ROLE_AGENT)
    customer1 = _get_or_create_user(
        "Bruno Cliente", "cliente1@helpdesk.local", ROLE_CUSTOMER
    )
    customer2 = _get_or_create_user(
        "Carla Cliente", "cliente2@helpdesk.local", ROLE_CUSTOMER
    )
    db.session.commit()

    # Cria tickets apenas se ainda não houver nenhum (evita duplicar no reseed).
    if db.session.scalar(db.select(db.func.count()).select_from(Ticket)) == 0:
        t1 = Ticket(
            customer_id=customer1.id,
            title="Não consigo acessar minha conta",
            description="Recebo erro de senha inválida ao tentar logar.",
            priority=PRIORITY_HIGH,
            status=STATUS_OPEN,
        )
        t2 = Ticket(
            customer_id=customer1.id,
            agent_id=agent.id,
            title="Dúvida sobre cobrança",
            description="Vi um valor que não reconheço na fatura.",
            priority=PRIORITY_MEDIUM,
            status=STATUS_IN_PROGRESS,
        )
        t3 = Ticket(
            customer_id=customer2.id,
            title="Solicitação de nova funcionalidade",
            description="Seria ótimo ter exportação de relatórios.",
            priority=PRIORITY_LOW,
            status=STATUS_OPEN,
        )
        db.session.add_all([t1, t2, t3])
        db.session.commit()

        db.session.add_all(
            [
                TicketUpdate(
                    ticket_id=t2.id,
                    author_id=agent.id,
                    message="Olá! Estou analisando sua fatura, retorno em breve.",
                ),
                TicketUpdate(
                    ticket_id=t2.id,
                    author_id=customer1.id,
                    message="Obrigado, fico no aguardo.",
                ),
            ]
        )
        db.session.commit()

    click.echo("Seed concluído. Usuários de exemplo (senha: %s):" % DEV_PASSWORD)
    click.echo("  - agente@helpdesk.local   (agent)")
    click.echo("  - cliente1@helpdesk.local (customer)")
    click.echo("  - cliente2@helpdesk.local (customer)")


def register_cli(app: Flask) -> None:
    @app.cli.command("seed")
    @with_appcontext
    def seed_command():
        """Popula o banco com dados iniciais de desenvolvimento."""
        seed_data()

    @app.cli.command("create-agent")
    @click.argument("name")
    @click.argument("email")
    @click.password_option()
    @with_appcontext
    def create_agent_command(name, email, password):
        """Cria um usuário com perfil de agente."""
        if db.session.execute(
            db.select(User).filter_by(email=email)
        ).scalar_one_or_none():
            raise click.ClickException(f"E-mail já cadastrado: {email}")
        user = User(name=name, email=email, role=ROLE_AGENT)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Agente criado: {email}")

    # Disponibiliza os valores de role no shell interativo (`flask shell`).
    @app.shell_context_processor
    def _shell_context():
        return {
            "db": db,
            "User": User,
            "Ticket": Ticket,
            "TicketUpdate": TicketUpdate,
            "ROLES": ROLES,
        }
