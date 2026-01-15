from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
import io
import csv
from app.database import get_db
from app.models.address import Address
from app.models.driver import Driver
from app.models.user import User
from app.schemas.address import (
    AddressCreate,
    AddressUpdate,
    AddressResponse,
    AddressBulkImport,
)
from app.services.geocoding import geocoding_service
from app.services.csv_import import csv_import_service
from app.services.auth import get_current_active_user

router = APIRouter(prefix="/api/addresses", tags=["addresses"])


@router.post("", response_model=AddressResponse, status_code=201)
async def create_address(
    address: AddressCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new address and automatically geocode it"""

    # Validate preferred_driver_id if provided
    driver_name = None
    if address.preferred_driver_id:
        driver_result = await db.execute(
            select(Driver).where(Driver.id == address.preferred_driver_id)
        )
        driver = driver_result.scalar_one_or_none()
        if not driver:
            raise HTTPException(status_code=400, detail="Preferred driver not found")
        driver_name = driver.name

    # Geocode the address
    lat, lng, status = await geocoding_service.geocode_address(
        street=address.street,
        city=address.city,
        state=address.state,
        postal_code=address.postal_code,
        country=address.country,
    )

    # Create address record
    db_address = Address(
        **address.model_dump(), latitude=lat, longitude=lng, geocode_status=status
    )

    db.add(db_address)
    await db.commit()
    await db.refresh(db_address)

    # Build response with driver name
    response = AddressResponse.model_validate(db_address)
    if driver_name:
        response.preferred_driver_name = driver_name

    return response


@router.get("", response_model=list[AddressResponse])
async def list_addresses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    geocode_status: Optional[str] = Query(None),
    preferred_driver_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List addresses with optional filters"""

    query = select(Address)

    # Apply filters
    if is_active is not None:
        query = query.where(Address.is_active == is_active)

    if geocode_status:
        query = query.where(Address.geocode_status == geocode_status)

    if preferred_driver_id is not None:
        query = query.where(Address.preferred_driver_id == preferred_driver_id)

    # Order by created date descending
    query = query.order_by(Address.created_at.desc())

    # Pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    addresses = result.scalars().all()

    # Build driver name lookup
    driver_ids = [a.preferred_driver_id for a in addresses if a.preferred_driver_id]
    driver_names = {}
    if driver_ids:
        driver_result = await db.execute(
            select(Driver).where(Driver.id.in_(driver_ids))
        )
        for driver in driver_result.scalars().all():
            driver_names[driver.id] = driver.name

    # Build response with driver names
    response = []
    for addr in addresses:
        addr_response = AddressResponse.model_validate(addr)
        if addr.preferred_driver_id and addr.preferred_driver_id in driver_names:
            addr_response.preferred_driver_name = driver_names[addr.preferred_driver_id]
        response.append(addr_response)

    return response


@router.get("/export")
async def export_addresses_csv(
    is_active: Optional[bool] = Query(None),
    geocode_status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Export all addresses as CSV."""

    # Build query with optional filters (matching list_addresses logic)
    query = select(Address)
    if is_active is not None:
        query = query.where(Address.is_active == is_active)
    if geocode_status:
        query = query.where(Address.geocode_status == geocode_status)
    query = query.order_by(Address.created_at.desc())

    result = await db.execute(query)
    addresses = result.scalars().all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header (compatible with import format plus extra fields)
    writer.writerow([
        'ID',
        'Street',
        'City',
        'State',
        'Postal Code',
        'Country',
        'Recipient Name',
        'Phone',
        'Notes',
        'Service Time (min)',
        'Preferred Time Start',
        'Preferred Time End',
        'Preferred Driver ID',
        'Latitude',
        'Longitude',
        'Geocode Status',
        'Is Active',
        'Created At',
        'Updated At'
    ])

    # Write address rows
    for address in addresses:
        writer.writerow([
            address.id,
            address.street,
            address.city,
            address.state or '',
            address.postal_code or '',
            address.country or '',
            address.recipient_name or '',
            address.phone or '',
            address.notes or '',
            address.service_time_minutes or '',
            address.preferred_time_start or '',
            address.preferred_time_end or '',
            address.preferred_driver_id or '',
            address.latitude or '',
            address.longitude or '',
            address.geocode_status or '',
            'Yes' if address.is_active else 'No',
            address.created_at.isoformat() if address.created_at else '',
            address.updated_at.isoformat() if address.updated_at else ''
        ])

    # Prepare response
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"addresses_{timestamp}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{address_id}", response_model=AddressResponse)
async def get_address(
    address_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a single address by ID"""

    result = await db.execute(select(Address).where(Address.id == address_id))
    address = result.scalar_one_or_none()

    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    # Build response with driver name
    response = AddressResponse.model_validate(address)
    if address.preferred_driver_id:
        driver_result = await db.execute(
            select(Driver).where(Driver.id == address.preferred_driver_id)
        )
        driver = driver_result.scalar_one_or_none()
        if driver:
            response.preferred_driver_name = driver.name

    return response


@router.put("/{address_id}", response_model=AddressResponse)
async def update_address(
    address_id: int,
    address_update: AddressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an existing address"""

    result = await db.execute(select(Address).where(Address.id == address_id))
    db_address = result.scalar_one_or_none()

    if not db_address:
        raise HTTPException(status_code=404, detail="Address not found")

    # Update fields
    update_data = address_update.model_dump(exclude_unset=True)

    # Validate preferred_driver_id if being updated
    driver_name = None
    if "preferred_driver_id" in update_data:
        if update_data["preferred_driver_id"] is not None:
            driver_result = await db.execute(
                select(Driver).where(Driver.id == update_data["preferred_driver_id"])
            )
            driver = driver_result.scalar_one_or_none()
            if not driver:
                raise HTTPException(status_code=400, detail="Preferred driver not found")
            driver_name = driver.name

    # If address fields changed, re-geocode
    address_fields = {"street", "city", "state", "postal_code", "country"}
    if any(field in update_data for field in address_fields):
        # Get current or updated values
        street = update_data.get("street", db_address.street)
        city = update_data.get("city", db_address.city)
        state = update_data.get("state", db_address.state)
        postal_code = update_data.get("postal_code", db_address.postal_code)
        country = update_data.get("country", db_address.country)

        lat, lng, status = await geocoding_service.geocode_address(
            street=street,
            city=city,
            state=state,
            postal_code=postal_code,
            country=country,
        )

        update_data["latitude"] = lat
        update_data["longitude"] = lng
        update_data["geocode_status"] = status

    # Apply updates
    for field, value in update_data.items():
        setattr(db_address, field, value)

    await db.commit()
    await db.refresh(db_address)

    # Build response with driver name
    response = AddressResponse.model_validate(db_address)
    if driver_name:
        response.preferred_driver_name = driver_name
    elif db_address.preferred_driver_id:
        # Fetch driver name if not already loaded
        driver_result = await db.execute(
            select(Driver).where(Driver.id == db_address.preferred_driver_id)
        )
        driver = driver_result.scalar_one_or_none()
        if driver:
            response.preferred_driver_name = driver.name

    return response


@router.delete("/{address_id}", status_code=204)
async def delete_address(
    address_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an address permanently"""

    result = await db.execute(select(Address).where(Address.id == address_id))
    db_address = result.scalar_one_or_none()

    if not db_address:
        raise HTTPException(status_code=404, detail="Address not found")

    await db.delete(db_address)
    await db.commit()

    return None


@router.delete("", status_code=204)
async def delete_all_addresses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete all addresses permanently"""

    result = await db.execute(select(Address))
    addresses = result.scalars().all()

    for address in addresses:
        await db.delete(address)

    await db.commit()

    return None


@router.post("/geocode/{address_id}", response_model=AddressResponse)
async def re_geocode_address(
    address_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Re-geocode a single address"""

    result = await db.execute(select(Address).where(Address.id == address_id))
    db_address = result.scalar_one_or_none()

    if not db_address:
        raise HTTPException(status_code=404, detail="Address not found")

    # Geocode
    lat, lng, status = await geocoding_service.geocode_address(
        street=db_address.street,
        city=db_address.city,
        state=db_address.state,
        postal_code=db_address.postal_code,
        country=db_address.country,
    )

    db_address.latitude = lat
    db_address.longitude = lng
    db_address.geocode_status = status

    await db.commit()
    await db.refresh(db_address)

    return db_address


@router.post("/import", response_model=AddressBulkImport)
async def import_addresses_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Import addresses from CSV file"""

    # Validate file type
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        # Parse CSV
        valid_rows, parse_errors = await csv_import_service.parse_csv(file)

        # Geocode and save valid rows
        created_ids = []
        geocode_errors = []

        for row in valid_rows:
            row_num = row.pop("_row_number")

            try:
                # Geocode
                lat, lng, status = await geocoding_service.geocode_address(
                    street=row["street"],
                    city=row["city"],
                    state=row.get("state"),
                    postal_code=row.get("postal_code"),
                    country=row.get("country", "USA"),
                )

                # Create address
                db_address = Address(
                    **row, latitude=lat, longitude=lng, geocode_status=status
                )
                db.add(db_address)
                await db.flush()
                created_ids.append(db_address.id)

            except Exception as e:
                geocode_errors.append({"row": row_num, "error": str(e)})

        await db.commit()

        # Combine all errors
        all_errors = parse_errors + geocode_errors

        return AddressBulkImport(
            total_rows=len(valid_rows) + len(parse_errors),
            successful=len(created_ids),
            failed=len(all_errors),
            errors=all_errors,
            created_ids=created_ids,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
