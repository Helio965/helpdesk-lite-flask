"""Decorators de autenticação e autorização baseados em sessão.

O usuário autenticado é carregado em ``g.user`` por um ``before_request``
registrado na *app factory*. Estes decorators apenas inspecionam ``g.user``.
"""

from functools import wraps

from flask import abort, g, redirect, request, url_for

from .models import ROLE_AGENT


def login_required(view):
    """Exige um usuário autenticado; caso contrário redireciona ao login."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.get("user") is None:
            return redirect(url_for("auth.login", next=request.full_path))
        return view(*args, **kwargs)

    return wrapped


def agent_required(view):
    """Exige um usuário autenticado com role ``agent`` (senão 403)."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        user = g.get("user")
        if user is None:
            return redirect(url_for("auth.login", next=request.full_path))
        if user.role != ROLE_AGENT:
            abort(403)
        return view(*args, **kwargs)

    return wrapped
