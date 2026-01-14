from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import date, datetime


# DeliveryDay schemas
class DeliveryDayBase(BaseModel):
    date: date
    depot_latitude: Optional[float] = None
    depot_longitude: Optional[float] = None
    depot_address: Optional[str] = None


class DeliveryDayCreate(DeliveryDayBase):
    pass


class DeliveryDay(DeliveryDayBase):
    id: int
    status: str
    total_stops: int
    total_drivers: int
    total_distance_km: float
    total_duration_minutes: float
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# Route schemas
class RouteStopBase(BaseModel):
    address_id: int
    sequence: int
    estimated_arrival: Optional[str] = None
    estimated_departure: Optional[str] = None
    distance_from_previous_km: float = 0.0
    duration_from_previous_minutes: float = 0.0


class RouteStop(RouteStopBase):
    id: int
    route_id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class RouteBase(BaseModel):
    delivery_day_id: int
    driver_id: int
    route_number: int
    color: Optional[str] = None


class Route(RouteBase):
    id: int
    total_stops: int
    total_distance_km: float
    total_duration_minutes: float
    route_geometry: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    stops: List[RouteStop] = []
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# Driver constraints for optimization
class DriverConstraints(BaseModel):
    max_stops: Optional[int] = Field(default=15, ge=1, le=50)
    max_route_duration_minutes: Optional[int] = Field(default=120, ge=60, le=720)


# Optimization request/response schemas
class OptimizationRequest(BaseModel):
    date: date
    address_ids: List[int] = Field(..., description="List of address IDs to include in optimization")
    driver_ids: List[int] = Field(..., description="List of driver IDs available for this day")
    depot_latitude: Optional[float] = Field(None, description="Starting point latitude (depot)")
    depot_longitude: Optional[float] = Field(None, description="Starting point longitude (depot)")
    depot_address: Optional[str] = None
    start_time: str = Field(default="09:00", description="Routes start time (HH:MM)")
    driver_constraints: Optional[Dict[int, DriverConstraints]] = Field(
        None,
        description="Per-driver constraints for max stops and route duration. Keys are driver IDs."
    )
    time_limit_seconds: int = Field(default=30, description="Max time for solver to run")


class OptimizationResult(BaseModel):
    delivery_day_id: int
    date: date
    status: str
    total_routes: int
    total_stops: int
    total_distance_km: float
    total_duration_minutes: float
    routes: List[Route]
    dropped_addresses: List[int] = Field(default=[], description="Addresses that couldn't be assigned")
    message: Optional[str] = None


# Route detail with address info
class RouteStopDetail(RouteStop):
    address: dict  # Will contain address details


class RouteDetail(Route):
    stops: List[RouteStopDetail]
    driver: dict  # Will contain driver details
