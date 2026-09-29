from sqlalchemy import select

from app.models.enums import Role, TicketEventType
from app.models.event import TicketEvent


def test_create_comment_as_user(client, make_user, make_ticket, auth_header):
    user = make_user(role=Role.user)
    ticket = make_ticket(created_by=user)

    response = client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={"body": "Sigo esperando una respuesta"},
        headers=auth_header(user),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["body"] == "Sigo esperando una respuesta"
    assert body["is_internal"] is False
    assert body["author"]["id"] == user.id


def test_user_cannot_create_internal_comment(client, make_user, make_ticket, auth_header):
    user = make_user(role=Role.user)
    ticket = make_ticket(created_by=user)

    response = client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={"body": "Nota interna", "is_internal": True},
        headers=auth_header(user),
    )

    assert response.status_code == 403


def test_agent_can_create_internal_comment(client, make_user, make_ticket, auth_header):
    agent = make_user(role=Role.agent)
    ticket = make_ticket()

    response = client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={"body": "Nota interna para el equipo", "is_internal": True},
        headers=auth_header(agent),
    )

    assert response.status_code == 201
    assert response.json()["is_internal"] is True


def test_create_comment_logs_comment_added_event(
    client, make_user, make_ticket, auth_header, db_session
):
    user = make_user(role=Role.user)
    ticket = make_ticket(created_by=user)

    client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={"body": "Comentario de prueba"},
        headers=auth_header(user),
    )

    events = db_session.scalars(
        select(TicketEvent).where(
            TicketEvent.ticket_id == ticket.id,
            TicketEvent.event_type == TicketEventType.comment_added,
        )
    ).all()
    assert len(events) == 1


def test_user_cannot_comment_on_others_ticket(client, make_user, make_ticket, auth_header):
    user = make_user(role=Role.user)
    other = make_user(role=Role.user)
    ticket = make_ticket(created_by=other)

    response = client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={"body": "Comentario de prueba"},
        headers=auth_header(user),
    )

    assert response.status_code == 404


def test_user_does_not_see_internal_comments_in_list(
    client, make_user, make_ticket, auth_header
):
    user = make_user(role=Role.user)
    agent = make_user(role=Role.agent)
    ticket = make_ticket(created_by=user)

    client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={"body": "Comentario público"},
        headers=auth_header(user),
    )
    client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={"body": "Nota interna", "is_internal": True},
        headers=auth_header(agent),
    )

    response = client.get(
        f"/api/v1/tickets/{ticket.id}/comments", headers=auth_header(user)
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert all(item["is_internal"] is False for item in body)


def test_agent_sees_internal_comments_in_list(client, make_user, make_ticket, auth_header):
    agent = make_user(role=Role.agent)
    ticket = make_ticket()

    client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={"body": "Comentario público"},
        headers=auth_header(agent),
    )
    client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={"body": "Nota interna", "is_internal": True},
        headers=auth_header(agent),
    )

    response = client.get(
        f"/api/v1/tickets/{ticket.id}/comments", headers=auth_header(agent)
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2


def test_list_comments_requires_auth(client, make_ticket):
    ticket = make_ticket()

    response = client.get(f"/api/v1/tickets/{ticket.id}/comments")

    assert response.status_code == 401
