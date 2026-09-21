from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = { "sub": subject, "exp": expire }

    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)