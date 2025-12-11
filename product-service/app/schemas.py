# app/schemas.py
from pydantic import BaseModel, condecimal
from typing import Optional

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: condecimal(max_digits=10, decimal_places=2)
    stock: int

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    stock: Optional[int] = None

class ProductOut(ProductBase):
    id: int

    class Config:
        orm_mode = True
