"""
Authentication routes.

POST /auth/register          → create account + send verify email
POST /auth/login             → issue access + refresh tokens
POST /auth/refresh           → rotate access token
GET  /auth/verify-email      → activate account via token link
POST /auth/forgot-password   → send reset email
POST /auth/reset-password    → apply new password from token
GET  /auth/me                → current user info (requires auth)
"""

from fastapi import APIRouter, BackgroundTasks, Query
from fastapi.responses import JSONResponse

from app.dependencies import CurrentUser, DB
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.user import UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(payload: RegisterRequest, db: DB):
    user = await auth_service.register_user(payload, db)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: DB):
    return await auth_service.login_user(
        payload.email, payload.password, db
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: DB):
    return await auth_service.refresh_access_token(
        payload.refresh_token, db
    )


@router.get("/verify-email")
async def verify_email(token: str = Query(...), db: DB = None):
    await auth_service.verify_email(token, db)
    return {"message": "Email verified. You can now log in."}


@router.post("/forgot-password", status_code=202)
async def forgot_password(payload: ForgotPasswordRequest, db: DB):
    await auth_service.request_password_reset(payload.email, db)
    return {
        "message": (
            "If that email is registered, you will receive "
            "a password reset link shortly."
        )
    }


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: DB):
    await auth_service.reset_password(
        payload.token, payload.new_password, db
    )
    return {"message": "Password updated. You can now log in."}


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user
