import uuid
from pathlib import Path

from app.core.config import settings

# Mapear el tipo MIME a una extensión propia evita confiar en la extensión
# que manda el cliente junto al nombre original del archivo.
ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
}


def is_allowed_content_type(content_type: str | None) -> bool:
    return content_type in ALLOWED_CONTENT_TYPES


def save_file(data: bytes, content_type: str) -> str:
    extension = ALLOWED_CONTENT_TYPES[content_type]
    stored_name = uuid.uuid4().hex + extension

    upload_dir = Path(settings.uploads_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / stored_name).write_bytes(data)

    return stored_name


def delete_file(stored_name: str) -> None:
    get_file_path(stored_name).unlink(missing_ok=True)


def get_file_path(stored_name: str) -> Path:
    return Path(settings.uploads_dir) / stored_name


def sanitize_filename(filename: str) -> str:
    # Se queda solo con el nombre (sin componentes de ruta) y descarta
    # caracteres de control o reservados en nombres de archivo.
    name = Path(filename).name
    cleaned = "".join(c for c in name if c.isprintable() and c not in '\\/:*?"<>|')
    cleaned = cleaned.strip().strip(".")
    return cleaned or "archivo"
