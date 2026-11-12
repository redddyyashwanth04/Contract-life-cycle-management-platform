from fastapi import APIRouter, Depends, HTTPException

from ..models import LoginRequest
from ..security import authenticate, create_session, drop_session, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest):
    user = authenticate(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_session(user)
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "organization": user["organization"],
        },
    }


@router.post("/logout")
def logout(user: dict = Depends(get_current_user), authorization: str = None):
    if authorization and authorization.startswith("Bearer "):
        drop_session(authorization.removeprefix("Bearer ").strip())
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "organization": user["organization"],
    }
