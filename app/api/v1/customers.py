from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_session
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customers"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(payload: CustomerCreate, session: SessionDep) -> Customer:
    customer = Customer(full_name=payload.full_name, email=payload.email)
    session.add(customer)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="email already registered")
    await session.refresh(customer)
    return customer


@router.get("", response_model=list[CustomerResponse])
async def list_customers(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Customer]:
    result = await session.execute(
        select(Customer).order_by(Customer.customer_id).offset(offset).limit(limit)
    )
    return list(result.scalars().all())


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: int, session: SessionDep) -> Customer:
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="customer not found")
    return customer


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int, payload: CustomerUpdate, session: SessionDep
) -> Customer:
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="customer not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(customer, key, value)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="email already registered")
    await session.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(customer_id: int, session: SessionDep) -> None:
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="customer not found")
    await session.delete(customer)
    await session.commit()
