from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CustomerCreate(BaseModel):
    full_name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)


class CustomerUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1)
    email: str | None = Field(default=None, min_length=1)


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: int
    full_name: str
    email: str
    created_at: datetime
