from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import asyncio
import logging

from .database import SessionLocal, Base, engine
from .models import Payment
from .schemas import PaymentResponse, PaymentType
from .kafka_consumer import consume_payments

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="payment-service",
    version="1.0.0",
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
async def startup_event():
    # cria tabelas se não existirem
    Base.metadata.create_all(bind=engine)

    # sobe o consumer Kafka em background
    loop = asyncio.get_running_loop()
    app.state.consumer_task = loop.create_task(consume_payments())
    logger.info("[payment-service] startup completo, consumer Kafka iniciado")


@app.on_event("shutdown")
async def shutdown_event():
    task = getattr(app.state, "consumer_task", None)
    if task:
        task.cancel()
        logger.info("[payment-service] consumer_task cancelado")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/payments", response_model=List[PaymentResponse])
def list_payments(db: Session = Depends(get_db)):
    payments = db.query(Payment).order_by(Payment.id.desc()).all()
    return payments


@app.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@app.get("/payments/types", response_model=List[PaymentType])
def get_payment_types():
    """
    Lista fixa de tipos de pagamento. Essa rota é cacheada pelo API Gateway (TTL infinito).
    """
    return [
        PaymentType(code="credit_card", label="Cartão de Crédito"),
        PaymentType(code="pix", label="PIX"),
        PaymentType(code="boleto", label="Boleto Bancário"),
    ]
