# app/main.py
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from .database import Base, engine, get_db
from . import crud, schemas
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


# cria tabelas automaticamente (pra trabalho acadêmico serve bem;
# em produção usamos Alembic)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="product-service",
    version="1.0.1",
    description="Microsserviço responsável pelo cadastro e gestão de produtos.",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/products", response_model=schemas.ProductOut, status_code=201)
def create_product(payload: schemas.ProductCreate, db: Session = Depends(get_db)):
    return crud.create_product(db, payload)


@app.get("/products", response_model=List[schemas.ProductOut])
def list_products(
    request: Request,
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    products = crud.list_products(db, skip=skip, limit=limit)

    set_cache_headers(response, 14400)

    if set_etag_and_maybe_304(request, response, products):
        return Response(status_code=304)

    return products



@app.get("/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.patch("/products/{product_id}", response_model=schemas.ProductOut)
def update_product(
    product_id: int, payload: schemas.ProductUpdate, db: Session = Depends(get_db)
):
    product = crud.update_product(db, product_id, payload)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.patch("/products/{product_id}/stock", response_model=schemas.ProductOut)
def patch_stock(
    product_id: int, payload: schemas.StockUpdate, db: Session = Depends(get_db)
):
    product = crud.patch_stock(db, product_id, payload.stock)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    ok = crud.delete_product(db, product_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Product not found")
    return
