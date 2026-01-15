from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
from datetime import date, datetime
import io
import csv
from app.database import get_db
from app.models.driver import Driver, DriverAvailability
from app.models.user import User
from app.schemas.driver import (
    DriverCreate,
    DriverUpdate,
    DriverResponse,
    DriverWithAvailability,
    DriverBulkImport,
    AvailabilityCreate,
    AvailabilityUpdate,
    AvailabilityResponse,
    BulkAvailabilityCreate,
    AvailableDriverResponse,
)
from app.services.geocoding import geocoding_service
from app.services.csv_import import driver_csv_import_service
from app.services.auth import get_current_active_user

router = APIRouter(prefix="/api/drivers", tags=["drivers"])


@router.post("", response_model=DriverResponse, status_code=201)
async def create_driver(
    driver: DriverCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new driver/volunteer"""

    # Geocode home address if provided
    home_lat, home_lng = None, None
    geocode_warning = None
    if driver.home_address:
        # Try to parse address or use as-is
        lat, lng, status = await geocoding_service.geocode_address(
            street=driver.home_address,
            city="",  # Address should be complete
            country="USA",
        )
        if status == "success":
            home_lat, home_lng = lat, lng
        else:
            geocode_warning = f"Could not geocode home address. The 'end at home' feature will not be available for this driver. Status: {status}"

    # Convert empty strings to None to avoid unique constraint issues
    driver_data = driver.model_dump(exclude={"home_address"})
    if driver_data.get("email") == "":
        driver_data["email"] = None
    if driver_data.get("phone") == "":
        driver_data["phone"] = None

    db_driver = Driver(
        **driver_data,
        home_address=driver.home_address or None,
        home_latitude=home_lat,
        home_longitude=home_lng,
    )

    db.add(db_driver)
    await db.commit()
    await db.refresh(db_driver)

    # Add warning to response if geocoding failed
    response = DriverResponse.model_validate(db_driver)
    if geocode_warning:
        response.warning = geocode_warning

    return response


@router.get("", response_model=list[DriverResponse])
async def list_drivers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all drivers with optional filters"""

    query = select(Driver)

    if is_active is not None:
        query = query.where(Driver.is_active == is_active)

    query = query.order_by(Driver.name).offset(skip).limit(limit)

    result = await db.execute(query)
    drivers = result.scalars().all()

    return drivers


@router.get("/export")
async def export_drivers_csv(
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Export all drivers as CSV."""

    # Build query with optional filters (matching list_drivers logic)
    query = select(Driver)
    if is_active is not None:
        query = query.where(Driver.is_active == is_active)
    query = query.order_by(Driver.name)

    result = await db.execute(query)
    drivers = result.scalars().all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'ID',
        'Name',
        'Email',
        'Phone',
        'Vehicle Type',
        'Max Stops',
        'Max Route Duration (min)',
        'Home Address',
        'Home Latitude',
        'Home Longitude',
        'Is Active',
        'Created At',
        'Updated At'
    ])

    # Write driver rows
    for driver in drivers:
        writer.writerow([
            driver.id,
            driver.name,
            driver.email or '',
            driver.phone or '',
            driver.vehicle_type or '',
            driver.max_stops or '',
            driver.max_route_duration_minutes or '',
            driver.home_address or '',
            driver.home_latitude or '',
            driver.home_longitude or '',
            'Yes' if driver.is_active else 'No',
            driver.created_at.isoformat() if driver.created_at else '',
            driver.updated_at.isoformat() if driver.updated_at else ''
        ])

    # Prepare response
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"drivers_{timestamp}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/available", response_model=list[AvailableDriverResponse])
async def get_available_drivers(
    target_date: date = Query(..., description="Date to check availability"),
    min_duration_minutes: int = Query(60, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all drivers available on a specific date"""

    result = await db.execute(
        select(DriverAvailability, Driver)
        .join(Driver)
        .where(
            and_(
                DriverAvailability.date == target_date,
                DriverAvailability.status == "available",
                Driver.is_active == True,
            )
        )
    )
    rows = result.all()

    available = []
    for availability, driver in rows:
        # Calculate duration
        start = datetime.strptime(availability.start_time, "%H:%M")
        end = datetime.strptime(availability.end_time, "%H:%M")
        duration = (end - start).seconds // 60

        if duration >= min_duration_minutes:
            available.append(
                AvailableDriverResponse(
                    driver_id=driver.id,
                    driver_name=driver.name,
                    start_time=availability.start_time,
                    end_time=availability.end_time,
                    duration_minutes=duration,
                    max_stops=driver.max_stops,
                    home_lat=driver.home_latitude,
                    home_lng=driver.home_longitude,
                )
            )

    return available


@router.get("/{driver_id}", response_model=DriverWithAvailability)
async def get_driver(
    driver_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a single driver by ID with their availability"""

    result = await db.execute(
        select(Driver).where(Driver.id == driver_id)
    )
    driver = result.scalar_one_or_none()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    # Load availability slots
    availability_result = await db.execute(
        select(DriverAvailability)
        .where(DriverAvailability.driver_id == driver_id)
        .order_by(DriverAvailability.date)
    )
    availability_slots = availability_result.scalars().all()

    return DriverWithAvailability(
        **driver.__dict__, availability_slots=availability_slots
    )


@router.put("/{driver_id}", response_model=DriverResponse)
async def update_driver(
    driver_id: int,
    driver_update: DriverUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an existing driver"""

    result = await db.execute(select(Driver).where(Driver.id == driver_id))
    db_driver = result.scalar_one_or_none()

    if not db_driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    update_data = driver_update.model_dump(exclude_unset=True)
    geocode_warning = None

    # Convert empty strings to None to avoid unique constraint issues
    if "email" in update_data and update_data["email"] == "":
        update_data["email"] = None
    if "phone" in update_data and update_data["phone"] == "":
        update_data["phone"] = None

    # Re-geocode home address if changed
    if "home_address" in update_data and update_data["home_address"]:
        lat, lng, status = await geocoding_service.geocode_address(
            street=update_data["home_address"], city="", country="USA"
        )
        if status == "success":
            update_data["home_latitude"] = lat
            update_data["home_longitude"] = lng
        else:
            geocode_warning = f"Could not geocode home address. The 'end at home' feature will not be available for this driver. Status: {status}"

    # Apply updates
    for field, value in update_data.items():
        setattr(db_driver, field, value)

    await db.commit()
    await db.refresh(db_driver)

    # Add warning to response if geocoding failed
    response = DriverResponse.model_validate(db_driver)
    if geocode_warning:
        response.warning = geocode_warning

    return response


@router.delete("/{driver_id}", status_code=204)
async def delete_driver(
    driver_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a driver permanently"""

    result = await db.execute(select(Driver).where(Driver.id == driver_id))
    db_driver = result.scalar_one_or_none()

    if not db_driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    await db.delete(db_driver)
    await db.commit()

    return None


@router.delete("", status_code=204)
async def delete_all_drivers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete all drivers permanently"""

    result = await db.execute(select(Driver))
    drivers = result.scalars().all()

    for driver in drivers:
        await db.delete(driver)

    await db.commit()

    return None


@router.post("/import", response_model=DriverBulkImport)
async def import_drivers_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Import drivers from CSV file"""

    # Validate file type
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        # Parse CSV
        valid_rows, parse_errors = await driver_csv_import_service.parse_csv(file)

        # Create drivers from valid rows
        created_ids = []
        driver_errors = []
        geocoding_warnings = []

        for row in valid_rows:
            row_num = row.pop("_row_number")

            try:
                # Geocode home address if provided
                home_lat, home_lng = None, None
                if row.get("home_address"):
                    lat, lng, status = await geocoding_service.geocode_address(
                        street=row["home_address"],
                        city="",  # Address should be complete
                        country="USA",
                    )
                    if status == "success":
                        home_lat, home_lng = lat, lng
                    else:
                        geocoding_warnings.append(
                            f"Row {row_num} ({row['name']}): Could not geocode home address"
                        )

                # Create driver
                db_driver = Driver(
                    name=row["name"],
                    email=row.get("email"),
                    phone=row.get("phone"),
                    vehicle_type=row.get("vehicle_type"),
                    max_stops=row.get("max_stops", 15),
                    max_route_duration_minutes=row.get("max_route_duration_minutes", 240),
                    home_address=row.get("home_address"),
                    home_latitude=home_lat,
                    home_longitude=home_lng,
                )
                db.add(db_driver)
                await db.flush()
                created_ids.append(db_driver.id)

            except Exception as e:
                driver_errors.append(f"Row {row_num}: {str(e)}")

        await db.commit()

        # Combine all errors
        all_errors = [f"Row {e['row']}: {e['error']}" for e in parse_errors] + driver_errors

        return DriverBulkImport(
            total=len(valid_rows) + len(parse_errors),
            successful=len(created_ids),
            failed=len(all_errors),
            errors=all_errors,
            created_ids=created_ids,
            geocoding_warnings=geocoding_warnings,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Availability endpoints


@router.post("/availability", response_model=AvailabilityResponse, status_code=201)
async def create_availability(
    availability: AvailabilityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a single availability slot for a driver"""

    # Check if driver exists
    result = await db.execute(
        select(Driver).where(Driver.id == availability.driver_id)
    )
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    # Check if availability already exists for this date
    existing = await db.execute(
        select(DriverAvailability).where(
            and_(
                DriverAvailability.driver_id == availability.driver_id,
                DriverAvailability.date == availability.date,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="Availability already exists for this date"
        )

    db_availability = DriverAvailability(**availability.model_dump())
    db.add(db_availability)
    await db.commit()
    await db.refresh(db_availability)

    return db_availability


@router.post("/availability/bulk", response_model=list[AvailabilityResponse])
async def create_bulk_availability(
    bulk: BulkAvailabilityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create availability for multiple dates at once"""

    # Check if driver exists
    result = await db.execute(select(Driver).where(Driver.id == bulk.driver_id))
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    created = []
    for target_date in bulk.dates:
        # Check if already exists
        existing = await db.execute(
            select(DriverAvailability).where(
                and_(
                    DriverAvailability.driver_id == bulk.driver_id,
                    DriverAvailability.date == target_date,
                )
            )
        )
        if not existing.scalar_one_or_none():
            db_availability = DriverAvailability(
                driver_id=bulk.driver_id,
                date=target_date,
                start_time=bulk.start_time,
                end_time=bulk.end_time,
                status=bulk.status,
            )
            db.add(db_availability)
            created.append(db_availability)

    await db.commit()
    for item in created:
        await db.refresh(item)

    return created


@router.get("/availability/{availability_id}", response_model=AvailabilityResponse)
async def get_availability(
    availability_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a single availability slot"""

    result = await db.execute(
        select(DriverAvailability).where(DriverAvailability.id == availability_id)
    )
    availability = result.scalar_one_or_none()

    if not availability:
        raise HTTPException(status_code=404, detail="Availability not found")

    return availability


@router.put("/availability/{availability_id}", response_model=AvailabilityResponse)
async def update_availability(
    availability_id: int,
    availability_update: AvailabilityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an availability slot"""

    result = await db.execute(
        select(DriverAvailability).where(DriverAvailability.id == availability_id)
    )
    db_availability = result.scalar_one_or_none()

    if not db_availability:
        raise HTTPException(status_code=404, detail="Availability not found")

    update_data = availability_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_availability, field, value)

    await db.commit()
    await db.refresh(db_availability)

    return db_availability


@router.delete("/availability/{availability_id}", status_code=204)
async def delete_availability(
    availability_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an availability slot"""

    result = await db.execute(
        select(DriverAvailability).where(DriverAvailability.id == availability_id)
    )
    db_availability = result.scalar_one_or_none()

    if not db_availability:
        raise HTTPException(status_code=404, detail="Availability not found")

    await db.delete(db_availability)
    await db.commit()

    return None
