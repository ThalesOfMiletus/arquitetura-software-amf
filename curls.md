````md
# CURLs do E-commerce (via Kong)

> Todas as requisições vão para o **Kong** em:  
> `http://localhost:8000`  

> Atenção ao rate limit: **10 requisições por minuto**.

---

## 0. Healthcheck do API Gateway

```bash
curl -i http://localhost:8000/health
````

---

## 1. USERS / CLIENTS

### 1.1 Criar cliente

```bash
curl -i -X POST http://localhost:8000/clients \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jack",
    "email": "jack.email@example.com",
    "password": "123456"
  }'
```

### 1.2 Listar todos os clientes

```bash
curl -i http://localhost:8000/clients
```

### 1.3 Buscar cliente por ID (rota cacheada, TTL 1 dia)

```bash
curl -i http://localhost:8000/users/1
# Substitua 1 pelo ID real do cliente
```

---

## 2. PRODUCTS

> Obs.: Os produtos iniciais são criados pelo **seeder**, então em produção você normalmente só consulta.

### 2.1 Listar todos os produtos (rota cacheada, TTL 4h)

```bash
curl -i http://localhost:8000/products
```

### 2.2 Buscar produto por ID

```bash
curl -i http://localhost:8000/products/1
# Substitua 1 pelo ID real do produto
```

---

## 3. ORDERS

### 3.1 Criar pedido (um cliente, um ou mais itens)

```bash
curl -i -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": 1,
    "client_name": "Jack",
    "items": [
      {
        "product_id": 1,
        "quantity": 1,
        "price": 100.0
      },
      {
        "product_id": 2,
        "quantity": 2,
        "price": 149.90
      }
    ],
    "payment": {
      "method": "credit_card",
      "card_last_digits": "1234"
    }
  }'
# client_id deve existir em /clients
# product_id deve existir em /products
```

### 3.2 Listar todos os pedidos

```bash
curl -i http://localhost:8000/orders
```

### 3.3 Buscar pedido por ID (rota cacheada, TTL 30 dias)

```bash
curl -i http://localhost:8000/orders/<ORDER_ID>
# Substitua <ORDER_ID> pelo id (UUID / ObjectId em string) retornado na criação do pedido
```

---

## 4. PAYMENTS

> Os pagamentos são criados automaticamente pelo **payment-service**
> ao consumir as mensagens do Kafka geradas pelo **order-service**.

### 4.1 Listar todos os pagamentos

```bash
curl -i http://localhost:8000/payments
```

### 4.2 Buscar pagamento por ID

```bash
curl -i http://localhost:8000/payments/1
# Substitua 1 pelo ID real do pagamento
```

### 4.3 Listar tipos de pagamento (rota cacheada, TTL infinito)

```bash
curl -i http://localhost:8000/payments/types
```

---

## 5. Health do API Gateway (extra)

> Útil para checar rapidamente se o gateway continua de pé durante os testes.

```bash
curl -i http://localhost:8000/health
```

---

## 6. Fluxo sugerido para demonstração (manual)

1. **Healthcheck**

   ```bash
   curl -i http://localhost:8000/health
   ```

2. **Criar cliente** e anotar o `id`

   ```bash
   curl -i -X POST http://localhost:8000/clients \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Jack",
       "email": "jack.email@example.com",
       "password": "123456"
     }'
   ```

3. **Listar produtos** e escolher alguns IDs válidos

   ```bash
   curl -i http://localhost:8000/products
   ```

4. **Criar pedido** usando `client_id` e `product_id` reais

   ```bash
   curl -i -X POST http://localhost:8000/orders \
     -H "Content-Type: application/json" \
     -d '{
       "client_id": 1,
       "client_name": "Jack",
       "items": [
         { "product_id": 1, "quantity": 1, "price": 100.0 }
       ],
       "payment": {
         "method": "credit_card",
         "card_last_digits": "1234"
       }
     }'
   ```

5. **Listar pedidos** e pegar o `id` para testar cache

   ```bash
   curl -i http://localhost:8000/orders
   ```

6. **Buscar pedido por ID (rota cacheada)**

   ```bash
   curl -i http://localhost:8000/orders/<ORDER_ID>
   ```

7. **Listar pagamentos**

   ```bash
   curl -i http://localhost:8000/payments
   ```

8. **Buscar pagamento por ID**

   ```bash
   curl -i http://localhost:8000/payments/<PAYMENT_ID>
   ```

9. **Ver tipos de pagamento (rota cacheada)**

   ```bash
   curl -i http://localhost:8000/payments/types
   ```

```

Se quiser depois eu monto uma versão `.sh` de novo baseada nesse `.md`, mas agora com comentários mais “didáticos” pro professor.
::contentReference[oaicite:0]{index=0}
```
