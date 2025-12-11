from sqlalchemy.orm import Session
from typing import List, Optional

from . import models, schemas


def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def list_users(db: Session) -> List[models.User]:
    return db.query(models.User).all()


def create_user(db: Session, payload: schemas.UserCreate) -> models.User:
    # verifica se e-mail já existe
    existing = get_user_by_email(db, payload.email)
    if existing:
        raise ValueError("Email already registered")

    data = payload.model_dump()  # inclui name, email, password
    user = models.User(**data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
