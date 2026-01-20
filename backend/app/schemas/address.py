from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class AddressBase(BaseModel):
    """Base address schema with common fields"""

    street: str = Field(..., min_length=1, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: str = Field(default="USA", max_length=100)
    recipient_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = Field(None, max_length=500)
    service_time_minutes: int = Field(default=5, ge=1, le=60)
    preferred_time_start: Optional[str] = Field(
        None, pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"
    )
    preferred_time_end: Optional[str] = Field(
        None, pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"
    )
    preferred_driver_id: Optional[int] = Field(
        None, description="Preferred driver for this address (soft constraint)"
    )
    prefers_male_driver: bool = Field(default=False)
    prefers_female_driver: bool = Field(default=False)


class AddressCreate(AddressBase):
    """Schema for creating a new address"""

    pass


class AddressUpdate(BaseModel):
    """Schema for updating an existing address"""

    street: Optional[str] = Field(None, min_length=1, max_length=255)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    recipient_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = Field(None, max_length=500)
    service_time_minutes: Optional[int] = Field(None, ge=1, le=60)
    preferred_time_start: Optional[str] = Field(
        None, pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"
    )
    preferred_time_end: Optional[str] = Field(
        None, pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"
    )
    preferred_driver_id: Optional[int] = Field(
        None, description="Preferred driver for this address (soft constraint)"
    )
    prefers_male_driver: Optional[bool] = None
    prefers_female_driver: Optional[bool] = None
    is_active: Optional[bool] = None


class AddressResponse(AddressBase):
    """Schema for address in responses"""

    id: int
    latitude: Optional[float]
    longitude: Optional[float]
    geocode_status: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    preferred_driver_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AddressBulkImport(BaseModel):
    """Response schema for CSV bulk import"""

    total_rows: int
    successful: int
    failed: int
    errors: list[dict]  # [{row: 5, error: "Invalid address"}]
    created_ids: list[int]
