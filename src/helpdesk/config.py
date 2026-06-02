"""Configuração da aplicação seguindo o princípio Twelve-Factor.

Todas as configurações sensíveis ou dependentes de ambiente são lidas de
variáveis de ambiente. Nenhum segredo fica embutido no código-fonte.
"""

import os


def _require(key: str, min_len: int = 0) -> str:
    """Lê uma variável de ambiente obrigatória.

    - Levanta ``RuntimeError`` se a variável estiver ausente ou vazia.
    - Levanta ``RuntimeError`` se o valor for menor que ``min_len``.
    """
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        raise RuntimeError(
            f"Configuração ausente: defina a variável de ambiente obrigatória '{key}'."
        )
    if len(value) < min_len:
        raise RuntimeError(
            f"Configuração inválida: '{key}' deve ter ao menos {min_len} caracteres."
        )
    return value


def _as_bool(value: str | None, default: bool = False) -> bool:
    """Converte uma string de ambiente em booleano de forma tolerante."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "t"}


class Config:
    """Configuração de produção/desenvolvimento.

    Os atributos sensíveis são resolvidos em ``__init__`` (e não no corpo da
    classe) para que a simples importação do módulo nunca exija que as
    variáveis de ambiente estejam presentes. Isso permite importar a
    configuração em testes sem disparar ``RuntimeError``.
    """

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    def __init__(self) -> None:
        self.SECRET_KEY = _require("SECRET_KEY", min_len=32)
        self.SQLALCHEMY_DATABASE_URI = _require("DATABASE_URL")
        self.SQLALCHEMY_TRACK_MODIFICATIONS = _as_bool(
            os.environ.get("SQLALCHEMY_TRACK_MODIFICATIONS"), default=False
        )
        self.DEBUG = _as_bool(os.environ.get("FLASK_DEBUG"), default=False)
        self.TICKETS_PER_PAGE = int(os.environ.get("TICKETS_PER_PAGE", "10"))


class TestConfig:
    """Configuração para a suíte de testes (SQLite em memória)."""

    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    # Necessário para assinar a sessão durante os testes.
    SECRET_KEY = "testing-secret-key-not-for-production-only-32+chars"
    TICKETS_PER_PAGE = 10
