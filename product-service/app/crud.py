# app/crud.py
from sqlalchemy.orm import Session
from . import models, schemas


def get_product(db: Session, product_id: int) -> models.Product | None:
    return db.query(models.Product).filter(models.Product.id == product_id).first()


def list_products(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(models.Product)
        .order_by(models.Product.id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_product(db: Session, payload: schemas.ProductCreate) -> models.Product:
    data = payload.model_dump()
    obj = models.Product(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_product(db: Session, product_id: int, payload: schemas.ProductUpdate):
    obj = get_product(db, product_id)
    if not obj:
        return None

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return obj

    for k, v in data.items():
        setattr(obj, k, v)

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def patch_stock(db: Session, product_id: int, new_stock: int):
    obj = get_product(db, product_id)
    if not obj:
        return None
    obj.stock = int(new_stock)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def delete_product(db: Session, product_id: int) -> bool:
    obj = get_product(db, product_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True
