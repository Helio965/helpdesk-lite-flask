"""Registro centralizado dos blueprints da aplicação."""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    from .auth import bp as auth_bp
    from .pages import bp as pages_bp
    from .tickets import bp as tickets_bp
    from .users import bp as users_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(tickets_bp)
