# backend/src/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import LoginIn, RegisterIn, TokenOut, UserOut
from ..security import create_access_token, hash_password, verify_password
from ..services.seed import seed_user_tasks

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(func.lower(User.username) == body.username.lower())):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username already taken")
    if db.scalar(select(User).where(func.lower(User.email) == body.email.lower())):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")
    user = User(username=body.username, email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    seed_user_tasks(db, user.id)
    return TokenOut(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.username) == body.username.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
