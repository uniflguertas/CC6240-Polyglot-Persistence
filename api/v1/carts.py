import json

from fastapi import APIRouter, status

from app.db.redis import redis_client
from app.schemas.cart import CartItem, CartResponse, CartUpsert

router = APIRouter(prefix="/carts", tags=["carts"])

CART_TTL_SECONDS = 24 * 60 * 60

def _cart_key(customer_id: int) -> str:
    return f"cart:{customer_id}"


async def _load_items(customer_id: int) -> list[CartItem]:
    raw = await redis_client.get(_cart_key(customer_id))
    if raw is None:
        return []
    return [CartItem(**item) for item in json.loads(raw)]


async def _save_items(customer_id: int, items: list[CartItem]) -> None:
    payload = json.dumps([item.model_dump() for item in items])
    await redis_client.set(_cart_key(customer_id), payload, ex=CART_TTL_SECONDS)


@router.get("/{customer_id}", response_model=CartResponse)
async def get_cart(customer_id: int) -> CartResponse:
    items = await _load_items(customer_id)
    return CartResponse(customer_id=customer_id, items=items)


@router.put("/{customer_id}", response_model=CartResponse)
async def replace_cart(customer_id: int, payload: CartUpsert) -> CartResponse:
    await _save_items(customer_id, payload.items)
    return CartResponse(customer_id=customer_id, items=payload.items)


@router.post("/{customer_id}/items", response_model=CartResponse)
async def add_item(customer_id: int, item: CartItem) -> CartResponse:
    items = await _load_items(customer_id)
    for existing in items:
        if existing.nosql_product_id == item.nosql_product_id:
            existing.quantity += item.quantity
            break
    else:
        items.append(item)
    await _save_items(customer_id, items)
    return CartResponse(customer_id=customer_id, items=items)


@router.delete("/{customer_id}/items/{nosql_product_id}", response_model=CartResponse)
async def remove_item(customer_id: int, nosql_product_id: str) -> CartResponse:
    items = await _load_items(customer_id)
    remaining = [i for i in items if i.nosql_product_id != nosql_product_id]
    if remaining:
        await _save_items(customer_id, remaining)
    else:
        await redis_client.delete(_cart_key(customer_id))
    return CartResponse(customer_id=customer_id, items=remaining)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(customer_id: int) -> None:
    await redis_client.delete(_cart_key(customer_id))
