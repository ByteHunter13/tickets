import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.enums import Role, TicketEventType
from app.models.event import TicketEvent


@pytest.fixture(autouse=True)
def isolated_uploads_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "uploads_dir", str(tmp_path))
    return tmp_path


def _png_bytes() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"0" * 100


def test_upload_attachment_as_owner(client, make_user, make_ticket, auth_header, isolated_uploads_dir):
    user = make_user(role=Role.user)
    ticket = make_ticket(created_by=user)

    response = client.post(
        f"/api/v1/tickets/{ticket.id}/attachments",
        files={"file": ("foto.png", _png_bytes(), "image/png")},
        headers=auth_header(user),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "foto.png"
    assert body["content_type"] == "image/png"
    assert body["uploaded_by"]["id"] == user.id

    stored_files = list(isolated_uploads_dir.iterdir())
    assert len(stored_files) == 1
    assert stored_files[0].suffix == ".png"


def test_upload_disallowed_type_returns_415(client, make_user, make_ticket, auth_header):
    user = make_user(role=Role.user)
    ticket = make_ticket(created_by=user)

    response = client.post(
        f"/api/v1/tickets/{ticket.id}/attachments",
        files={"file": ("virus.exe", b"MZ" + b"0" * 50, "application/x-msdownload")},
        headers=auth_header(user),
    )

    assert response.status_code == 415


def test_upload_too_large_returns_413(client, make_user, make_ticket, auth_header, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    user = make_user(role=Role.user)
    ticket = make_ticket(created_by=user)

    data = b"0" * (2 * 1024 * 1024)

    response = client.post(
        f"/api/v1/tickets/{ticket.id}/attachments",
        files={"file": ("grande.txt", data, "text/plain")},
        headers=auth_header(user),
    )

    assert response.status_code == 413


def test_download_by_uninvolved_user_returns_404(client, make_user, make_ticket, auth_header):
    owner = make_user(role=Role.user)
    stranger = make_user(role=Role.user)
    ticket = make_ticket(created_by=owner)

    upload_response = client.post(
        f"/api/v1/tickets/{ticket.id}/attachments",
        files={"file": ("foto.png", _png_bytes(), "image/png")},
        headers=auth_header(owner),
    )
    attachment_id = upload_response.json()["id"]

    response = client.get(
        f"/api/v1/attachments/{attachment_id}/download",
        headers=auth_header(stranger),
    )

    assert response.status_code == 404


def test_download_by_owner_succeeds(client, make_user, make_ticket, auth_header):
    user = make_user(role=Role.user)
    ticket = make_ticket(created_by=user)

    upload_response = client.post(
        f"/api/v1/tickets/{ticket.id}/attachments",
        files={"file": ("foto.png", _png_bytes(), "image/png")},
        headers=auth_header(user),
    )
    attachment_id = upload_response.json()["id"]

    response = client.get(
        f"/api/v1/attachments/{attachment_id}/download",
        headers=auth_header(user),
    )

    assert response.status_code == 200
    assert response.content == _png_bytes()


def test_delete_attachment_removes_file_from_disk(
    client, make_user, make_ticket, auth_header, isolated_uploads_dir
):
    user = make_user(role=Role.user)
    ticket = make_ticket(created_by=user)

    upload_response = client.post(
        f"/api/v1/tickets/{ticket.id}/attachments",
        files={"file": ("foto.png", _png_bytes(), "image/png")},
        headers=auth_header(user),
    )
    attachment_id = upload_response.json()["id"]
    assert len(list(isolated_uploads_dir.iterdir())) == 1

    response = client.delete(
        f"/api/v1/attachments/{attachment_id}", headers=auth_header(user)
    )

    assert response.status_code == 204
    assert list(isolated_uploads_dir.iterdir()) == []


def test_delete_by_non_owner_non_admin_forbidden(client, make_user, make_ticket, auth_header):
    owner = make_user(role=Role.user)
    agent = make_user(role=Role.agent)
    ticket = make_ticket(created_by=owner)

    upload_response = client.post(
        f"/api/v1/tickets/{ticket.id}/attachments",
        files={"file": ("foto.png", _png_bytes(), "image/png")},
        headers=auth_header(owner),
    )
    attachment_id = upload_response.json()["id"]

    response = client.delete(
        f"/api/v1/attachments/{attachment_id}", headers=auth_header(agent)
    )

    assert response.status_code == 403


def test_admin_can_delete_others_attachment(client, make_user, make_ticket, auth_header):
    owner = make_user(role=Role.user)
    admin = make_user(role=Role.admin)
    ticket = make_ticket(created_by=owner)

    upload_response = client.post(
        f"/api/v1/tickets/{ticket.id}/attachments",
        files={"file": ("foto.png", _png_bytes(), "image/png")},
        headers=auth_header(owner),
    )
    attachment_id = upload_response.json()["id"]

    response = client.delete(
        f"/api/v1/attachments/{attachment_id}", headers=auth_header(admin)
    )

    assert response.status_code == 204


def test_upload_logs_attachment_added_event(client, make_user, make_ticket, auth_header, db_session):
    user = make_user(role=Role.user)
    ticket = make_ticket(created_by=user)

    client.post(
        f"/api/v1/tickets/{ticket.id}/attachments",
        files={"file": ("foto.png", _png_bytes(), "image/png")},
        headers=auth_header(user),
    )

    events = db_session.scalars(
        select(TicketEvent).where(
            TicketEvent.ticket_id == ticket.id,
            TicketEvent.event_type == TicketEventType.attachment_added,
        )
    ).all()
    assert len(events) == 1


def test_upload_attachment_requires_auth(client, make_ticket):
    ticket = make_ticket()

    response = client.post(
        f"/api/v1/tickets/{ticket.id}/attachments",
        files={"file": ("foto.png", _png_bytes(), "image/png")},
    )

    assert response.status_code == 401
