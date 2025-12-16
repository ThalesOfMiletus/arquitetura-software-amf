from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: str
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    amount: Decimal
    status: str
    payment_type: str
    created_at: datetime


class PaymentTypeOut(BaseModel):
    code: str
    label: str


class PatchPaymentStatusIn(BaseModel):
    status: Literal["PAID", "FAILED", "PENDING"]


class HealthOut(BaseModel):
    status: str = Field(default="ok")
