from fastapi import APIRouter

from app.schemas.order import CheckoutRequest, CompletedOrderResponse
from app.services.checkout import checkout as checkout_service

router = APIRouter(prefix="/checkout", tags=["checkout"])


@router.post("", response_model=CompletedOrderResponse)
async def post_checkout(payload: CheckoutRequest) -> CompletedOrderResponse:
    return await checkout_service(payload.customer_id)
