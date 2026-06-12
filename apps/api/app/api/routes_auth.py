from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUserID
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserRead
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    create_user,
    get_user_by_id,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest) -> TokenResponse:
    user = create_user(body.email, body.password)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    user = authenticate_user(body.email, body.password)
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserRead)
def me(user_id: CurrentUserID) -> UserRead:
    if user_id is None:
        raise HTTPException(status_code=401, detail="需要登录账号（演示密码模式不支持 /me）")
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserRead(id=user.id, email=user.email, created_at=user.created_at)
