"""Autenticação por sessão: login e logout."""

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from marshmallow import ValidationError

from ...extensions import db, limiter
from ...models import User
from ...schemas import UserLoginSchema

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _login_rate_limit() -> str:
    """Limite de login lido da config (permite ajuste por ambiente)."""
    from flask import current_app

    return current_app.config.get("LOGIN_RATE_LIMIT", "10 per minute")

_login_schema = UserLoginSchema()

# Mensagem genérica: nunca revela se o e-mail existe ou se a senha está errada.
_GENERIC_LOGIN_ERROR = "E-mail ou senha inválidos."


def _safe_next(target: str | None) -> str:
    """Evita open-redirect: só aceita caminhos internos relativos."""
    if not target:
        return url_for("pages.home")
    # Recusa URLs absolutas / com esquema ou host externo.
    if target.startswith("//") or "://" in target:
        return url_for("pages.home")
    if not target.startswith("/"):
        return url_for("pages.home")
    return target


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit(_login_rate_limit, methods=["POST"])
def login():
    # Usuário já autenticado não precisa ver o formulário de login.
    if g.get("user") is not None:
        return redirect(url_for("pages.home"))

    if request.method == "POST":
        try:
            data = _login_schema.load(request.form.to_dict())
        except ValidationError:
            # Não detalhamos qual campo falhou para não vazar informação.
            flash(_GENERIC_LOGIN_ERROR, "error")
            return render_template("auth/login.html"), 400

        user = db.session.execute(
            db.select(User).filter_by(email=data["email"])
        ).scalar_one_or_none()

        if user is None or not user.check_password(data["password"]):
            flash(_GENERIC_LOGIN_ERROR, "error")
            return render_template("auth/login.html"), 401

        # Sucesso: regenera a sessão e guarda apenas o id do usuário.
        session.clear()
        session["user_id"] = user.id
        flash("Login realizado com sucesso.", "success")
        return redirect(_safe_next(request.args.get("next")))

    return render_template("auth/login.html")


@bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    g.user = None
    flash("Você saiu da sua conta.", "success")
    return redirect(url_for("auth.login"))
