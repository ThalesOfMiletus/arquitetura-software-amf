# app/crud.py
from sqlalchemy.orm import Session
from . import models, schemas


def get_product(db: Session, product_id: int):
    """Busca um produto pelo ID."""
    return db.query(models.Product).filter(models.Product.id == product_id).first()


def create_product(db: Session, payload: schemas.ProductCreate):
    data = payload.model_dump()  # <-- aqui é o certo em Pydantic v2
    obj = models.Product(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_products(db: Session):
    return db.query(models.Product).all()

