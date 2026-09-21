from app.models.enums import Role

def test_list_users_as_admin(client, make_user, auth_header):
    admin = make_user(role=Role.admin)
    make_user(role=Role.user)

    response = client.get("/api/v1/users", headers=auth_header(admin))

    assert response.status_code == 200
    assert len(response.json()) >= 2

def test_list_users_as_agent(client, make_user, auth_header):
    agent = make_user(role=Role.agent)

    response = client.get("/api/v1/users", headers=auth_header(agent))

    assert response.status_code == 200

def test_list_users_forbidden_for_regular_user(client, make_user, auth_header):
    user = make_user(role=Role.user)

    response = client.get("/api/v1/users", headers=auth_header(user))

    assert response.status_code == 403

def test_list_users_requires_auth(client):
    response = client.get("/api/v1/users")

    assert response.status_code == 401

def test_update_role_as_admin(client, make_user, auth_header):
    admin = make_user(role=Role.admin)
    target = make_user(role=Role.user)

    response = client.patch(
        f"/api/v1/users/{target.id}/role",
        json={"role": "agent"},
        headers=auth_header(admin),
    )

    assert response.status_code == 200
    assert response.json()["role"] == "agent"

def test_update_role_forbidden_for_agent(client, make_user, auth_header):
    agent = make_user(role=Role.agent)
    target = make_user(role=Role.user)

    response = client.patch(
        f"/api/v1/users/{target.id}/role",
        json={"role": "admin"},
        headers=auth_header(agent),
    )

    assert response.status_code == 403

def test_update_role_unknown_user_returns_404(client, make_user, auth_header):
    admin = make_user(role=Role.admin)

    response = client.patch(
        "/api/v1/users/999999/role",
        json={"role": "agent"},
        headers=auth_header(admin),
    )

    assert response.status_code == 404

def test_deactivate_user_as_admin(client, make_user, auth_header):
    admin = make_user(role=Role.admin)
    target = make_user(role=Role.user)

    response = client.patch(
        f"/api/v1/users/{target.id}/active",
        json={"is_active": False},
        headers=auth_header(admin),
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

def test_deactivated_user_token_stops_working(client, make_user, auth_header):
    admin = make_user(role=Role.admin)
    target = make_user(role=Role.user)
    target_headers = auth_header(target)

    client.patch(
        f"/api/v1/users/{target.id}/active",
        json={"is_active": False},
        headers=auth_header(admin),
    )

    response = client.get("/api/v1/auth/me", headers=target_headers)

    assert response.status_code == 401

def test_admin_cannot_remove_own_admin_role(client, make_user, auth_header):
    admin = make_user(role=Role.admin)

    response = client.patch(
        f"/api/v1/users/{admin.id}/role",
        json={"role": "agent"},
        headers=auth_header(admin),
    )

    assert response.status_code == 400

def test_admin_can_keep_own_role_as_admin(client, make_user, auth_header):
    admin = make_user(role=Role.admin)

    response = client.patch(
        f"/api/v1/users/{admin.id}/role",
        json={"role": "admin"},
        headers=auth_header(admin),
    )

    assert response.status_code == 200

def test_admin_cannot_deactivate_self(client, make_user, auth_header):
    admin = make_user(role=Role.admin)

    response = client.patch(
        f"/api/v1/users/{admin.id}/active",
        json={"is_active": False},
        headers=auth_header(admin),
    )

    assert response.status_code == 400

def test_update_active_forbidden_for_agent(client, make_user, auth_header):
    agent = make_user(role=Role.agent)
    target = make_user(role=Role.user)

    response = client.patch(
        f"/api/v1/users/{target.id}/active",
        json={"is_active": False},
        headers=auth_header(agent),
    )

    assert response.status_code == 403
