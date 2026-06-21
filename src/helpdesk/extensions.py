"""Instâncias únicas das extensões Flask usadas pela aplicação.

Mantê-las em um módulo separado evita importações circulares: os modelos
importam ``db`` daqui e a *app factory* (``create_app``) chama ``init_app``
sobre cada extensão já criada.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

# ORM principal de persistência (Flask-SQLAlchemy).
db = SQLAlchemy()

# Migrations baseadas em Alembic (Flask-Migrate).
migrate = Migrate()

# Proteção CSRF para todos os formulários POST (Flask-WTF).
csrf = CSRFProtect()

# Rate limiting (Flask-Limiter). Identifica o cliente pelo IP de origem.
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
