# seeder/seeder.py
import time
import requests

# URLs INTERNAS (dentro da rede do Docker)
USER_SERVICE_URL = "http://user-service:8000"
PRODUCT_SERVICE_URL = "http://product-service:8000"
ORDER_SERVICE_URL = "http://order-service:8000"
PAYMENT_SERVICE_URL = "http://payment-service:8000"
NOTIFICATION_SERVICE_URL = "http://notification-service:8000"


def wait_for_service(name: str, url: str, timeout: int = 60):
    print(f"[seeder] Aguardando {name} em {url} ...")
    start = time.time()
    while True:
        try:
            r = requests.get(url, timeout=3)
            if r.status_code < 500:
                print(f"[seeder] {name} está pronto!")
                return
        except Exception:
            pass

        if time.time() - start > timeout:
            raise TimeoutError(f"{name} não respondeu em {timeout} segundos")
        time.sleep(3)


def get_existing_user_by_email(email: str):
    # não temos endpoint de busca por email, mas podemos listar todos e filtrar
    try:
        r = requests.get(f"{USER_SERVICE_URL}/clients")
        if r.status_code == 200:
            for u in r.json():
                if u.get("email") == email:
                    return u
    except Exception:
        pass
    return None


def create_user():
    print("[seeder] Criando usuário ...")
    email = "thales.seed@example.com"
    payload = {
        "name": "Thales Criado pelo Seeder",
        "email": email,
        "password": "123456"
    }

    existing = get_existing_user_by_email(email)
    if existing:
        print("[seeder] Usuário já existe, reutilizando:", existing)
        return existing

    r = requests.post(f"{USER_SERVICE_URL}/clients", json=payload)
    if r.status_code >= 400:
        print("[seeder] Erro ao criar usuário, status:", r.status_code, r.text)
        # última tentativa: tenta listar e ver se foi criado mesmo assim
        existing = get_existing_user_by_email(email)
        if existing:
            print("[seeder] Usuário encontrado após erro, reutilizando:", existing)
            return existing
        r.raise_for_status()

    user = r.json()
    print("[seeder] Usuário criado:", user)
    return user


def get_products_by_name():
    try:
        r = requests.get(f"{PRODUCT_SERVICE_URL}/products")
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []


def create_products():
    print("[seeder] Criando produtos ...")
    products_payload = [
        {
            "name": "Notebook Dell G15",
            "description": "Notebook gamer com RTX 4060 e i7",
            "price": 4999.90,
            "stock": 5,
        },
        {
            "name": "Mouse Logitech G203",
            "description": "Mouse gamer com RGB",
            "price": 149.90,
            "stock": 20,
        },
        {
            "name": "Teclado Mecânico Redragon Kumara",
            "description": "Switch Outemu Blue ABNT2",
            "price": 249.90,
            "stock": 12,
        },
    ]

    existing = get_products_by_name()
    existing_by_name = {p["name"]: p for p in existing}

    created = []
    for p in products_payload:
        if p["name"] in existing_by_name:
            print("[seeder] Produto já existe, reutilizando:", existing_by_name[p["name"]])
            created.append(existing_by_name[p["name"]])
            continue

        r = requests.post(f"{PRODUCT_SERVICE_URL}/products", json=p)
        if r.status_code >= 400:
            print("[seeder] Erro ao criar produto", p["name"], "status:", r.status_code, r.text)
            # tenta recarregar lista e reutilizar se existir
            existing = get_products_by_name()
            existing_by_name = {prod["name"]: prod for prod in existing}
            if p["name"] in existing_by_name:
                created.append(existing_by_name[p["name"]])
                continue
            r.raise_for_status()

        prod = r.json()
        print("[seeder] Produto criado:", prod)
        created.append(prod)

    return created


def create_orders(user, products):
    print("[seeder] Criando pedidos ...")
    orders_created = []

    if len(products) < 2:
        print("[seeder] Produtos insuficientes para criar pedidos.")
        return orders_created

    order1 = {
        "client_id": user["id"],
        "client_name": user["name"],
        "items": [
            {
                "product_id": products[0]["id"],
                "quantity": 1,
                "price": float(products[0]["price"]),
            },
            {
                "product_id": products[1]["id"],
                "quantity": 2,
                "price": float(products[1]["price"]),
            },
        ],
        "payment": {
            "method": "credit_card",
            "card_last_digits": "1234"
        }
    }



    for o in [order1]:
        if o is None:
            continue
        r = requests.post(f"{ORDER_SERVICE_URL}/orders", json=o)
        if r.status_code >= 400:
            print("[seeder] Erro ao criar pedido, status:", r.status_code, r.text)
            continue
        order_resp = r.json()
        print("[seeder] Pedido criado:", order_resp)
        orders_created.append(order_resp)

    return orders_created


def list_payments():
    print("[seeder] Aguardando pagamentos serem processados (Kafka -> payment-service) ...")
    time.sleep(5)

    try:
        r = requests.get(f"{PAYMENT_SERVICE_URL}/payments")
        if r.status_code == 200:
            payments = r.json()
            print("[seeder] Pagamentos encontrados no payment-service:")
            for p in payments:
                print("   ", p)
        else:
            print("[seeder] Erro ao buscar pagamentos, status:", r.status_code, r.text)
    except Exception as e:
        print("[seeder] Erro ao buscar pagamentos:", e)


def main():
    # 1) Espera serviços subirem
    wait_for_service("user-service", f"{USER_SERVICE_URL}/clients")
    wait_for_service("product-service", f"{PRODUCT_SERVICE_URL}/products")
    wait_for_service("order-service", f"{ORDER_SERVICE_URL}/orders")
    wait_for_service("payment-service", f"{PAYMENT_SERVICE_URL}/payments")

    # 2) Cria usuário, produtos e pedidos (idempotente)
    user = create_user()
    products = create_products()
    orders = create_orders(user, products)

    print("\n[seeder] Resumo:")
    print("Usuário:", user)
    print("Produtos:", products)
    print("Pedidos:", orders)

    # 3) Consulta pagamentos gerados
    list_payments()
    print("Pagamentos listados com sucesso.")

    print("\n[seeder] Seed finalizado com sucesso.")


if __name__ == "__main__":
    main()
