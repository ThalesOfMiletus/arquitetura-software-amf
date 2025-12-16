# Trabalho de Arquiteura de Software - Thales Cogo

Este guia direciona a execução do projeto via **Docker Compose**, o teste **end-to-end** com `fluxo.sh`, a validação das **rotas cacheadas** e uma lista de **cURLs** úteis para avaliação.

## 1) Subir o ambiente com Docker Compose

Na raiz do repositório (onde está o `docker-compose.yml`):

```bash
docker compose up -d --build
```

Verificar se os containers estão **Up**:

```bash
docker compose ps
```

Ver logs (se necessário):

```bash
docker compose logs -f
```

### Endpoints (padrão)

- user-service: `http://localhost:8001`
- product-service: `http://localhost:8002`
- order-service: `http://localhost:8003`
- payment-service: `http://localhost:8004`
- RabbitMQ UI: `http://localhost:15672` (login: `guest` / senha: `guest`)

> Dica: um check rápido:
```bash
curl -s http://localhost:8002/health
curl -s http://localhost:8003/health
curl -s http://localhost:8004/health
```

---

## 2) Rodar o fluxo end-to-end (E2E)

O script **cria usuário + 2 produtos + pedido + aguarda pagamento**.

No Git Bash:

```bash
chmod +x fluxo.sh
./fluxo.sh
```

Ao final, o script imprime:
- `client_id`
- `product ids`
- `order_id`
- `payment_id`

Se quiser acompanhar logs enquanto roda:

```bash
docker compose logs -f order-service
docker compose logs -f payment-service
```

---

## 3) Testar as rotas cacheadas

As rotas cacheadas retornam cabeçalhos HTTP como:
- `Cache-Control`
- `ETag`

E suportam revalidação via:
- `If-None-Match` → resposta **304 Not Modified** quando não houve mudança.

### 3.1) Ver headers (Cache-Control e ETag)

**User (TTL 1 dia)**  
> rota: `GET /clients/{id}`

```bash
curl -i http://localhost:8001/clients/1
```

**Products (TTL 4 horas)**  
> rota: `GET /products`

```bash
curl -i "http://localhost:8002/products?skip=0&limit=10"
```

**Payment types (“TTL infinito” na prática: 1 ano + immutable)**  
> rota: `GET /payments/types`

```bash
curl -i http://localhost:8004/payments/types
```

### 3.2) Testar 304 (ETag)

Exemplo com `/products`:

```bash
URL="http://localhost:8002/products?skip=0&limit=10"
ETAG=$(curl -sI "$URL" | tr -d '\r' | awk -F': ' '/^ETag:/ {print $2}')
echo "ETag=$ETAG"
curl -i "$URL" -H "If-None-Match: $ETAG"
```

Se estiver ok, o segundo `curl` deve retornar **HTTP 304**.

---

## 4) Lista de cURLs úteis (por serviço)

> Observação: substitua IDs conforme necessário.

---

### 4.1) user-service (`http://localhost:8001`)

**Criar cliente**
```bash
curl -s -X POST http://localhost:8001/clients \
  -H "Content-Type: application/json" \
  -d '{"name":"Thales","email":"thales@teste.com","password":"123456"}'
```

**Listar clientes**
```bash
curl -s http://localhost:8001/clients
```

**Buscar cliente por ID**
```bash
curl -s http://localhost:8001/clients/1
```

**Buscar cliente por ID com headers (cache)**
```bash
curl -i http://localhost:8001/clients/1
```

---

### 4.2) product-service (`http://localhost:8002`)

**Health**
```bash
curl -s http://localhost:8002/health
```

**Criar produto**
```bash
curl -s -X POST http://localhost:8002/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Cafe","price":20.00,"stock":50}'
```

**Listar produtos (paginação)**
```bash
curl -s "http://localhost:8002/products?skip=0&limit=10"
```

**Listar produtos com headers (cache)**
```bash
curl -i "http://localhost:8002/products?skip=0&limit=10"
```

**Buscar produto por ID**
```bash
curl -s http://localhost:8002/products/1
```

**Atualizar produto (patch parcial)**
```bash
curl -s -X PATCH http://localhost:8002/products/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"Cafe Premium","price":25.00}'
```

**Atualizar estoque**
```bash
curl -s -X PATCH http://localhost:8002/products/1/stock \
  -H "Content-Type: application/json" \
  -d '{"stock": 40}'
```

**Deletar produto**
```bash
curl -i -X DELETE http://localhost:8002/products/1
```

---

### 4.3) order-service (`http://localhost:8003`)

**Health**
```bash
curl -s http://localhost:8003/health
```

**Criar pedido (dispara evento no Kafka)**
```bash
curl -s -X POST http://localhost:8003/orders \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": 1,
    "client_name": "Thales",
    "items": [
      {"product_id": 1, "quantity": 2, "price": 20.00},
      {"product_id": 2, "quantity": 1, "price": 7.00}
    ],
    "payment": {"method":"CREDIT_CARD","card_last4":"4242"}
  }'
```

**Listar pedidos**
```bash
curl -s "http://localhost:8003/orders?skip=0&limit=20"
```

**Buscar pedido por ID**
```bash
curl -s http://localhost:8003/orders/SEU_ORDER_ID
```

**Buscar pedido por ID com headers (cache)**
```bash
curl -i http://localhost:8003/orders/SEU_ORDER_ID
```

---

### 4.4) payment-service (`http://localhost:8004`)

**Health**
```bash
curl -s http://localhost:8004/health
```

**Listar pagamentos**
```bash
curl -s "http://localhost:8004/payments?skip=0&limit=50"
```

**Buscar pagamento por ID**
```bash
curl -s http://localhost:8004/payments/1
```

**Tipos de pagamento**
```bash
curl -s http://localhost:8004/payments/types
```

**Tipos de pagamento com headers (cache)**
```bash
curl -i http://localhost:8004/payments/types
```

---

## 5) Encerrar o ambiente

```bash
docker compose down
```

Para apagar volumes (banco/filas etc.):

```bash
docker compose down -v
```
