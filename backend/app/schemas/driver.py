from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, date


class DriverBase(BaseModel):
    """Base driver schema with common fields"""

    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    vehicle_type: Optional[str] = Field(None, max_length=50)
    max_stops: int = Field(default=15, ge=1, le=50)
    max_route_duration_minutes: int = Field(default=240, ge=30, le=720)
    home_address: Optional[str] = Field(None, max_length=500)


class DriverCreate(DriverBase):
    """Schema for creating a new driver"""

    pass


class DriverUpdate(BaseModel):
    """Schema for updating an existing driver"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    vehicle_type: Optional[str] = Field(None, max_length=50)
    max_stops: Optional[int] = Field(None, ge=1, le=50)
    max_route_duration_minutes: Optional[int] = Field(None, ge=30, le=720)
    home_address: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class DriverResponse(DriverBase):
    """Schema for driver in responses"""

    id: int
    home_latitude: Optional[float]
    home_longitude: Optional[float]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class AvailabilityBase(BaseModel):
    """Base availability schema"""

    date: date
    start_time: str = Field(..., pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    end_time: str = Field(..., pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    status: str = Field(default="available", pattern=r"^(available|tentative|unavailable)$")


class AvailabilityCreate(AvailabilityBase):
    """Schema for creating availability"""

    driver_id: int


class AvailabilityUpdate(BaseModel):
    """Schema for updating availability"""

    start_time: Optional[str] = Field(None, pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    end_time: Optional[str] = Field(None, pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    status: Optional[str] = Field(None, pattern=r"^(available|tentative|unavailable)$")


class AvailabilityResponse(AvailabilityBase):
    """Schema for availability in responses"""

    id: int
    driver_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class DriverWithAvailability(DriverResponse):
    """Driver with their availability slots"""

    availability_slots: list[AvailabilityResponse] = []


class BulkAvailabilityCreate(BaseModel):
    """Schema for setting availability for multiple dates"""

    driver_id: int
    dates: list[date]
    start_time: str = Field(..., pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    end_time: str = Field(..., pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    status: str = Field(default="available")


class AvailableDriverResponse(BaseModel):
    """Driver available for a specific date"""

    driver_id: int
    driver_name: str
    start_time: str
    end_time: str
    duration_minutes: int
    max_stops: int
    home_lat: Optional[float]
    home_lng: Optional[float]
