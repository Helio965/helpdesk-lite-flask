"""HelpDesk Lite — *app factory*.

Aplicação web Flask tradicional (templates Jinja) com autenticação por
sessão, ORM (Flask-SQLAlchemy), migrations (Flask-Migrate) e validação
server-side (Marshmallow).
"""

from flask import Flask, g, render_template, session

from .config import Config
from .extensions import csrf, db, limiter, migrate

__all__ = ["create_app"]


def create_app(test_config=None) -> Flask:
    """Cria e configura a aplicação.

    ``test_config`` pode ser ``None`` (carrega ``Config`` a partir do
    ambiente), um dicionário ou um objeto/classe de configuração — útil para
    testes.
    """
    app = Flask(__name__, instance_relative_config=False)

    _load_config(app, test_config)

    # Extensões
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)

    # Registra os modelos no metadata para que o Flask-Migrate os detecte.
    from . import models  # noqa: F401

    _register_user_loader(app)
    _register_error_handlers(app)
    _register_security_headers(app)

    from .blueprints import register_blueprints
    from .cli import register_cli

    register_blueprints(app)
    register_cli(app)

    return app


def _load_config(app: Flask, test_config) -> None:
    if test_config is None:
        # Produção/desenvolvimento: variáveis vêm do ambiente (.env).
        from dotenv import load_dotenv

        load_dotenv()
        app.config.from_object(Config())
    elif isinstance(test_config, dict):
        app.config.from_mapping(test_config)
    else:
        # Classe ou instância de configuração.
        app.config.from_object(test_config)


def _register_user_loader(app: Flask) -> None:
    """Carrega o usuário autenticado em ``g.user`` a cada requisição."""
    from .models import User

    @app.before_request
    def load_logged_in_user():
        user_id = session.get("user_id")
        if user_id is None:
            g.user = None
            return
        user = db.session.get(User, user_id)
        if user is None:
            # Sessão aponta para usuário inexistente: limpa para evitar estado inválido.
            session.pop("user_id", None)
        g.user = user


def _register_error_handlers(app: Flask) -> None:
    from flask_wtf.csrf import CSRFError

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        # Token CSRF ausente/inválido: trata como requisição inválida (400).
        return render_template("errors/400.html", reason=error.description), 400

    @app.errorhandler(429)
    def too_many_requests(error):
        return render_template("errors/429.html"), 429

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500


def _register_security_headers(app: Flask) -> None:
    """Adiciona cabeçalhos de segurança em todas as respostas."""

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        # CSP simples: a UI usa apenas CSS inline próprio, sem scripts externos.
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; form-action 'self'; frame-ancestors 'none'",
        )
        return response
