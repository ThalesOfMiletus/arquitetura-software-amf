#!/usr/bin/env bash
set -euo pipefail

# =========================
# Config (ajuste se quiser)
# =========================
USER_URL="${USER_URL:-http://localhost:8001}"
PRODUCT_URL="${PRODUCT_URL:-http://localhost:8002}"
ORDER_URL="${ORDER_URL:-http://localhost:8003}"
PAYMENT_URL="${PAYMENT_URL:-http://localhost:8004}"

NAME="${NAME:-Thales}"
PASSWORD="${PASSWORD:-123456}"

# =========================
# Helpers
# =========================
echo_step() { echo; echo "==> $*"; }

json_get() {
  # uso: echo "$JSON" | json_get id
  local key="$1"
  python -c "import sys,json; data=json.load(sys.stdin); print(data.get('${key}',''))"
}

curl_body_status() {
  # uso: curl_body_status <outvar_body> <outvar_status> <curl args...>
  local __bodyvar="$1"; shift
  local __statusvar="$1"; shift
  local tmp
  tmp="$(mktemp)"
  local status
  status="$(curl -sS -o "$tmp" -w "%{http_code}" "$@" || true)"
  local body
  body="$(cat "$tmp" 2>/dev/null || true)"
  rm -f "$tmp" || true
  printf -v "$__bodyvar" '%s' "$body"
  printf -v "$__statusvar" '%s' "$status"
}

ensure_2xx_or_die() {
  local service="$1"
  local body="$2"
  local status="$3"

  case "$status" in
    2* ) return 0 ;;
    * )
      echo
      echo "❌ ${service} retornou HTTP ${status}"
      echo "Resposta:"
      echo "$body"
      echo
      echo "Logs sugeridos:"
      echo "  docker compose logs --tail=200 ${service}"
      exit 1
      ;;
  esac
}

TS="$(python -c "import time; print(int(time.time()))")"
EMAIL="thales+e2e-${TS}@teste.com"

# =========================
# 1) User
# =========================
echo_step "1) Criando usuário (${EMAIL})"
USER_PAYLOAD="$(cat <<JSON
{"name":"${NAME}","email":"${EMAIL}","password":"${PASSWORD}"}
JSON
)"
USER_BODY=""; USER_STATUS=""
curl_body_status USER_BODY USER_STATUS -X POST "${USER_URL}/clients" -H "Content-Type: application/json" -d "${USER_PAYLOAD}"
echo "${USER_BODY}"
ensure_2xx_or_die "user-service" "${USER_BODY}" "${USER_STATUS}"

CLIENT_ID="$(printf '%s' "${USER_BODY}" | json_get id || true)"
if [[ -z "${CLIENT_ID}" ]]; then
  echo "Falhou ao obter client_id."
  exit 1
fi
echo "client_id=${CLIENT_ID}"

# =========================
# 2) Products
# =========================
echo_step "2) Criando produtos"
P1_PAYLOAD='{"name":"Cafe","price":20,"stock":50}'
P1_BODY=""; P1_STATUS=""
curl_body_status P1_BODY P1_STATUS -X POST "${PRODUCT_URL}/products" -H "Content-Type: application/json" -d "${P1_PAYLOAD}"
echo "${P1_BODY}"
ensure_2xx_or_die "product-service" "${P1_BODY}" "${P1_STATUS}"
P1_ID="$(printf '%s' "${P1_BODY}" | json_get id || true)"
P1_PRICE="$(printf '%s' "${P1_BODY}" | json_get price || true)"

P2_PAYLOAD='{"name":"Pao","price":7,"stock":100}'
P2_BODY=""; P2_STATUS=""
curl_body_status P2_BODY P2_STATUS -X POST "${PRODUCT_URL}/products" -H "Content-Type: application/json" -d "${P2_PAYLOAD}"
echo "${P2_BODY}"
ensure_2xx_or_die "product-service" "${P2_BODY}" "${P2_STATUS}"
P2_ID="$(printf '%s' "${P2_BODY}" | json_get id || true)"
P2_PRICE="$(printf '%s' "${P2_BODY}" | json_get price || true)"

if [[ -z "${P1_ID}" || -z "${P2_ID}" ]]; then
  echo "Falhou ao obter product ids."
  exit 1
fi
echo "product_1_id=${P1_ID} price=${P1_PRICE}"
echo "product_2_id=${P2_ID} price=${P2_PRICE}"

# =========================
# 3) Order
# =========================
echo_step "3) Criando pedido (order-service) — dispara evento pro Kafka"
ORDER_PAYLOAD="$(cat <<JSON
{
  "client_id": ${CLIENT_ID},
  "client_name": "${NAME}",
  "items": [
    {"product_id": ${P1_ID}, "quantity": 2, "price": ${P1_PRICE}},
    {"product_id": ${P2_ID}, "quantity": 1, "price": ${P2_PRICE}}
  ],
  "payment": {"method": "CREDIT_CARD", "card_last4": "4242"}
}
JSON
)"
ORDER_BODY=""; ORDER_STATUS=""
curl_body_status ORDER_BODY ORDER_STATUS -X POST "${ORDER_URL}/orders" -H "Content-Type: application/json" -d "${ORDER_PAYLOAD}"
echo "${ORDER_BODY}"
ensure_2xx_or_die "order-service" "${ORDER_BODY}" "${ORDER_STATUS}"

ORDER_ID="$(printf '%s' "${ORDER_BODY}" | json_get id || true)"
if [[ -z "${ORDER_ID}" ]]; then
  echo "Falhou ao obter order_id."
  exit 1
fi
echo "order_id=${ORDER_ID}"

# =========================
# 4) Order fetch
# =========================
echo_step "4) Consultando o pedido recém-criado"
curl -sS "${ORDER_URL}/orders/${ORDER_ID}" || true
echo

# =========================
# 5) Payment poll
# =========================
echo_step "5) Aguardando o payment-service consumir do Kafka e criar o pagamento"
PAYMENT_ID=""
for i in $(seq 1 25); do
  PAY_BODY=""; PAY_STATUS=""
  curl_body_status PAY_BODY PAY_STATUS "${PAYMENT_URL}/payments?skip=0&limit=50"
  if [[ "$PAY_STATUS" != 2* ]]; then
    echo "payment-service ainda não OK (HTTP ${PAY_STATUS})..."
    sleep 1
    continue
  fi

  PAYMENT_ID="$(printf '%s' "${PAY_BODY}" | python -c "import sys,json; order_id='${ORDER_ID}';
try:
    data=json.load(sys.stdin)
except Exception:
    print(''); raise SystemExit
items = data.get('items') if isinstance(data, dict) else data
if not isinstance(items, list):
    print(''); raise SystemExit
for p in items:
    if str(p.get('order_id'))==str(order_id):
        print(p.get('id','')); break
else:
    print('')")"

  if [[ -n "${PAYMENT_ID}" ]]; then
    break
  fi
  echo "Ainda não apareceu pagamento... tentativa ${i}/25"
  sleep 1
done

if [[ -z "${PAYMENT_ID}" ]]; then
  echo
  echo "Não encontrei pagamento para order_id=${ORDER_ID} após 25s."
  echo "Logs sugeridos:"
  echo "  docker compose logs --tail=200 order-service"
  echo "  docker compose logs --tail=200 payment-service"
  exit 1
fi

echo "payment_id=${PAYMENT_ID}"

# =========================
# 6) Payment fetch
# =========================
echo_step "6) Buscando pagamento por ID"
PAY_ONE_BODY=""; PAY_ONE_STATUS=""
curl_body_status PAY_ONE_BODY PAY_ONE_STATUS "${PAYMENT_URL}/payments/${PAYMENT_ID}"
echo "${PAY_ONE_BODY}"
ensure_2xx_or_die "payment-service" "${PAY_ONE_BODY}" "${PAY_ONE_STATUS}"

echo
echo "✅ Fluxo E2E concluído:"
echo "   client_id=${CLIENT_ID}"
echo "   products=${P1_ID}, ${P2_ID}"
echo "   order_id=${ORDER_ID}"
echo "   payment_id=${PAYMENT_ID}"
