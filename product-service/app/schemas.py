# app/schemas.py
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, condecimal, conint


Price = condecimal(gt=0, max_digits=10, decimal_places=2)
Stock = conint(ge=0)


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=500)
    price: Price
    stock: Stock = 0


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=500)
    price: Optional[Price] = None
    stock: Optional[Stock] = None


class StockUpdate(BaseModel):
    stock: Stock


class ProductOut(ProductBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
