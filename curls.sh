#!/usr/bin/env bash
# Arquivo: curls.sh
# Uso:
#   chmod +x curls.sh
#   ./curls.sh
#
# Obs.: Todas as chamadas vão para o KONG em http://localhost:8000

BASE_URL="http://localhost:8000"

ORDER_ID=""
PAYMENT_ID=""

echo "=== 0. HEALTHCHECK API GATEWAY (via Kong) ==="
curl -i "$BASE_URL/health"
echo -e "\n\n"
sleep 3

########################################
# 1. USERS / CLIENTS
########################################

echo "=== 1.1 Criar cliente ==="
read -p "Digite o NOME do cliente: " CLIENT_NAME
read -p "Digite o EMAIL do cliente: " CLIENT_EMAIL

curl -i -X POST "$BASE_URL/clients" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$CLIENT_NAME\",
    \"email\": \"$CLIENT_EMAIL\",
    \"password\": \"123456\"
  }"
echo -e "\n\n"

echo "Veja o ID do cliente na resposta acima ou em /clients."
read -p "Digite o ID do cliente para usar nas próximas chamadas: " CLIENT_ID

sleep 3

echo "=== 1.2 Listar todos os clientes ==="
curl -i "$BASE_URL/clients"
echo -e "\n\n"

echo "=== 1.3 Buscar cliente por ID (rota cacheada, TTL 1 dia) ==="
curl -i "$BASE_URL/users/$CLIENT_ID"
echo -e "\n\n"
sleep 3

########################################
# 2. PRODUCTS (somente leitura - criados pelo seeder)
########################################

echo "=== 2.1 Listar produtos existentes (seed + extras) ==="
curl -i "$BASE_URL/products"
echo -e "\n\n"

read -p "Digite o ID do produto que será comprado (um único produto): " PRODUCT_ID

echo "=== 2.2 Buscar produto selecionado por ID ==="
curl -i "$BASE_URL/products/$PRODUCT_ID"
echo -e "\n\n"
sleep 3

########################################
# 3. ORDERS (um produto, qty=1, price=100.0) 
########################################

echo "=== 3.1 Criar pedido para o cliente $CLIENT_ID com o produto $PRODUCT_ID ==="
echo "Será usado quantity = 1 e price = 100.0 apenas para demonstração."

curl -i -X POST "$BASE_URL/orders" \
  -H "Content-Type: application/json" \
  -d "{
    \"client_id\": $CLIENT_ID,
    \"client_name\": \"$CLIENT_NAME\",
    \"items\": [
      {
        \"product_id\": $PRODUCT_ID,
        \"quantity\": 1,
        \"price\": 100.0
      }
    ],
    \"payment\": {
      \"method\": \"credit_card\",
      \"card_last_digits\": \"1234\"
    }
  }"
echo -e "\n\n"

echo "Pegue o 'id' (UUID) do pedido na resposta acima."
read -p "Cole aqui o ORDER_ID para usar depois (ex.: a4cc4097-...): " ORDER_ID

sleep 3

echo "=== 3.2 Listar todos os pedidos ==="
curl -i "$BASE_URL/orders"
echo -e "\n\n"

echo "=== 3.3 Buscar pedido por ID (rota cacheada, TTL 30 dias) ==="
echo "Usando ORDER_ID=$ORDER_ID"
curl -i "$BASE_URL/orders/$ORDER_ID"
echo -e "\n\n"
sleep 3

########################################
# 4. PAYMENTS
########################################

echo "=== 4.1 Listar todos os pagamentos ==="
curl -i "$BASE_URL/payments"
echo -e "\n\n"

read -p "Digite o ID de um pagamento da lista acima para testar (ex.: 1): " PAYMENT_ID

echo "=== 4.2 Buscar pagamento por ID ==="
echo "Usando PAYMENT_ID=$PAYMENT_ID"
curl -i "$BASE_URL/payments/$PAYMENT_ID"
echo -e "\n\n"
sleep 3

########################################
# 5. ROTAS DE SAÚDE
########################################

echo "=== 5.1 Health do API Gateway (via Kong) ==="
curl -i "$BASE_URL/health"
echo -e "\n\n"
