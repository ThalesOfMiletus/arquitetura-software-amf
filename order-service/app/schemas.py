from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class OrderItem(BaseModel):
    product_id: int
    quantity: int
    price: float  # sempre float, nada de Decimal pra não quebrar no Mongo


class PaymentInfo(BaseModel):
    method: str
    card_last_digits: Optional[str] = None


class OrderCreate(BaseModel):
    client_id: int
    client_name: str
    items: List[OrderItem]
    payment: PaymentInfo


class OrderResponse(BaseModel):
    id: str = Field(..., description="ID do pedido (string do ObjectId)")
    client_id: int
    client_name: str
    items: List[OrderItem]
    total_amount: float
    status: str
    created_at: datetime
    payment: PaymentInfo

    class Config:
        from_attributes = True
        populate_by_name = True
