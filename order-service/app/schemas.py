from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, conint, condecimal

class OrderItemIn(BaseModel):
    product_id: int
    quantity: conint(gt=0)  # > 0
    price: condecimal(gt=0, max_digits=10, decimal_places=2)

class OrderCreate(BaseModel):
    client_id: int
    client_name: Optional[str] = None
    items: List[OrderItemIn] = Field(min_length=1)

class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: int
    client_name: Optional[str] = None
    items: List[dict]
    total_amount: Decimal
    status: str
    created_at: datetime

class HealthOut(BaseModel):
    status: str
