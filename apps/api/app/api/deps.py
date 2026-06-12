from typing import Annotated

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

_bearer = HTTPBearer(auto_error=False)


def _resolve_user_id(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> str | None:
    """Return authenticated user_id, or None for demo-password sessions."""
    if credentials is None:
        if settings.demo_password:
            raise HTTPException(status_code=401, detail="请输入访问密码")
        return None

    token = credentials.credentials

    try:
        from app.services.auth_service import decode_token
        return decode_token(token)
    except HTTPException:
        pass

    if settings.demo_password and token == settings.demo_password:
        return None

    raise HTTPException(status_code=401, detail="请输入访问密码或使用有效账号登录")


CurrentUserID = Annotated[str | None, Depends(_resolve_user_id)]
