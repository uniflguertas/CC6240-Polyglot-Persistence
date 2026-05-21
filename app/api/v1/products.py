from decimal import Decimal
from typing import Annotated, Any

from bson import ObjectId
from bson.decimal128 import Decimal128
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query, status
from pymongo import ReturnDocument

from app.db.mongo import mongo_db
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])

PRODUCT_COLLECTION = "product_catalog"


def _collection():
    return mongo_db[PRODUCT_COLLECTION]


def _decode_price(value: Any) -> Decimal:
    if isinstance(value, Decimal128):
        return value.to_decimal()
    return Decimal(str(value))


def _to_response(doc: dict[str, Any]) -> ProductResponse:
    return ProductResponse(
        nosql_product_id=str(doc["_id"]),
        product_name=doc["product_name"],
        current_price=_decode_price(doc["current_price"]),
        available_stock=doc["available_stock"],
        technical_details=doc.get("technical_details", {}),
    )


def _parse_oid(nosql_product_id: str) -> ObjectId:
    try:
        return ObjectId(nosql_product_id)
    except (InvalidId, TypeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="invalid nosql_product_id")


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(payload: ProductCreate) -> ProductResponse:
    doc = payload.model_dump()
    doc["current_price"] = Decimal128(doc["current_price"])
    result = await _collection().insert_one(doc)
    created = await _collection().find_one({"_id": result.inserted_id})
    return _to_response(created)


@router.get("", response_model=list[ProductResponse])
async def list_products(
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    skip: Annotated[int, Query(ge=0)] = 0,
) -> list[ProductResponse]:
    cursor = _collection().find().skip(skip).limit(limit)
    return [_to_response(doc) async for doc in cursor]


@router.get("/{nosql_product_id}", response_model=ProductResponse)
async def get_product(nosql_product_id: str) -> ProductResponse:
    doc = await _collection().find_one({"_id": _parse_oid(nosql_product_id)})
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="product not found")
    return _to_response(doc)


@router.patch("/{nosql_product_id}", response_model=ProductResponse)
async def update_product(nosql_product_id: str, payload: ProductUpdate) -> ProductResponse:
    oid = _parse_oid(nosql_product_id)
    data = payload.model_dump(exclude_unset=True)
    if "current_price" in data and data["current_price"] is not None:
        data["current_price"] = Decimal128(data["current_price"])

    if not data:
        doc = await _collection().find_one({"_id": oid})
    else:
        doc = await _collection().find_one_and_update(
            {"_id": oid},
            {"$set": data},
            return_document=ReturnDocument.AFTER,
        )

    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="product not found")
    return _to_response(doc)


@router.delete("/{nosql_product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(nosql_product_id: str) -> None:
    result = await _collection().delete_one({"_id": _parse_oid(nosql_product_id)})
    if result.deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="product not found")
