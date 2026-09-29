from fastapi import BackgroundTasks

from app.models.ticket import Ticket
from app.models.user import User
from app.services.email import send_email


def notify_ticket_created(background: BackgroundTasks, *, ticket: Ticket, creator: User) -> None:
    background.add_task(
        send_email,
        creator.email,
        f"Ticket #{ticket.id} creado",
        f"Hola {creator.full_name},\n\n"
        f'Registramos tu ticket #{ticket.id}: "{ticket.title}".\n'
        "Te avisaremos por correo ante cualquier novedad.\n\n"
        "Equipo de soporte",
    )


def notify_ticket_assigned(background: BackgroundTasks, *, ticket: Ticket) -> None:
    assignee = ticket.assigned_to
    if assignee is None:
        return

    background.add_task(
        send_email,
        assignee.email,
        f"Ticket #{ticket.id} asignado a ti",
        f"Hola {assignee.full_name},\n\n"
        f'Se te asignó el ticket #{ticket.id}: "{ticket.title}".\n\n'
        "Equipo de soporte",
    )


def notify_status_changed(background: BackgroundTasks, *, ticket: Ticket) -> None:
    creator = ticket.created_by

    background.add_task(
        send_email,
        creator.email,
        f"Ticket #{ticket.id}: nuevo estado {ticket.status.value}",
        f"Hola {creator.full_name},\n\n"
        f'Tu ticket #{ticket.id} ("{ticket.title}") cambió de estado a: {ticket.status.value}.\n\n'
        "Equipo de soporte",
    )


def notify_new_comment(background: BackgroundTasks, *, ticket: Ticket, actor: User) -> None:
    # Las dos partes de la conversación son el creador y el agente asignado;
    # se notifica a la que no escribió el comentario.
    recipient = ticket.assigned_to if actor.id == ticket.created_by_id else ticket.created_by

    if recipient is None or recipient.id == actor.id:
        return

    background.add_task(
        send_email,
        recipient.email,
        f"Nuevo comentario en el ticket #{ticket.id}",
        f"Hola {recipient.full_name},\n\n"
        f'{actor.full_name} agregó un comentario en el ticket #{ticket.id} ("{ticket.title}").\n\n'
        "Equipo de soporte",
    )
