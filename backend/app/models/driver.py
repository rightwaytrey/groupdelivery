from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Driver(Base):
    """Driver/Volunteer model"""

    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)

    # Driver info
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True, unique=True)
    phone = Column(String(20), nullable=True)

    # Vehicle info (optional capacity constraints)
    vehicle_type = Column(String(50), nullable=True)  # "sedan", "suv", "van", etc.
    max_stops = Column(Integer, default=15)  # Soft limit for route planning
    max_route_duration_minutes = Column(Integer, default=240)  # Maximum route duration in minutes

    # Home location (for route start/end)
    home_latitude = Column(Float, nullable=True)
    home_longitude = Column(Float, nullable=True)
    home_address = Column(String(500), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    availability_slots = relationship(
        "DriverAvailability", back_populates="driver", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Driver(id={self.id}, name='{self.name}')>"


class DriverAvailability(Base):
    """Tracks which drivers are available on which days/times"""

    __tablename__ = "driver_availability"

    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False)

    # Date and time window
    date = Column(Date, nullable=False)
    start_time = Column(String(5), nullable=False)  # "09:00"
    end_time = Column(String(5), nullable=False)  # "14:00"

    # Status
    status = Column(
        String(20), default="available"
    )  # available, tentative, unavailable

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationship
    driver = relationship("Driver", back_populates="availability_slots")

    # Index for efficient queries by driver and date
    __table_args__ = (Index("ix_driver_availability_driver_date", "driver_id", "date"),)

    def __repr__(self):
        return f"<DriverAvailability(driver_id={self.driver_id}, date={self.date})>"
