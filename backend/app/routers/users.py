"""
User self-service routes.

GET    /users/me             → current profile (alias to /auth/me)
PATCH  /users/me             → update name / company
POST   /users/me/password    → change password
DELETE /users/me             → delete account (hard delete)
"""

from fastapi import APIRouter

from app.core.exceptions import Unauthorized
from app.core.security import hash_password, verify_password
from app.dependencies import DB, VerifiedUser
from app.schemas.user import ChangePasswordRequest, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_profile(user: VerifiedUser):
    return user


@router.patch("/me", response_model=UserOut)
async def update_profile(
    payload: UserUpdate,
    user: VerifiedUser,
    db: DB,
):
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.company is not None:
        user.company = payload.company
    await db.commit()
    return user


@router.post("/me/password", status_code=200)
async def change_password(
    payload: ChangePasswordRequest,
    user: VerifiedUser,
    db: DB,
):
    if not verify_password(payload.current_password, user.hashed_password):
        raise Unauthorized("Current password is incorrect.")

    user.hashed_password = hash_password(payload.new_password)
    # Cierra el resto de sesiones abiertas: cambiar la contraseña
    # debe expulsar a cualquiera que tuviera un token de esta cuenta.
    user.token_version += 1
    await db.commit()
    return {
        "message": (
            "Password updated. Other sessions have been signed out."
        )
    }


@router.delete("/me", status_code=204)
async def delete_account(user: VerifiedUser, db: DB):
    await db.delete(user)
    await db.commit()
