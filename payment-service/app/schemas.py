from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class PaymentResponse(BaseModel):
    id: int
    order_id: str
    client_id: int
    client_name: str
    amount: float
    method: str
    card_last_digits: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentType(BaseModel):
    code: str
    label: str
