#!/usr/bin/env python3

# ++==================================++
# || CC6240 - POLYGLOT PERSISTENCE    ||
# || LUÍS MIGUEL DE ALMEIDA GUERTAS   ||
# || RA 24.123.040-8                  ||
# || LUÍS FERNANDO DE SOUZA GONÇALVES ||
# || RA 24.123.052-3                  ||
# ++==================================++

import json
import sys
from typing import Any, Callable
from urllib import error, request

BASE_URL = "http://127.0.0.1:8000/api/v1"
HTTP_TIMEOUT_SECONDS = 30

# ++============================++
# || FUNÇÕES DE REQUISIÇÃO HTTP ||
# ++============================++

def api(method: str, path: str, body: dict | None = None) -> tuple[int, Any]:
    url = BASE_URL + path
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body, default=str).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url, data=data, method=method, headers=headers)
    try:
        with request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else None)
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw
    except error.URLError as exc:
        return 0, f"connection error: {exc.reason}"


# ++============================================++
# || FUNÇÕES DE FORMATAÇÃO DA SAÍDA DO TERMINAL ||
# ++============================================++

LINE = "=" * 64
THIN = "-" * 64


def header(title: str) -> None:
    print()
    print(LINE)
    print(f" {title}")
    print(LINE)


def section(title: str) -> None:
    print()
    print(f"-- {title} --")


def info(msg: str) -> None:
    print(f"   {msg}")


def success(msg: str) -> None:
    print(f"[ok] {msg}")


def show_error(status: int, payload: Any) -> None:
    if status == 0:
        print(f"[error] {payload}")
        return
    if isinstance(payload, dict):
        detail = payload.get("detail", payload)
    else:
        detail = payload
    print(f"[HTTP {status}] {detail}")


def show_customer(c: dict) -> None:
    print(f"   customer_id  : {c['customer_id']}")
    print(f"   full_name    : {c['full_name']}")
    print(f"   email        : {c['email']}")
    print(f"   created_at   : {c['created_at']}")


def show_product(p: dict) -> None:
    print(f"   nosql_product_id  : {p['nosql_product_id']}")
    print(f"   product_name      : {p['product_name']}")
    print(f"   current_price     : ${p['current_price']}")
    print(f"   available_stock   : {p['available_stock']}")
    print(f"   technical_details : {json.dumps(p.get('technical_details', {}))}")


def show_cart(c: dict) -> None:
    print(f"   customer_id : {c['customer_id']}")
    items = c.get("items", [])
    if not items:
        print("   items       : (empty)")
        return
    print(f"   items ({len(items)}):")
    for it in items:
        print(f"     - product={it['nosql_product_id']}  qty={it['quantity']}")


def show_order(o: dict) -> None:
    print(f"   order_id       : {o['order_id']}")
    print(f"   customer_id    : {o['customer_id']}")
    print(f"   total_amount   : ${o['total_amount']}")
    print(f"   payment_status : {o['payment_status']}")
    print(f"   created_at     : {o['created_at']}")
    items = o.get("items", [])
    print(f"   line items ({len(items)}):")
    for it in items:
        print(
            f"     - item #{it['item_id']}  product={it['nosql_product_id']}  "
            f"qty={it['quantity']}  locked_price=${it['locked_price']}"
        )


# ++================================++
# || VALIDAÇÃO DE INPUTS DO USUÁRIO ||
# ++================================++

def ask(label: str) -> str:
    return input(f"   {label}: ").strip()


def ask_int(label: str) -> int | None:
    raw = ask(label)
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        info("(invalid integer)")
        return None


def ask_json(label: str) -> dict | None:
    raw = ask(f"{label} (JSON object, blank for {{}})")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            info("(must be a JSON object)")
            return None
        return parsed
    except json.JSONDecodeError as exc:
        info(f"(invalid JSON: {exc})")
        return None


def pause() -> None:
    try:
        input("\n   (press enter to continue) ")
    except EOFError:
        pass


# ++==========================++
# || FUNÇÃO DE MENU PRINCIPAL ||
# ++==========================++

def run_menu(title: str, options: dict[str, tuple[str, Callable[[], None]]]) -> None:
    while True:
        header(title)
        for key, (label, _) in options.items():
            print(f"   [{key}] {label}")
        print("   [b] Back")
        choice = input("\n > ").strip().lower()
        if choice == "b":
            return
        opt = options.get(choice)
        if opt is None:
            info("(invalid choice)")
            continue
        try:
            opt[1]()
        except KeyboardInterrupt:
            print("\n   (action cancelled)")
        except Exception as exc:
            print(f"   [crash] {type(exc).__name__}: {exc}")
        pause()


# ++=================================++
# || CRUD DE CUSTOMERS (POSTgreSQL) ||
# ++=================================++

def customer_create() -> None:
    section("Create customer (POST /customers)")
    full_name = ask("full_name")
    email = ask("email")
    if not full_name or not email:
        info("(both fields required)")
        return
    status, payload = api("POST", "/customers", {"full_name": full_name, "email": email})
    if status == 201:
        success(f"created customer #{payload['customer_id']}")
        show_customer(payload)
    else:
        show_error(status, payload)


def customer_list() -> None:
    section("List customers (GET /customers)")
    status, payload = api("GET", "/customers?limit=200")
    if status != 200:
        show_error(status, payload)
        return
    if not payload:
        info("(no customers yet)")
        return
    info(f"{len(payload)} customer(s):")
    for c in payload:
        print(THIN)
        show_customer(c)


def customer_read() -> None:
    section("Read customer (GET /customers/{id})")
    cid = ask_int("customer_id")
    if cid is None:
        return
    status, payload = api("GET", f"/customers/{cid}")
    if status == 200:
        show_customer(payload)
    else:
        show_error(status, payload)


def customer_update() -> None:
    section("Update customer (PATCH /customers/{id})")
    cid = ask_int("customer_id")
    if cid is None:
        return
    full_name = ask("new full_name (blank to skip)")
    email = ask("new email (blank to skip)")
    body: dict = {}
    if full_name:
        body["full_name"] = full_name
    if email:
        body["email"] = email
    if not body:
        info("(nothing to update)")
        return
    status, payload = api("PATCH", f"/customers/{cid}", body)
    if status == 200:
        success("updated")
        show_customer(payload)
    else:
        show_error(status, payload)


def customer_delete() -> None:
    section("Delete customer (DELETE /customers/{id})")
    cid = ask_int("customer_id")
    if cid is None:
        return
    status, payload = api("DELETE", f"/customers/{cid}")
    if status == 204:
        success(f"customer #{cid} deleted")
    else:
        show_error(status, payload)


def customers_menu() -> None:
    run_menu(
        "Manage Customers  [PostgreSQL]",
        {
            "1": ("Create", customer_create),
            "2": ("List all", customer_list),
            "3": ("Read by ID", customer_read),
            "4": ("Update", customer_update),
            "5": ("Delete", customer_delete),
        },
    )


# ++============================++
# || CRUD DE PRODUTOS (MongoDB) ||
# ++============================++

def product_create() -> None:
    section("Create product (POST /products)")
    name = ask("product_name")
    price = ask("current_price (e.g. 19.99)")
    stock = ask_int("available_stock")
    if not name or not price or stock is None:
        info("(name, price, and stock are required)")
        return
    details = ask_json("technical_details")
    if details is None:
        return
    body = {
        "product_name": name,
        "current_price": price,
        "available_stock": stock,
        "technical_details": details,
    }
    status, payload = api("POST", "/products", body)
    if status == 201:
        success(f"created product {payload['nosql_product_id']}")
        show_product(payload)
    else:
        show_error(status, payload)


def product_list() -> None:
    section("List products (GET /products)")
    status, payload = api("GET", "/products?limit=200")
    if status != 200:
        show_error(status, payload)
        return
    if not payload:
        info("(no products yet)")
        return
    info(f"{len(payload)} product(s):")
    for p in payload:
        print(THIN)
        show_product(p)


def product_read() -> None:
    section("Read product (GET /products/{id})")
    pid = ask("nosql_product_id")
    if not pid:
        return
    status, payload = api("GET", f"/products/{pid}")
    if status == 200:
        show_product(payload)
    else:
        show_error(status, payload)


def product_update() -> None:
    section("Update product (PATCH /products/{id})")
    pid = ask("nosql_product_id")
    if not pid:
        return
    body: dict = {}
    name = ask("new product_name (blank to skip)")
    price = ask("new current_price (blank to skip)")
    stock_raw = ask("new available_stock (blank to skip)")
    if name:
        body["product_name"] = name
    if price:
        body["current_price"] = price
    if stock_raw:
        try:
            body["available_stock"] = int(stock_raw)
        except ValueError:
            info("(invalid stock)")
            return
    details_raw = ask("new technical_details JSON (blank to skip)")
    if details_raw:
        try:
            body["technical_details"] = json.loads(details_raw)
        except json.JSONDecodeError as exc:
            info(f"(invalid JSON: {exc})")
            return
    if not body:
        info("(nothing to update)")
        return
    status, payload = api("PATCH", f"/products/{pid}", body)
    if status == 200:
        success("updated")
        show_product(payload)
    else:
        show_error(status, payload)


def product_delete() -> None:
    section("Delete product (DELETE /products/{id})")
    pid = ask("nosql_product_id")
    if not pid:
        return
    status, payload = api("DELETE", f"/products/{pid}")
    if status == 204:
        success(f"product {pid} deleted")
    else:
        show_error(status, payload)


def products_menu() -> None:
    run_menu(
        "Manage Products  [MongoDB]",
        {
            "1": ("Create", product_create),
            "2": ("List all", product_list),
            "3": ("Read by ID", product_read),
            "4": ("Update", product_update),
            "5": ("Delete", product_delete),
        },
    )


# ++==========================++
# || CRUD DE CARRINHO (Redis) ||
# ++==========================++

def cart_view() -> None:
    section("View cart (GET /carts/{customer_id})")
    cid = ask_int("customer_id")
    if cid is None:
        return
    status, payload = api("GET", f"/carts/{cid}")
    if status == 200:
        show_cart(payload)
    else:
        show_error(status, payload)


def cart_add() -> None:
    section("Add item (POST /carts/{customer_id}/items)")
    cid = ask_int("customer_id")
    if cid is None:
        return
    pid = ask("nosql_product_id")
    qty = ask_int("quantity")
    if not pid or qty is None or qty <= 0:
        info("(product_id and positive quantity required)")
        return
    status, payload = api(
        "POST", f"/carts/{cid}/items", {"nosql_product_id": pid, "quantity": qty}
    )
    if status == 200:
        success("item added (cart TTL reset to 24h)")
        show_cart(payload)
    else:
        show_error(status, payload)


def cart_clear() -> None:
    section("Clear cart (DELETE /carts/{customer_id})")
    cid = ask_int("customer_id")
    if cid is None:
        return
    status, payload = api("DELETE", f"/carts/{cid}")
    if status == 204:
        success(f"cart for customer #{cid} cleared")
    else:
        show_error(status, payload)


def carts_menu() -> None:
    run_menu(
        "Manage Shopping Carts  [Redis]",
        {
            "1": ("View cart", cart_view),
            "2": ("Add item", cart_add),
            "3": ("Clear cart", cart_clear),
        },
    )


# ++=============================================++
# || SILUMAÇÃO DO CHECKOUT (TRANSAÇÃO POLIGLOTA) ||
# ++=============================================++

def checkout_run() -> None:
    header("Checkout Simulation  [Redis -> MongoDB -> PostgreSQL]")
    cid = ask_int("customer_id")
    if cid is None:
        return

    section("Step 1/3: read cart from Redis")
    status, cart = api("GET", f"/carts/{cid}")
    if status != 200:
        show_error(status, cart)
        return
    show_cart(cart)
    if not cart.get("items"):
        info("\n   cart is empty - checkout would fail with 400. Aborting demo.")
        return

    section("Step 2/3: POST /checkout")
    info("server orchestrates:")
    info("  (a) Mongo: validate prices + atomically decrement available_stock")
    info("  (b) Postgres: insert completed_order + order_item rows (transaction)")
    info("  (c) Redis: delete cart key on success")
    print()
    status, result = api("POST", "/checkout", {"customer_id": cid})

    section("Step 3/3: result")
    if status == 200:
        success("checkout succeeded")
        show_order(result)
        print()
        info("verifiable side effects:")
        info("  - Postgres now has rows in completed_order + order_item")
        info("  - Mongo available_stock was decremented for each line item")
        info("  - Redis cart key 'cart:%d' was deleted" % cid)
    else:
        show_error(status, result)
        info("\n   no order was persisted; any in-flight stock decrements were rolled back")


# ++================++
# || MENU PRINCIPAL ||
# ++================++

def main_menu() -> None:
    while True:
        header("Polyglot Persistence Backend  -  Demo CLI")
        info(f"API base: {BASE_URL}")
        print()
        print("   [1] Manage Customers   (PostgreSQL)")
        print("   [2] Manage Products    (MongoDB)")
        print("   [3] Manage Carts       (Redis)")
        print("   [4] Run Checkout       (polyglot transaction)")
        print("   [5] Exit")
        choice = input("\n > ").strip()
        if choice == "1":
            customers_menu()
        elif choice == "2":
            products_menu()
        elif choice == "3":
            carts_menu()
        elif choice == "4":
            try:
                checkout_run()
            except KeyboardInterrupt:
                print("\n   (cancelled)")
            pause()
        elif choice == "5":
            print("\nGoodbye.\n")
            return
        else:
            info("(invalid choice)")


if __name__ == "__main__":
    try:
        main_menu()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye.\n")
        sys.exit(0)
