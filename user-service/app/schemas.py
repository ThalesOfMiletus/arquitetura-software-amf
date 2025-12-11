# app/schemas.py
from pydantic import BaseModel  # <-- tiramos o EmailStr
from typing import Optional


class UserBase(BaseModel):
    name: str
    email: str  # <-- aqui agora é só string normal


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    id: int
    is_active: bool

    class Config:
        orm_mode = True
