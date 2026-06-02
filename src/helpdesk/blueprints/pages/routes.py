"""Páginas gerais (home/landing)."""

from flask import Blueprint, g, render_template

from ...extensions import db
from ...models import STATUS_CLOSED, STATUS_OPEN, Ticket

bp = Blueprint("pages", __name__)


@bp.route("/")
def home():
    # Usuário não autenticado: landing simples com link para o login.
    if g.get("user") is None:
        return render_template("pages/home.html", summary=None)

    # Autenticado: resumo de tickets de acordo com o papel.
    base = db.select(Ticket)
    if g.user.is_customer:
        base = base.filter_by(customer_id=g.user.id)

    total = db.session.scalar(
        db.select(db.func.count()).select_from(base.subquery())
    )
    open_count = db.session.scalar(
        db.select(db.func.count()).select_from(
            base.filter_by(status=STATUS_OPEN).subquery()
        )
    )
    closed_count = db.session.scalar(
        db.select(db.func.count()).select_from(
            base.filter_by(status=STATUS_CLOSED).subquery()
        )
    )

    summary = {
        "total": total or 0,
        "open": open_count or 0,
        "closed": closed_count or 0,
    }
    return render_template("pages/home.html", summary=summary)
