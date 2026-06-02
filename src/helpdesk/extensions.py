"""Instâncias únicas das extensões Flask usadas pela aplicação.

Mantê-las em um módulo separado evita importações circulares: os modelos
importam ``db`` daqui e a *app factory* (``create_app``) chama ``init_app``
sobre cada extensão já criada.
"""

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# ORM principal de persistência (Flask-SQLAlchemy).
db = SQLAlchemy()

# Migrations baseadas em Alembic (Flask-Migrate).
migrate = Migrate()
