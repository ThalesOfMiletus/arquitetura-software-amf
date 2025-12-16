import asyncio
from contextlib import asynccontextmanager
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.kafka_consumer import consume_forever
from app.models import Payment
from app.schemas import HealthOut, PaymentOut, PaymentTypeOut
import hashlib
import json
from fastapi import Request, Response
from fastapi.encoders import jsonable_encoder

def set_cache_headers(response: Response, ttl_seconds: int, *, immutable: bool = False) -> None:
    cc = f"public, max-age={ttl_seconds}"
    # s-maxage ajuda cache compartilhado (proxy/gateway)
    cc += f", s-maxage={ttl_seconds}"
    if immutable:
        cc += ", immutable"
    response.headers["Cache-Control"] = cc

def set_etag_and_maybe_304(request: Request, response: Response, payload) -> bool:
    encoded = jsonable_encoder(payload)
    raw = json.dumps(
        encoded,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    etag = hashlib.sha1(raw).hexdigest()
    response.headers["ETag"] = etag

    inm = request.headers.get("if-none-match")
    if inm and inm.strip('"') == etag:
        response.status_code = 304
        return True
    return False



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


@app.get("/payments/{payment_id:int}", response_model=PaymentOut)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    return payment


@app.get("/payments/types", response_model=List[PaymentTypeOut])
def payment_types(request: Request, response: Response):
    payload = [
        PaymentTypeOut(code="CREDIT_CARD", label="Cartão de Crédito"),
        PaymentTypeOut(code="PIX", label="Pix"),
        PaymentTypeOut(code="BOLETO", label="Boleto"),
    ]

    # "TTL infinito" na prática: 1 ano + immutable
    set_cache_headers(response, 31536000, immutable=True)

    # ETag para 304
    payload_list = [p.model_dump() for p in payload]
    if set_etag_and_maybe_304(request, response, payload_list):
        return Response(status_code=304)

    return payload
