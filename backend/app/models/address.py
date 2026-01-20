from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Address(Base):
    """Address model for delivery locations"""

    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)

    # Address fields
    street = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(50), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), default="USA")

    # Geocoded coordinates
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    geocode_status = Column(
        String(20), default="pending"
    )  # pending, success, not_found, error

    # Delivery metadata
    recipient_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    notes = Column(String(500), nullable=True)

    # Service time estimate (minutes to complete delivery)
    service_time_minutes = Column(Integer, default=5)

    # Preferred time window (optional)
    preferred_time_start = Column(String(5), nullable=True)  # "09:00"
    preferred_time_end = Column(String(5), nullable=True)  # "12:00"

    # Preferred driver (soft constraint for route optimization)
    preferred_driver_id = Column(
        Integer, ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True
    )

    # Gender preference for driver assignment
    prefers_male_driver = Column(Boolean, default=False)
    prefers_female_driver = Column(Boolean, default=False)

    # Relationships
    preferred_driver = relationship("Driver", foreign_keys=[preferred_driver_id])

    # Status tracking
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self):
        return f"<Address(id={self.id}, street='{self.street}', city='{self.city}')>"
