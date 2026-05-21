from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: int
    order_id: int
    nosql_product_id: str
    quantity: int
    locked_price: Decimal


class CompletedOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: int
    customer_id: int
    total_amount: Decimal
    payment_status: str
    created_at: datetime
    items: list[OrderItemResponse] = Field(default_factory=list)


class CheckoutRequest(BaseModel):
    customer_id: int
