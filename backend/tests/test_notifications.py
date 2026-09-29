import pytest

from app.models.enums import Role
from app.services import notifications


@pytest.fixture
def sent_emails(monkeypatch):
    calls = []

    def fake_send_email(to, subject, body):
        calls.append({"to": to, "subject": subject, "body": body})

    monkeypatch.setattr(notifications, "send_email", fake_send_email)
    return calls


def test_creating_ticket_sends_confirmation_to_creator(
    client, make_user, make_category, auth_header, sent_emails
):
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
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == user.email


def test_assigning_ticket_notifies_assignee(
    client, make_user, make_ticket, auth_header, sent_emails
):
    admin = make_user(role=Role.admin)
    agent = make_user(role=Role.agent)
    ticket = make_ticket()

    response = client.patch(
        f"/api/v1/tickets/{ticket.id}/staff",
        json={"assigned_to_id": agent.id},
        headers=auth_header(admin),
    )

    assert response.status_code == 200
    assignment_emails = [call for call in sent_emails if call["to"] == agent.email]
    assert len(assignment_emails) == 1
    assert f"#{ticket.id}" in assignment_emails[0]["subject"]


def test_status_change_notifies_creator(
    client, make_user, make_ticket, auth_header, sent_emails
):
    agent = make_user(role=Role.agent)
    creator = make_user(role=Role.user)
    ticket = make_ticket(created_by=creator)

    response = client.patch(
        f"/api/v1/tickets/{ticket.id}/staff",
        json={"status": "in_progress"},
        headers=auth_header(agent),
    )

    assert response.status_code == 200
    status_emails = [call for call in sent_emails if call["to"] == creator.email]
    assert len(status_emails) == 1


def test_setting_same_status_does_not_notify(
    client, make_user, make_ticket, auth_header, sent_emails
):
    from app.models.enums import TicketStatus

    agent = make_user(role=Role.agent)
    creator = make_user(role=Role.user)
    ticket = make_ticket(created_by=creator, status=TicketStatus.in_progress)

    response = client.patch(
        f"/api/v1/tickets/{ticket.id}/staff",
        json={"status": "in_progress"},
        headers=auth_header(agent),
    )

    assert response.status_code == 200
    assert sent_emails == []


def test_comment_by_creator_notifies_assigned_agent(
    client, make_user, make_ticket, auth_header, sent_emails
):
    creator = make_user(role=Role.user)
    agent = make_user(role=Role.agent)
    ticket = make_ticket(created_by=creator, assigned_to_id=agent.id)

    response = client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={"body": "Sigo esperando una respuesta"},
        headers=auth_header(creator),
    )

    assert response.status_code == 201
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == agent.email


def test_comment_by_agent_notifies_creator(
    client, make_user, make_ticket, auth_header, sent_emails
):
    creator = make_user(role=Role.user)
    agent = make_user(role=Role.agent)
    ticket = make_ticket(created_by=creator, assigned_to_id=agent.id)

    response = client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={"body": "Ya estamos revisando tu caso"},
        headers=auth_header(agent),
    )

    assert response.status_code == 201
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == creator.email


def test_internal_comment_does_not_notify_creator(
    client, make_user, make_ticket, auth_header, sent_emails
):
    creator = make_user(role=Role.user)
    agent = make_user(role=Role.agent)
    ticket = make_ticket(created_by=creator, assigned_to_id=agent.id)

    response = client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={"body": "Nota interna para el equipo", "is_internal": True},
        headers=auth_header(agent),
    )

    assert response.status_code == 201
    assert sent_emails == []


def test_comment_by_creator_without_assignee_sends_no_email(
    client, make_user, make_ticket, auth_header, sent_emails
):
    creator = make_user(role=Role.user)
    ticket = make_ticket(created_by=creator)

    response = client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={"body": "¿Hay alguna novedad?"},
        headers=auth_header(creator),
    )

    assert response.status_code == 201
    assert sent_emails == []
