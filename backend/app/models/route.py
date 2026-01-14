from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base


class DeliveryDay(Base):
    __tablename__ = "delivery_days"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    depot_latitude = Column(Float, nullable=True)
    depot_longitude = Column(Float, nullable=True)
    depot_address = Column(String(500), nullable=True)
    status = Column(String(20), default="draft")  # draft, optimized, in_progress, completed
    total_stops = Column(Integer, default=0)
    total_drivers = Column(Integer, default=0)
    total_distance_km = Column(Float, default=0.0)
    total_duration_minutes = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    routes = relationship("Route", back_populates="delivery_day", cascade="all, delete-orphan")


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    delivery_day_id = Column(Integer, ForeignKey("delivery_days.id", ondelete="CASCADE"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False)
    route_number = Column(Integer, nullable=False)
    color = Column(String(7), nullable=True)  # Hex color for map display
    total_stops = Column(Integer, default=0)
    total_distance_km = Column(Float, default=0.0)
    total_duration_minutes = Column(Float, default=0.0)
    route_geometry = Column(Text, nullable=True)  # GeoJSON LineString
    start_time = Column(String(5), nullable=True)  # "09:00"
    end_time = Column(String(5), nullable=True)  # "13:30"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    delivery_day = relationship("DeliveryDay", back_populates="routes")
    driver = relationship("Driver")
    stops = relationship("RouteStop", back_populates="route", cascade="all, delete-orphan", order_by="RouteStop.sequence")


class RouteStop(Base):
    __tablename__ = "route_stops"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id", ondelete="CASCADE"), nullable=False)
    address_id = Column(Integer, ForeignKey("addresses.id", ondelete="CASCADE"), nullable=False)
    sequence = Column(Integer, nullable=False)  # Order in the route (0, 1, 2, ...)
    estimated_arrival = Column(String(5), nullable=True)  # "10:30"
    estimated_departure = Column(String(5), nullable=True)  # "10:35"
    distance_from_previous_km = Column(Float, default=0.0)
    duration_from_previous_minutes = Column(Float, default=0.0)
    status = Column(String(20), default="pending")  # pending, completed, skipped
    actual_arrival = Column(DateTime, nullable=True)
    actual_departure = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    route = relationship("Route", back_populates="stops")
    address = relationship("Address")
