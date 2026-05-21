from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    product_name: str = Field(..., min_length=1)
    current_price: Decimal = Field(..., ge=0)
    available_stock: int = Field(..., ge=0)
    technical_details: dict[str, Any] = Field(default_factory=dict)


class ProductUpdate(BaseModel):
    product_name: str | None = Field(default=None, min_length=1)
    current_price: Decimal | None = Field(default=None, ge=0)
    available_stock: int | None = Field(default=None, ge=0)
    technical_details: dict[str, Any] | None = None


class ProductResponse(BaseModel):
    nosql_product_id: str
    product_name: str
    current_price: Decimal
    available_stock: int
    technical_details: dict[str, Any]
