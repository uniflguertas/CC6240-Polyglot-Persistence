from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CompletedOrder(Base):
    __tablename__ = "completed_order"

    order_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customer.customer_id"), nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=False),
        server_default=func.now(),
        nullable=False,
    )


class OrderItem(Base):
    __tablename__ = "order_item"

    item_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("completed_order.order_id"), nullable=False
    )
    nosql_product_id: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    locked_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
