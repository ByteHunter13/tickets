# Importar todos los modelos aquí para que Alembic los detecte
from app.db.session import Base
from app.models.user import User
from app.models.ticket import Category, Ticket
from app.models.comment import Comment
from app.models.event import TicketEvent
from app.models.attachment import Attachment