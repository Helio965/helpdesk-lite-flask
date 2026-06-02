"""Tickets e atualizações de tickets.

Regras de autorização:

* Cliente (``customer``) vê/edita apenas os próprios tickets e sempre cria
  chamados para si mesmo (``customer_id`` vem do usuário autenticado).
* Agente (``agent``) vê todos os tickets, adiciona mensagens em qualquer um e
  é o único que pode alterar ``status``, ``priority`` e ``agent_id``.
* ``agent_id`` só pode apontar para um usuário existente com role ``agent``.
"""

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from marshmallow import ValidationError

from ...decorators import agent_required, login_required
from ...extensions import db
from ...models import (
    ROLE_AGENT,
    STATUS_OPEN,
    TICKET_PRIORITIES,
    TICKET_STATUSES,
    Ticket,
    TicketUpdate,
    User,
)
from ...schemas import (
    TicketCreateSchema,
    TicketUpdateMessageSchema,
    TicketUpdateSchema,
)

bp = Blueprint("tickets", __name__, url_prefix="/tickets")

_create_schema = TicketCreateSchema()
_edit_schema = TicketUpdateSchema()
_message_schema = TicketUpdateMessageSchema()


def _get_ticket_or_404(ticket_id: int) -> Ticket:
    ticket = db.session.get(Ticket, ticket_id)
    if ticket is None:
        abort(404)
    return ticket


def _ensure_can_view(ticket: Ticket) -> None:
    """Cliente só acessa o próprio ticket; agente acessa qualquer um."""
    if g.user.is_agent:
        return
    if ticket.customer_id != g.user.id:
        abort(403)


def _agents():
    return db.session.execute(
        db.select(User).filter_by(role=ROLE_AGENT).order_by(User.name)
    ).scalars().all()


@bp.route("/")
@login_required
def list_tickets():
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config.get("TICKETS_PER_PAGE", 10)

    query = db.select(Ticket).order_by(Ticket.created_at.desc())
    if g.user.is_customer:
        # Cliente enxerga somente os próprios tickets.
        query = query.filter_by(customer_id=g.user.id)

    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    return render_template(
        "tickets/list.html", tickets=pagination.items, pagination=pagination
    )


@bp.route("/create", methods=["GET", "POST"])
@login_required
def create_ticket():
    if request.method == "POST":
        try:
            data = _create_schema.load(request.form.to_dict())
        except ValidationError as err:
            return (
                render_template(
                    "tickets/form.html",
                    errors=err.messages,
                    form=request.form,
                    priorities=TICKET_PRIORITIES,
                ),
                400,
            )

        # Atribuição explícita. customer_id NUNCA vem do cliente: é sempre o
        # usuário autenticado. status é definido pelo servidor como "open".
        ticket = Ticket(
            customer_id=g.user.id,
            title=data["title"],
            description=data["description"] or None,
            priority=data["priority"],
            status=STATUS_OPEN,
        )
        db.session.add(ticket)
        db.session.commit()

        flash("Ticket criado com sucesso.", "success")
        return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))

    return render_template(
        "tickets/form.html", errors={}, form={}, priorities=TICKET_PRIORITIES
    )


@bp.route("/<int:ticket_id>")
@login_required
def ticket_detail(ticket_id):
    ticket = _get_ticket_or_404(ticket_id)
    _ensure_can_view(ticket)
    return render_template(
        "tickets/detail.html",
        ticket=ticket,
        agents=_agents() if g.user.is_agent else [],
        statuses=TICKET_STATUSES,
        priorities=TICKET_PRIORITIES,
    )


@bp.route("/<int:ticket_id>/update", methods=["POST"])
@login_required
def add_update(ticket_id):
    """Adiciona uma mensagem ao histórico do ticket."""
    ticket = _get_ticket_or_404(ticket_id)
    _ensure_can_view(ticket)  # cliente só atualiza ticket próprio

    try:
        data = _message_schema.load(request.form.to_dict())
    except ValidationError as err:
        flash("Mensagem inválida: ela é obrigatória (1 a 255 caracteres).", "error")
        return (
            render_template(
                "tickets/detail.html",
                ticket=ticket,
                agents=_agents() if g.user.is_agent else [],
                statuses=TICKET_STATUSES,
                priorities=TICKET_PRIORITIES,
                errors=err.messages,
            ),
            400,
        )

    update = TicketUpdate(
        ticket_id=ticket.id,
        author_id=g.user.id,
        message=data["message"],
    )
    db.session.add(update)
    db.session.commit()

    flash("Atualização adicionada.", "success")
    return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))


@bp.route("/<int:ticket_id>/edit", methods=["POST"])
@agent_required
def edit_ticket(ticket_id):
    """Alteração administrativa (status, prioridade, agente). Somente agente."""
    ticket = _get_ticket_or_404(ticket_id)

    try:
        data = _edit_schema.load(request.form.to_dict())
    except ValidationError as err:
        flash("Dados inválidos para atualização do ticket.", "error")
        return (
            render_template(
                "tickets/detail.html",
                ticket=ticket,
                agents=_agents(),
                statuses=TICKET_STATUSES,
                priorities=TICKET_PRIORITIES,
                errors=err.messages,
            ),
            400,
        )

    # agent_id, se informado, precisa existir e ter role "agent".
    agent_id = data.get("agent_id")
    if agent_id is not None:
        agent = db.session.get(User, agent_id)
        if agent is None or agent.role != ROLE_AGENT:
            flash("Responsável inválido: deve ser um usuário com perfil de agente.", "error")
            return (
                render_template(
                    "tickets/detail.html",
                    ticket=ticket,
                    agents=_agents(),
                    statuses=TICKET_STATUSES,
                    priorities=TICKET_PRIORITIES,
                    errors={"agent_id": ["Agente inválido."]},
                ),
                400,
            )
        ticket.agent_id = agent_id
    elif "agent_id" in request.form:
        # Campo enviado vazio => desatribui o ticket.
        ticket.agent_id = None

    if data.get("status") is not None:
        ticket.status = data["status"]
    if data.get("priority") is not None:
        ticket.priority = data["priority"]

    db.session.commit()
    flash("Ticket atualizado.", "success")
    return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))
