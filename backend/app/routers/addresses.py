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

    return db_address


@router.get("", response_model=list[AddressResponse])
async def list_addresses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    geocode_status: Optional[str] = Query(None),
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

    # Order by created date descending
    query = query.order_by(Address.created_at.desc())

    # Pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    addresses = result.scalars().all()

    return addresses


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

    return address


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

    return db_address


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
