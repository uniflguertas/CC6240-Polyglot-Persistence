from pydantic import BaseModel, Field


class CartItem(BaseModel):
    nosql_product_id: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)


class CartUpsert(BaseModel):
    items: list[CartItem]


class CartResponse(BaseModel):
    customer_id: int
    items: list[CartItem]
