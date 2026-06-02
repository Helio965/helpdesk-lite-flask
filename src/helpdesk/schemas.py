"""Schemas Marshmallow para validação server-side e proteção contra
*mass assignment*.

Estratégia de segurança:

* Cada schema declara explicitamente (whitelist) os campos aceitos do cliente.
* ``Meta.unknown = EXCLUDE`` descarta silenciosamente qualquer campo não
  declarado (ex.: ``role``, ``id``, ``password_hash``, ``customer_id``,
  ``status``, ``is_admin``). Assim, payloads maliciosos não conseguem
  sobrescrever atributos internos.
* As rotas nunca fazem ``Model(**request.form)``; elas usam os dados já
  validados e atribuem campos sensíveis de forma explícita no servidor.
"""

from marshmallow import EXCLUDE, Schema, fields, pre_load, validate

from .models import TICKET_PRIORITIES, TICKET_STATUSES


class _BaseSchema(Schema):
    """Base que descarta campos desconhecidos (anti mass assignment)."""

    class Meta:
        unknown = EXCLUDE


class UserCreateSchema(_BaseSchema):
    """Criação de usuário.

    Aceita apenas ``name``, ``email`` e ``password``. Campos como ``role``,
    ``id``, ``created_at`` e ``password_hash`` NÃO são aceitos do cliente: a
    *role* é sempre controlada pelo servidor (usuários criados pelo formulário
    nascem como ``customer``).
    """

    name = fields.Str(required=True, validate=validate.Length(min=2, max=80))
    email = fields.Email(required=True, validate=validate.Length(max=120))
    password = fields.Str(required=True, validate=validate.Length(min=6, max=128))


class UserLoginSchema(_BaseSchema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=1))


class TicketCreateSchema(_BaseSchema):
    """Criação de ticket pelo cliente autenticado.

    Aceita ``title``, ``description`` e ``priority``. Não aceita ``id``,
    ``customer_id``, ``agent_id``, ``status``, ``created_at`` nem
    ``updated_at`` — o servidor define ``customer_id`` (usuário logado) e
    ``status = "open"``.
    """

    title = fields.Str(required=True, validate=validate.Length(min=3, max=120))
    description = fields.Str(
        load_default="", allow_none=True, validate=validate.Length(max=5000)
    )
    priority = fields.Str(
        load_default="medium", validate=validate.OneOf(TICKET_PRIORITIES)
    )

    @pre_load
    def _normalize(self, data, **kwargs):
        data = dict(data)
        if data.get("description") is None:
            data["description"] = ""
        # Campo vazio no formulário deve cair no default de prioridade.
        if data.get("priority") in ("", None):
            data.pop("priority", None)
        return data


class TicketUpdateSchema(_BaseSchema):
    """Edição administrativa do ticket (apenas agente).

    Permite alterar ``status``, ``priority`` e ``agent_id``. A regra de que
    ``agent_id`` deve apontar para um usuário existente com role ``agent`` é
    verificada na rota (depende do banco de dados).
    """

    status = fields.Str(load_default=None, validate=validate.OneOf(TICKET_STATUSES))
    priority = fields.Str(
        load_default=None, validate=validate.OneOf(TICKET_PRIORITIES)
    )
    agent_id = fields.Int(load_default=None, allow_none=True)

    @pre_load
    def _empty_to_none(self, data, **kwargs):
        data = dict(data)
        if data.get("agent_id") in ("", None):
            data["agent_id"] = None
        return data


class TicketUpdateMessageSchema(_BaseSchema):
    """Mensagem de atualização adicionada ao histórico do ticket."""

    message = fields.Str(required=True, validate=validate.Length(min=1, max=255))
