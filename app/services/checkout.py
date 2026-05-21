import json
import logging
from decimal import Decimal
from typing import Any

from bson import ObjectId
from bson.decimal128 import Decimal128
from bson.errors import InvalidId
from fastapi import HTTPException, status

from app.db.mongo import mongo_db
from app.db.postgres import async_session_factory
from app.db.redis import redis_client
from app.models.customer import Customer
from app.models.order import CompletedOrder, OrderItem
from app.schemas.cart import CartItem
from app.schemas.order import CompletedOrderResponse, OrderItemResponse

logger = logging.getLogger(__name__)

PRODUCT_COLLECTION = "product_catalog"
PAYMENT_STATUS_PAID = "paid"


def _cart_key(customer_id: int) -> str:
    return f"cart:{customer_id}"


async def _load_cart(customer_id: int) -> list[CartItem]:
    raw = await redis_client.get(_cart_key(customer_id))
    if raw is None:
        return []
    return [CartItem(**item) for item in json.loads(raw)]


def _decode_price(value: Any) -> Decimal:
    if isinstance(value, Decimal128):
        return value.to_decimal()
    return Decimal(str(value))


async def _restore_stock(decremented: list[tuple[ObjectId, int]]) -> None:
    for oid, qty in decremented:
        try:
            await mongo_db[PRODUCT_COLLECTION].update_one(
                {"_id": oid}, {"$inc": {"available_stock": qty}}
            )
        except Exception:
            logger.exception("compensation failed: could not restore stock for %s", oid)


async def checkout(customer_id: int) -> CompletedOrderResponse:
    async with async_session_factory() as session:
        customer = await session.get(Customer, customer_id)
        if customer is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="customer not found")

    cart_items = await _load_cart(customer_id)
    if not cart_items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="cart is empty")

    try:
        product_oids = [ObjectId(item.nosql_product_id) for item in cart_items]
    except InvalidId:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="cart contains invalid nosql_product_id"
        )

    cursor = mongo_db[PRODUCT_COLLECTION].find({"_id": {"$in": product_oids}})
    products = {str(doc["_id"]): doc async for doc in cursor}

    line_items: list[tuple[str, int, Decimal]] = []
    for item in cart_items:
        product = products.get(item.nosql_product_id)
        if product is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"product {item.nosql_product_id} not found",
            )
        if product["available_stock"] < item.quantity:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=f"insufficient stock for product {item.nosql_product_id}",
            )
        locked_price = _decode_price(product["current_price"])
        line_items.append((item.nosql_product_id, item.quantity, locked_price))

    total_amount = sum((Decimal(qty) * price for _, qty, price in line_items), Decimal("0"))

    decremented: list[tuple[ObjectId, int]] = []
    try:
        for nosql_id, qty, _price in line_items:
            oid = ObjectId(nosql_id)
            result = await mongo_db[PRODUCT_COLLECTION].update_one(
                {"_id": oid, "available_stock": {"$gte": qty}},
                {"$inc": {"available_stock": -qty}},
            )
            if result.modified_count == 0:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail=f"insufficient stock for product {nosql_id}",
                )
            decremented.append((oid, qty))
    except Exception:
        await _restore_stock(decremented)
        raise

    try:
        async with async_session_factory() as session:
            async with session.begin():
                order = CompletedOrder(
                    customer_id=customer_id,
                    total_amount=total_amount,
                    payment_status=PAYMENT_STATUS_PAID,
                )
                session.add(order)
                await session.flush()

                items: list[OrderItem] = []
                for nosql_id, qty, price in line_items:
                    item_row = OrderItem(
                        order_id=order.order_id,
                        nosql_product_id=nosql_id,
                        quantity=qty,
                        locked_price=price,
                    )
                    session.add(item_row)
                    items.append(item_row)
                await session.flush()

            response = CompletedOrderResponse(
                order_id=order.order_id,
                customer_id=order.customer_id,
                total_amount=order.total_amount,
                payment_status=order.payment_status,
                created_at=order.created_at,
                items=[
                    OrderItemResponse(
                        item_id=row.item_id,
                        order_id=row.order_id,
                        nosql_product_id=row.nosql_product_id,
                        quantity=row.quantity,
                        locked_price=row.locked_price,
                    )
                    for row in items
                ],
            )
    except HTTPException:
        await _restore_stock(decremented)
        raise
    except Exception:
        logger.exception("checkout postgres write failed; restoring mongo stock")
        await _restore_stock(decremented)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, detail="checkout failed"
        )

    try:
        await redis_client.delete(_cart_key(customer_id))
    except Exception:
        logger.warning(
            "checkout succeeded but failed to clear cart for customer %s; "
            "cart will expire via TTL",
            customer_id,
        )

    return response
