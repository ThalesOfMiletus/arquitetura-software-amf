# app/main.py
from fastapi import FastAPI
import asyncio

from .rabbit_consumer import consume_notifications

app = FastAPI(
    title="notification-service",
    version="1.0.0",
    description="Microsserviço responsável por consumir notificações de pedidos pagos.",
)


@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_event_loop()
    # guarda a conexão pra poder fechar depois se quiser
    app.state.rabbit_connection = await consume_notifications()


@app.on_event("shutdown")
async def shutdown_event():
    conn = getattr(app.state, "rabbit_connection", None)
    if conn:
        await conn.close()


@app.get("/health")
def health():
    return {"status": "ok"}
