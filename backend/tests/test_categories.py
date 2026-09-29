from app.models.enums import Role


def test_list_categories(client, make_user, make_category, auth_header):
    user = make_user(role=Role.user)
    category = make_category()

    response = client.get("/api/v1/categories", headers=auth_header(user))

    assert response.status_code == 200
    body = response.json()
    assert any(item["id"] == category.id and item["name"] == category.name for item in body)


def test_list_categories_requires_auth(client):
    response = client.get("/api/v1/categories")

    assert response.status_code == 401
