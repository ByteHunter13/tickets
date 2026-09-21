from sqlalchemy import select

from app.models.enums import Role, TicketEventType, TicketStatus
from app.models.event import TicketEvent


def test_create_ticket_as_user(client, make_user, make_category, auth_header, db_session):
    user = make_user(role=Role.user)
    category = make_category()

    response = client.post(
        "/api/v1/tickets",
        json={
            "title": "No puedo iniciar sesión",
            "description": "Me sale un error al iniciar sesión desde ayer",
            "category_id": category.id,
        },
        headers=auth_header(user),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "open"
    assert body["created_by"]["id"] == user.id

    events = db_session.scalars(
        select(TicketEvent).where(TicketEvent.ticket_id == body["id"])
    ).all()
    assert len(events) == 1
    assert events[0].event_type == TicketEventType.ticket_created


def test_create_ticket_requires_auth(client, make_category):
    category = make_category()

    response = client.post(
        "/api/v1/tickets",
        json={"title": "Título", "description": "Descripción larga", "category_id": category.id},
    )

    assert response.status_code == 401


def test_create_ticket_invalid_title_too_short(client, make_user, make_category, auth_header):
    user = make_user()
    category = make_category()

    response = client.post(
        "/api/v1/tickets",
        json={"title": "hi", "description": "Descripción larga", "category_id": category.id},
        headers=auth_header(user),
    )

    assert response.status_code == 422


def test_list_tickets_user_sees_only_own(client, make_user, make_ticket, auth_header):
    user = make_user(role=Role.user)
    other = make_user(role=Role.user)
    make_ticket(created_by=user)
    make_ticket(created_by=other)

    response = client.get("/api/v1/tickets", headers=auth_header(user))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert all(item["created_by"]["id"] == user.id for item in body["items"])


def test_list_tickets_agent_sees_all(client, make_user, make_ticket, auth_header):
    agent = make_user(role=Role.agent)
    make_ticket()
    make_ticket()

    response = client.get("/api/v1/tickets", headers=auth_header(agent))

    assert response.status_code == 200
    assert response.json()["total"] >= 2


def test_list_tickets_filter_by_status(client, make_user, make_ticket, auth_header):
    agent = make_user(role=Role.agent)
    make_ticket(status=TicketStatus.open)
    make_ticket(status=TicketStatus.closed)

    response = client.get(
        "/api/v1/tickets", params={"status": "closed"}, headers=auth_header(agent)
    )

    assert response.status_code == 200
    body = response.json()
    assert all(item["status"] == "closed" for item in body["items"])


def test_list_tickets_pagination_fields(client, make_user, make_ticket, auth_header):
    agent = make_user(role=Role.agent)
    for _ in range(3):
        make_ticket()

    response = client.get(
        "/api/v1/tickets", params={"page": 1, "page_size": 2}, headers=auth_header(agent)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert len(body["items"]) == 2


def test_list_tickets_requires_auth(client):
    response = client.get("/api/v1/tickets")

    assert response.status_code == 401


def test_get_own_ticket_as_user(client, make_user, make_ticket, auth_header):
    user = make_user(role=Role.user)
    ticket = make_ticket(created_by=user)

    response = client.get(f"/api/v1/tickets/{ticket.id}", headers=auth_header(user))

    assert response.status_code == 200
    assert response.json()["id"] == ticket.id


def test_get_others_ticket_as_user_returns_404(client, make_user, make_ticket, auth_header):
    user = make_user(role=Role.user)
    other = make_user(role=Role.user)
    ticket = make_ticket(created_by=other)

    response = client.get(f"/api/v1/tickets/{ticket.id}", headers=auth_header(user))

    assert response.status_code == 404


def test_get_any_ticket_as_agent(client, make_user, make_ticket, auth_header):
    agent = make_user(role=Role.agent)
    ticket = make_ticket()

    response = client.get(f"/api/v1/tickets/{ticket.id}", headers=auth_header(agent))

    assert response.status_code == 200


def test_get_ticket_not_found(client, make_user, auth_header):
    user = make_user()

    response = client.get("/api/v1/tickets/999999", headers=auth_header(user))

    assert response.status_code == 404


def test_update_own_ticket_while_open(client, make_user, make_ticket, auth_header):
    user = make_user(role=Role.user)
    ticket = make_ticket(created_by=user, status=TicketStatus.open)

    response = client.patch(
        f"/api/v1/tickets/{ticket.id}",
        json={"title": "Nuevo título más claro"},
        headers=auth_header(user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Nuevo título más claro"
    assert body["description"] == ticket.description


def test_update_own_ticket_after_in_progress_fails(client, make_user, make_ticket, auth_header):
    user = make_user(role=Role.user)
    ticket = make_ticket(created_by=user, status=TicketStatus.in_progress)

    response = client.patch(
        f"/api/v1/tickets/{ticket.id}",
        json={"title": "Nuevo título más claro"},
        headers=auth_header(user),
    )

    assert response.status_code == 400


def test_update_others_ticket_returns_404(client, make_user, make_ticket, auth_header):
    user = make_user(role=Role.user)
    other = make_user(role=Role.user)
    ticket = make_ticket(created_by=other, status=TicketStatus.open)

    response = client.patch(
        f"/api/v1/tickets/{ticket.id}",
        json={"title": "Nuevo título más claro"},
        headers=auth_header(user),
    )

    assert response.status_code == 404


def test_staff_update_status_as_agent(client, make_user, make_ticket, auth_header):
    agent = make_user(role=Role.agent)
    ticket = make_ticket(status=TicketStatus.open)

    response = client.patch(
        f"/api/v1/tickets/{ticket.id}/staff",
        json={"status": "in_progress"},
        headers=auth_header(agent),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_staff_update_forbidden_for_regular_user(client, make_user, make_ticket, auth_header):
    user = make_user(role=Role.user)
    ticket = make_ticket(created_by=user)

    response = client.patch(
        f"/api/v1/tickets/{ticket.id}/staff",
        json={"status": "in_progress"},
        headers=auth_header(user),
    )

    assert response.status_code == 403


def test_staff_update_sets_closed_at_when_closed(client, make_user, make_ticket, auth_header):
    agent = make_user(role=Role.agent)
    ticket = make_ticket(status=TicketStatus.resolved)

    response = client.patch(
        f"/api/v1/tickets/{ticket.id}/staff",
        json={"status": "closed"},
        headers=auth_header(agent),
    )

    assert response.status_code == 200
    assert response.json()["closed_at"] is not None


def test_staff_update_clears_closed_at_when_reopened(client, make_user, make_ticket, auth_header):
    agent = make_user(role=Role.agent)
    ticket = make_ticket(status=TicketStatus.closed)

    response = client.patch(
        f"/api/v1/tickets/{ticket.id}/staff",
        json={"status": "open"},
        headers=auth_header(agent),
    )

    assert response.status_code == 200
    assert response.json()["closed_at"] is None


def test_staff_update_assign_to_nonexistent_user_404(client, make_user, make_ticket, auth_header):
    agent = make_user(role=Role.agent)
    ticket = make_ticket()

    response = client.patch(
        f"/api/v1/tickets/{ticket.id}/staff",
        json={"assigned_to_id": 999999},
        headers=auth_header(agent),
    )

    assert response.status_code == 404


def test_staff_update_assign_to_regular_user_role_rejected(
    client, make_user, make_ticket, auth_header
):
    agent = make_user(role=Role.agent)
    regular_user = make_user(role=Role.user)
    ticket = make_ticket()

    response = client.patch(
        f"/api/v1/tickets/{ticket.id}/staff",
        json={"assigned_to_id": regular_user.id},
        headers=auth_header(agent),
    )

    assert response.status_code == 400


def test_staff_update_logs_status_changed_event(
    client, make_user, make_ticket, auth_header, db_session
):
    agent = make_user(role=Role.agent)
    ticket = make_ticket(status=TicketStatus.open)

    client.patch(
        f"/api/v1/tickets/{ticket.id}/staff",
        json={"status": "in_progress"},
        headers=auth_header(agent),
    )

    events = db_session.scalars(
        select(TicketEvent).where(
            TicketEvent.ticket_id == ticket.id,
            TicketEvent.event_type == TicketEventType.status_changed,
        )
    ).all()
    assert len(events) == 1
    assert events[0].old_value == "open"
    assert events[0].new_value == "in_progress"


def test_staff_update_logs_assignment_changed_event(
    client, make_user, make_ticket, auth_header, db_session
):
    agent = make_user(role=Role.agent)
    assignee = make_user(role=Role.agent)
    ticket = make_ticket()

    client.patch(
        f"/api/v1/tickets/{ticket.id}/staff",
        json={"assigned_to_id": assignee.id},
        headers=auth_header(agent),
    )

    events = db_session.scalars(
        select(TicketEvent).where(
            TicketEvent.ticket_id == ticket.id,
            TicketEvent.event_type == TicketEventType.assignment_changed,
        )
    ).all()
    assert len(events) == 1
    assert events[0].new_value == str(assignee.id)
