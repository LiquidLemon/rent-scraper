from fastapi import Request, Depends
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from models import User
from database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user


class NotAuthenticatedError(Exception):
    pass


def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise NotAuthenticatedError()

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        request.session.clear()
        raise NotAuthenticatedError()
    return user