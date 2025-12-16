import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Integer, Numeric, String, UniqueConstraint

from app.database import Base


class PaymentStatus(str, enum.Enum):
    PAID = "PAID"
    FAILED = "FAILED"
    PENDING = "PENDING"


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_payments_order_id"),
    )

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(String, nullable=False, index=True)
    client_id = Column(Integer, nullable=True, index=True)
    client_name = Column(String, nullable=True)

    # Money: prefer Numeric instead of Float
    amount = Column(Numeric(10, 2), nullable=False)

    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PAID)
    payment_type = Column(String, nullable=False, default="CREDIT_CARD")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
