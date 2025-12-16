# app/main.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .database import Base, engine, get_db
from . import models, schemas, crud
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

# cria tabelas ao subir o serviço (p/ trabalho tá ótimo)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="user-service",
    version="1.0.0",
    description="Microsserviço responsável pelo cadastro de usuários/clientes."
)


@app.post("/clients", response_model=schemas.UserOut, status_code=201)
def create_client(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        user = crud.create_user(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return user


@app.get("/clients", response_model=List[schemas.UserOut])
def list_clients(db: Session = Depends(get_db)):
    return crud.list_users(db)


@app.get("/clients/{client_id}", response_model=schemas.UserOut)
def get_client(
    client_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    user = crud.get_user(db, client_id)
    if not user:
        raise HTTPException(status_code=404, detail="Client not found")

    set_cache_headers(response, 86400)

    if set_etag_and_maybe_304(request, response, user):
        return Response(status_code=304)

    return user

