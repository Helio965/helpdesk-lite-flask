"""Testes de autenticação por sessão."""


def test_login_success_sets_session(client, customer_user):
    resp = client.post(
        "/auth/login",
        data={"email": "cliente1@example.com", "password": "Senha@123"},
    )
    assert resp.status_code == 302
    with client.session_transaction() as sess:
        assert sess["user_id"] == customer_user.id


def test_login_wrong_password_is_generic(client, customer_user):
    resp = client.post(
        "/auth/login",
        data={"email": "cliente1@example.com", "password": "errada"},
    )
    assert resp.status_code == 401
    assert "E-mail ou senha inválidos.".encode() in resp.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_login_unknown_email_is_generic(client):
    """E-mail inexistente devolve a MESMA mensagem que senha errada."""
    resp = client.post(
        "/auth/login",
        data={"email": "naoexiste@example.com", "password": "qualquer"},
    )
    assert resp.status_code == 401
    assert "E-mail ou senha inválidos.".encode() in resp.data


def test_logout_clears_session(logged_customer):
    resp = logged_customer.post("/auth/logout")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]
    with logged_customer.session_transaction() as sess:
        assert "user_id" not in sess


def test_protected_route_without_login_redirects(client):
    resp = client.get("/tickets/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_authenticated_user_accesses_protected_route(logged_customer):
    resp = logged_customer.get("/tickets/")
    assert resp.status_code == 200


def test_login_loads_user_into_g(client, agent_user):
    """Após login, g.user é carregado e a navegação reflete o papel."""
    client.post(
        "/auth/login",
        data={"email": "agente1@example.com", "password": "Senha@123"},
    )
    resp = client.get("/")
    assert resp.status_code == 200
    # Apenas agentes veem o link de usuários na navegação.
    assert b"/users" in resp.data
