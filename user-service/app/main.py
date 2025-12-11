# app/main.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .database import Base, engine, get_db
from . import models, schemas, crud

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
def get_client(client_id: int, db: Session = Depends(get_db)):
    user = crud.get_user(db, client_id)
    if not user:
        raise HTTPException(status_code=404, detail="Client not found")
    return user
