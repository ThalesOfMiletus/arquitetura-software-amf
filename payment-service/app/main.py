import asyncio
from contextlib import asynccontextmanager
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.kafka_consumer import consume_forever
from app.models import Payment
from app.schemas import HealthOut, PaymentOut, PaymentTypeOut


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    Base.metadata.create_all(bind=engine)

    task = asyncio.create_task(consume_forever())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="payment-service", version="1.0.0", lifespan=lifespan)


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut(status="ok")


@app.get("/payments", response_model=List[PaymentOut])
def list_payments(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    return db.query(Payment).order_by(Payment.id.desc()).offset(skip).limit(limit).all()


@app.get("/payments/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    return payment


@app.get("/payments/types", response_model=List[PaymentTypeOut])
def payment_types():
    # Mantém compatível com teu endpoint atual
    return [
        PaymentTypeOut(code="CREDIT_CARD", label="Cartão de Crédito"),
        PaymentTypeOut(code="PIX", label="Pix"),
        PaymentTypeOut(code="BOLETO", label="Boleto"),
    ]
