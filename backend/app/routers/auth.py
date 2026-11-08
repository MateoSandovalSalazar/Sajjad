"""
Authentication routes.

POST /auth/register          → create account + send verify email
POST /auth/login             → issue access + refresh tokens
POST /auth/refresh           → rotate access token
GET  /auth/verify-email      → activate account via token link
POST /auth/resend-verification → reenvía el correo de verificación
POST /auth/forgot-password   → send reset email
POST /auth/reset-password    → apply new password from token
GET  /auth/me                → current user info (requires auth)

Todos los endpoints públicos llevan rate limit por IP: son la
superficie que un atacante puede golpear sin credenciales. Los
valores están en core/ratelimit.py.

SlowAPI exige que el endpoint reciba `request: Request` — de ahí
que aparezca aunque el cuerpo de la función no lo use.
"""

from fastapi import APIRouter, Query, Request

from app.core import ratelimit as rl
from app.core.ratelimit import limiter
from app.dependencies import DB, CurrentUser
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.user import UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
@limiter.limit(rl.REGISTER)
async def register(request: Request, payload: RegisterRequest, db: DB):
    user = await auth_service.register_user(payload, db)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit(rl.LOGIN)
async def login(request: Request, payload: LoginRequest, db: DB):
    return await auth_service.login_user(
        payload.email, payload.password, db
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(rl.REFRESH)
async def refresh(request: Request, payload: RefreshRequest, db: DB):
    return await auth_service.refresh_access_token(
        payload.refresh_token, db
    )


@router.get("/verify-email")
@limiter.limit(rl.TOKEN_SUBMIT)
async def verify_email(
    request: Request, token: str = Query(...), db: DB = None
):
    await auth_service.verify_email(token, db)
    return {"message": "Email verified. You can now log in."}


@router.post("/resend-verification", status_code=202)
@limiter.limit(rl.VERIFICATION_RESEND)
async def resend_verification(
    request: Request, payload: ResendVerificationRequest, db: DB
):
    await auth_service.resend_verification_email(payload.email, db)
    return {
        "message": (
            "If that email is registered and not yet verified, "
            "you will receive a new verification link shortly."
        )
    }


@router.post("/forgot-password", status_code=202)
@limiter.limit(rl.PASSWORD_RESET_REQUEST)
async def forgot_password(
    request: Request, payload: ForgotPasswordRequest, db: DB
):
    await auth_service.request_password_reset(payload.email, db)
    return {
        "message": (
            "If that email is registered, you will receive "
            "a password reset link shortly."
        )
    }


@router.post("/reset-password")
@limiter.limit(rl.TOKEN_SUBMIT)
async def reset_password(
    request: Request, payload: ResetPasswordRequest, db: DB
):
    await auth_service.reset_password(
        payload.token, payload.new_password, db
    )
    return {"message": "Password updated. You can now log in."}


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user
