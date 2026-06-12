"""JWT-based authentication utilities."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext

import app.db.session as _db
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import UserRead

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Token ─────────────────────────────────────────────────────────────────────

def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expire_days)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> str:
    """Return user_id from a valid JWT, else raise 401."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="无效令牌")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="无效或已过期的令牌")


# ── User CRUD ─────────────────────────────────────────────────────────────────

def get_user_by_email(email: str) -> User | None:
    with _db.db_session() as db:
        user = db.query(User).filter(User.email == email).first()
        if user is not None:
            db.expunge(user)
        return user


def get_user_by_id(user_id: str) -> User | None:
    with _db.db_session() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user is not None:
            db.expunge(user)
        return user


def create_user(email: str, password: str) -> UserRead:
    if get_user_by_email(email) is not None:
        raise HTTPException(status_code=409, detail="该邮箱已注册")
    if len(password) < 6:
        raise HTTPException(status_code=422, detail="密码至少 6 位")

    user = User(
        id=uuid4().hex,
        email=email,
        hashed_password=hash_password(password),
    )
    with _db.db_session() as db:
        db.add(user)
        db.flush()
        return UserRead(id=user.id, email=user.email, created_at=user.created_at)


def authenticate_user(email: str, password: str) -> User:
    user = get_user_by_email(email)
    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    return user
