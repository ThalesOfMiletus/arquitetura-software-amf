import os
import json
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import httpx
import redis.asyncio as redis

# URLs internas (nome dos serviços no docker-compose)
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:8000")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8000")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://order-service:8000")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8000")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# TTLs em segundos
TTL_USER_BY_ID = 60 * 60 * 24           # 1 dia
TTL_PRODUCTS = 60 * 60 * 4              # 4 horas
TTL_ORDER_BY_ID = 60 * 60 * 24 * 30     # 30 dias
TTL_PAYMENTS_TYPES = None               # infinito

app = FastAPI(
    title="api-gateway",
    version="1.0.0",
    description="API Gateway com cache em Redis para os microserviços do e-commerce.",
)

redis_client: redis.Redis | None = None
http_client: httpx.AsyncClient | None = None


@app.on_event("startup")
async def startup_event():
    global redis_client, http_client
    redis_client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    http_client = httpx.AsyncClient()


@app.on_event("shutdown")
async def shutdown_event():
    global redis_client, http_client
    if http_client:
        await http_client.aclose()
    # redis_client é gerenciado internamente pelo driver, não precisa fechar aqui


async def get_or_set_cache(
    key: str,
    ttl: int | None,
    fetch_func: Callable[[], Awaitable[Any]],
):
    """
    Busca um JSON no cache Redis. Se não existir, chama fetch_func(),
    salva no Redis e devolve.
    """
    assert redis_client is not None

    cached = await redis_client.get(key)
    if cached is not None:
        data = json.loads(cached)
        return JSONResponse(content=data)

    # cache miss
    data = await fetch_func()

    dump = json.dumps(data)
    if ttl is not None:
        await redis_client.set(key, dump, ex=ttl)
    else:
        await redis_client.set(key, dump)

    return JSONResponse(content=data)


@app.get("/health")
async def health():
    return {"status": "ok"}


# -------------------------------------------------------------------
# USERS / CLIENTS
# -------------------------------------------------------------------

@app.post("/clients")
async def create_client(payload: dict):
    """
    Cria cliente no user-service.
    """
    assert http_client is not None
    try:
        resp = await http_client.post(
            f"{USER_SERVICE_URL}/clients",
            json=payload,
            timeout=10.0,
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao conectar no user-service em {USER_SERVICE_URL}: {e}",
        )

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return JSONResponse(content=resp.json(), status_code=resp.status_code)


@app.get("/clients")
async def list_clients():
    """
    Lista clientes no user-service.
    """
    assert http_client is not None
    try:
        resp = await http_client.get(
            f"{USER_SERVICE_URL}/clients",
            timeout=10.0,
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao conectar no user-service em {USER_SERVICE_URL}: {e}",
        )

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return JSONResponse(content=resp.json(), status_code=resp.status_code)


@app.get("/users/{user_id}")
async def get_user_by_id(user_id: int):
    """
    Rota cacheada: GET /users/{id}
    Proxy para user-service: GET /clients/{id}
    TTL: 1 dia
    """
    assert http_client is not None

    async def fetch():
        try:
            resp = await http_client.get(
                f"{USER_SERVICE_URL}/clients/{user_id}",
                timeout=10.0,
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Erro ao conectar no user-service em {USER_SERVICE_URL}: {e}",
            )

        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="User not found")
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()

    key = f"user:{user_id}"
    return await get_or_set_cache(key, TTL_USER_BY_ID, fetch)


# -------------------------------------------------------------------
# PRODUCTS
# -------------------------------------------------------------------

@app.get("/products")
async def get_products():
    """
    Rota cacheada: GET /products
    Proxy para product-service: GET /products
    TTL: 4h
    """
    assert http_client is not None

    async def fetch():
        try:
            resp = await http_client.get(
                f"{PRODUCT_SERVICE_URL}/products",
                timeout=10.0,
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Erro ao conectar no product-service em {PRODUCT_SERVICE_URL}: {e}",
            )

        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()

    key = "products:all"
    return await get_or_set_cache(key, TTL_PRODUCTS, fetch)


@app.get("/products/{product_id}")
async def get_product_by_id(product_id: int):
    """
    Busca produto por ID no product-service.
    (sem cache individual, só na lista)
    """
    assert http_client is not None
    try:
        resp = await http_client.get(
            f"{PRODUCT_SERVICE_URL}/products/{product_id}",
            timeout=10.0,
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao conectar no product-service em {PRODUCT_SERVICE_URL}: {e}",
        )

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Product not found")
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return JSONResponse(content=resp.json(), status_code=resp.status_code)


# -------------------------------------------------------------------
# ORDERS
# -------------------------------------------------------------------

@app.post("/orders")
async def create_order(payload: dict):
    """
    Cria pedido no order-service.
    """
    assert http_client is not None
    try:
        resp = await http_client.post(
            f"{ORDER_SERVICE_URL}/orders",
            json=payload,
            timeout=30.0,  # criar pedido envolve Mongo + Kafka, pode levar um pouco mais
        )
    except httpx.ReadTimeout:
        raise HTTPException(
            status_code=504,
            detail=f"order-service não respondeu a tempo em {ORDER_SERVICE_URL}/orders",
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao conectar no order-service em {ORDER_SERVICE_URL}: {e}",
        )

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return JSONResponse(content=resp.json(), status_code=resp.status_code)


@app.get("/orders")
async def list_orders():
    """
    Lista pedidos no order-service.
    """
    assert http_client is not None
    try:
        resp = await http_client.get(
            f"{ORDER_SERVICE_URL}/orders",
            timeout=10.0,
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao conectar no order-service em {ORDER_SERVICE_URL}: {e}",
        )

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return JSONResponse(content=resp.json(), status_code=resp.status_code)


@app.get("/orders/{order_id}")
async def get_order_by_id(order_id: str):
    """
    Rota cacheada: GET /orders/{id}
    Proxy para order-service: GET /orders/{id}
    TTL: 30 dias
    """
    assert http_client is not None

    async def fetch():
        try:
            resp = await http_client.get(
                f"{ORDER_SERVICE_URL}/orders/{order_id}",
                timeout=10.0,
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Erro ao conectar no order-service em {ORDER_SERVICE_URL}: {e}",
            )

        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Order not found")
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()

    key = f"order:{order_id}"
    return await get_or_set_cache(key, TTL_ORDER_BY_ID, fetch)


# -------------------------------------------------------------------
# PAYMENTS
# -------------------------------------------------------------------

@app.get("/payments")
async def list_payments():
    """
    Lista pagamentos no payment-service.
    """
    assert http_client is not None
    try:
        resp = await http_client.get(
            f"{PAYMENT_SERVICE_URL}/payments",
            timeout=10.0,
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao conectar no payment-service em {PAYMENT_SERVICE_URL}: {e}",
        )

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return JSONResponse(content=resp.json(), status_code=resp.status_code)


@app.get("/payments/{payment_id}")
async def get_payment_by_id(payment_id: int):
    """
    Busca pagamento por ID no payment-service.
    """
    assert http_client is not None
    try:
        resp = await http_client.get(
            f"{PAYMENT_SERVICE_URL}/payments/{payment_id}",
            timeout=10.0,
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao conectar no payment-service em {PAYMENT_SERVICE_URL}: {e}",
        )

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Payment not found")
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return JSONResponse(content=resp.json(), status_code=resp.status_code)


@app.get("/payments/types")
async def get_payment_types():
    """
    Rota cacheada: GET /payments/types
    TTL: infinito
    """
    assert http_client is not None

    async def fetch():
        try:
            resp = await http_client.get(
                f"{PAYMENT_SERVICE_URL}/payments/types",
                timeout=10.0,
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Erro ao conectar no payment-service em {PAYMENT_SERVICE_URL}: {e}",
            )

        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()

    key = "payments:types"
    return await get_or_set_cache(key, TTL_PAYMENTS_TYPES, fetch)
