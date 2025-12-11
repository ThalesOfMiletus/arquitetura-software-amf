from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime

from .database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, index=True)          # ID do pedido (string do ObjectId)
    client_id = Column(Integer, index=True)
    client_name = Column(String)
    amount = Column(Float)
    method = Column(String)
    card_last_digits = Column(String, nullable=True)
    status = Column(String, default="PAID")
    created_at = Column(DateTime, default=datetime.utcnow)
