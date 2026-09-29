from app.models.enums import Role, TicketPriority, TicketStatus


def test_status_changed_twice_creates_two_events(client, make_user, make_ticket, auth_header):
    agent = make_user(role=Role.agent)
    ticket = make_ticket(status=TicketStatus.open)

    client.patch(
        f"/api/v1/tickets/{ticket.id}/staff",
        json={"status": "in_progress"},
        headers=auth_header(agent),
    )
    client.patch(
        f"/api/v1/tickets/{ticket.id}/staff",
        json={"status": "resolved"},
        headers=auth_header(agent),
    )

    response = client.get(f"/api/v1/tickets/{ticket.id}/events", headers=auth_header(agent))

    assert response.status_code == 200
    status_events = [e for e in response.json() if e["event_type"] == "status_changed"]
    assert len(status_events) == 2
    assert status_events[0]["old_value"] == "open"
    assert status_events[0]["new_value"] == "in_progress"
    assert status_events[1]["old_value"] == "in_progress"
    assert status_events[1]["new_value"] == "resolved"


def test_setting_same_value_does_not_create_event(client, make_user, make_ticket, auth_header):
    agent = make_user(role=Role.agent)
    ticket = make_ticket(priority=TicketPriority.medium)

    client.patch(
        f"/api/v1/tickets/{ticket.id}/staff",
        json={"priority": "medium"},
        headers=auth_header(agent),
    )

    response = client.get(f"/api/v1/tickets/{ticket.id}/events", headers=auth_header(agent))

    assert response.status_code == 200
    priority_events = [e for e in response.json() if e["event_type"] == "priority_changed"]
    assert len(priority_events) == 0


def test_events_include_ticket_created_and_comment_added(
    client, make_user, make_category, auth_header
):
    user = make_user(role=Role.user)
    category = make_category()

    create_response = client.post(
        "/api/v1/tickets",
        json={
            "title": "No puedo iniciar sesión",
            "description": "Me sale un error al iniciar sesión desde ayer",
            "category_id": category.id,
        },
        headers=auth_header(user),
    )
    ticket_id = create_response.json()["id"]

    client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={"body": "Comentario de prueba"},
        headers=auth_header(user),
    )

    response = client.get(f"/api/v1/tickets/{ticket_id}/events", headers=auth_header(user))

    assert response.status_code == 200
    event_types = [e["event_type"] for e in response.json()]
    assert event_types == ["ticket_created", "comment_added"]


def test_user_cannot_see_others_ticket_events(client, make_user, make_ticket, auth_header):
    user = make_user(role=Role.user)
    other = make_user(role=Role.user)
    ticket = make_ticket(created_by=other)

    response = client.get(f"/api/v1/tickets/{ticket.id}/events", headers=auth_header(user))

    assert response.status_code == 404


def test_list_events_requires_auth(client, make_ticket):
    ticket = make_ticket()

    response = client.get(f"/api/v1/tickets/{ticket.id}/events")

    assert response.status_code == 401
