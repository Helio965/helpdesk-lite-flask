"""Gestão de usuários — acesso restrito a agentes.

Não há cadastro público. A criação de usuários é feita por um agente e,
por segurança, sempre gera um usuário com role ``customer`` (a *role* é
controlada pelo servidor, nunca pelo payload do cliente).
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from marshmallow import ValidationError

from ...decorators import agent_required
from ...extensions import db
from ...models import ROLE_CUSTOMER, User
from ...schemas import UserCreateSchema

bp = Blueprint("users", __name__, url_prefix="/users")

_create_schema = UserCreateSchema()


@bp.route("/")
@agent_required
def list_users():
    users = (
        db.session.execute(db.select(User).order_by(User.created_at.desc()))
        .scalars()
        .all()
    )
    return render_template("users/list.html", users=users)


@bp.route("/create", methods=["GET", "POST"])
@agent_required
def create_user():
    if request.method == "POST":
        try:
            data = _create_schema.load(request.form.to_dict())
        except ValidationError as err:
            return (
                render_template(
                    "users/form.html", errors=err.messages, form=request.form
                ),
                400,
            )

        # E-mail único: verifica antes de inserir para dar mensagem clara.
        exists = db.session.execute(
            db.select(User).filter_by(email=data["email"])
        ).scalar_one_or_none()
        if exists is not None:
            return (
                render_template(
                    "users/form.html",
                    errors={"email": ["E-mail já cadastrado."]},
                    form=request.form,
                ),
                400,
            )

        # Atribuição EXPLÍCITA dos campos (nunca User(**data)).
        # role é forçada pelo servidor: novos usuários nascem como customer.
        user = User(name=data["name"], email=data["email"], role=ROLE_CUSTOMER)
        user.set_password(data["password"])
        db.session.add(user)
        db.session.commit()

        flash(f"Usuário '{user.name}' criado com sucesso.", "success")
        return redirect(url_for("users.list_users"))

    return render_template("users/form.html", errors={}, form={})
