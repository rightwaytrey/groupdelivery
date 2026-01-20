from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime
import json
import io
import csv
import traceback
import logging

logger = logging.getLogger(__name__)

from ..database import get_db
from ..models import Address, Driver, DeliveryDay, Route, RouteStop
from ..models.user import User
from ..schemas.route import (
    OptimizationRequest,
    OptimizationResult,
    DroppedAddressDetail,
    DeliveryDay as DeliveryDaySchema,
    Route as RouteSchema
)
from ..services.osrm import osrm_service
from ..services.vrp_solver import VRPSolver, format_time, parse_time
from ..services.auth import get_current_active_user
from ..config import settings

router = APIRouter(prefix="/api/optimize", tags=["optimization"])


# Route colors for map visualization
ROUTE_COLORS = [
    "#3B82F6",  # Blue
    "#EF4444",  # Red
    "#10B981",  # Green
    "#F59E0B",  # Amber
    "#8B5CF6",  # Purple
    "#EC4899",  # Pink
    "#14B8A6",  # Teal
    "#F97316",  # Orange
]


@router.post("", response_model=OptimizationResult)
async def optimize_routes(
    request: OptimizationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Optimize delivery routes for a given date.

    This endpoint:
    1. Fetches addresses and drivers
    2. Gets distance matrix from OSRM
    3. Runs VRP solver with time windows
    4. Creates DeliveryDay, Routes, and RouteStops
    5. Gets route geometries from OSRM
    """

    print(f"=== OPTIMIZATION REQUEST RECEIVED ===", flush=True)
    print(f"Date: {request.date}", flush=True)
    print(f"Addresses: {len(request.address_ids)}, Drivers: {len(request.driver_ids)}", flush=True)

    logger.info(f"=== Starting optimization for date: {request.date} ===")
    logger.info(f"Addresses: {len(request.address_ids)}, Drivers: {len(request.driver_ids)}")

    # Validate addresses exist and have coordinates
    result = await db.execute(
        select(Address).where(
            Address.id.in_(request.address_ids),
            Address.is_active == True,
            Address.latitude.isnot(None),
            Address.longitude.isnot(None)
        )
    )
    addresses = list(result.scalars().all())

    if len(addresses) < len(request.address_ids):
        raise HTTPException(
            status_code=400,
            detail=f"Some addresses not found or don't have coordinates. Found {len(addresses)} of {len(request.address_ids)}"
        )

    # Validate drivers exist and are active
    result = await db.execute(
        select(Driver).where(
            Driver.id.in_(request.driver_ids),
            Driver.is_active == True
        )
    )
    drivers = list(result.scalars().all())

    if len(drivers) != len(request.driver_ids):
        raise HTTPException(
            status_code=400,
            detail=f"Some drivers not found or inactive. Found {len(drivers)} of {len(request.driver_ids)}"
        )

    if len(drivers) == 0:
        raise HTTPException(status_code=400, detail="At least one driver is required")

    # Build driver ID to vehicle index mapping for preferred driver constraints
    driver_id_to_vehicle_idx = {driver.id: idx for idx, driver in enumerate(drivers)}
    driver_ids_in_request = set(driver_id_to_vehicle_idx.keys())

    # Build gender-based driver index lists
    male_driver_indices = [idx for idx, driver in enumerate(drivers) if driver.gender == 'male']
    female_driver_indices = [idx for idx, driver in enumerate(drivers) if driver.gender == 'female']

    # Always use default depot location
    depot_lat = settings.default_depot_latitude
    depot_lon = settings.default_depot_longitude
    depot_address = settings.default_depot_address

    # Determine which drivers will end at home
    drivers_ending_at_home = {}
    for driver in drivers:
        if request.driver_constraints and driver.id in request.driver_constraints:
            if request.driver_constraints[driver.id].end_at_home:
                if driver.home_latitude and driver.home_longitude:
                    drivers_ending_at_home[driver.id] = (driver.home_latitude, driver.home_longitude)
                    logger.info(f"Driver {driver.name} (ID {driver.id}) will end at home: {driver.home_address}")
                    print(f"Driver {driver.name} (ID {driver.id}) will end at home: {driver.home_address}", flush=True)
                else:
                    # Driver wants to end at home but has no home address
                    raise HTTPException(
                        status_code=400,
                        detail=f"Driver {driver.name} has 'end at home' enabled but no home address configured"
                    )

    logger.info(f"Drivers ending at home: {list(drivers_ending_at_home.keys())}")
    print(f"Drivers ending at home: {list(drivers_ending_at_home.keys())}", flush=True)

    # Build locations list: depot first, then addresses, then home locations
    locations = [(depot_lat, depot_lon)]  # Index 0 = depot
    address_map = {}  # Map location index to address
    for i, addr in enumerate(addresses):
        locations.append((addr.latitude, addr.longitude))
        address_map[i + 1] = addr  # +1 because depot is at index 0

    # Collect and validate preferred driver constraints
    preferred_driver_constraints = {}
    preferred_driver_errors = []
    gender_preference_errors = []

    for location_idx, addr in address_map.items():
        allowed_vehicles = None

        # Priority 1: Specific preferred driver
        if addr.preferred_driver_id is not None:
            if addr.preferred_driver_id in driver_ids_in_request:
                vehicle_idx = driver_id_to_vehicle_idx[addr.preferred_driver_id]
                allowed_vehicles = [vehicle_idx]
            else:
                # Track addresses with preferred drivers not in the selection
                result = await db.execute(
                    select(Driver).where(Driver.id == addr.preferred_driver_id)
                )
                preferred_driver = result.scalar_one_or_none()
                preferred_driver_errors.append({
                    'address_id': addr.id,
                    'recipient_name': addr.recipient_name or 'Unknown',
                    'street': addr.street,
                    'preferred_driver_id': addr.preferred_driver_id,
                    'preferred_driver_name': preferred_driver.name if preferred_driver else 'Unknown'
                })

        # Priority 2: Gender preference (only if no specific driver)
        elif addr.prefers_male_driver and not addr.prefers_female_driver:
            if not male_driver_indices:
                gender_preference_errors.append({
                    'address_id': addr.id,
                    'recipient_name': addr.recipient_name or 'Unknown',
                    'street': addr.street,
                    'preference': 'male driver',
                    'message': 'No male drivers available in selection'
                })
            else:
                allowed_vehicles = male_driver_indices
        elif addr.prefers_female_driver and not addr.prefers_male_driver:
            if not female_driver_indices:
                gender_preference_errors.append({
                    'address_id': addr.id,
                    'recipient_name': addr.recipient_name or 'Unknown',
                    'street': addr.street,
                    'preference': 'female driver',
                    'message': 'No female drivers available in selection'
                })
            else:
                allowed_vehicles = female_driver_indices
        # If both or neither checked: no constraint

        if allowed_vehicles:
            preferred_driver_constraints[location_idx] = allowed_vehicles

    # Fail early if any addresses have preferred drivers not in the selection
    if preferred_driver_errors:
        error_details = {
            'message': 'Some addresses have preferred drivers that are not included in the selected drivers',
            'addresses': preferred_driver_errors
        }
        logger.error(f"Preferred driver validation failed: {error_details}")
        raise HTTPException(status_code=400, detail=error_details)

    # Fail if any addresses have gender preferences that cannot be satisfied
    if gender_preference_errors:
        error_details = {
            'message': 'Some addresses require a driver gender not available in selected drivers',
            'addresses': gender_preference_errors
        }
        logger.error(f"Gender preference validation failed: {error_details}")
        raise HTTPException(status_code=400, detail=error_details)

    # Add home locations to the end of locations list
    # These will be mandatory final stops in routes
    home_location_indices = {}  # Map driver_id -> location index
    driver_home_locations = {}  # Map driver_id -> (lat, lon)
    for driver_id, home_coords in drivers_ending_at_home.items():
        home_idx = len(locations)
        home_location_indices[driver_id] = home_idx
        driver_home_locations[driver_id] = home_coords
        locations.append(home_coords)
        logger.info(f"Added home location for driver {driver_id} at index {home_idx}")
        print(f"Added home location for driver {driver_id} at index {home_idx}", flush=True)

    # Get distance matrix from OSRM
    logger.info(f"Fetching distance matrix for {len(locations)} locations from OSRM...")
    try:
        distance_matrix, duration_matrix = await osrm_service.get_distance_matrix(locations)
        logger.info(f"Successfully fetched distance matrix: {len(distance_matrix)}x{len(distance_matrix[0])} matrix")
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"OSRM distance matrix error:\n{error_details}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get distance matrix from OSRM: {type(e).__name__}: {str(e)}"
        )

    # Set up VRP solver with simple depot-based routing
    # All vehicles start and end at depot (index 0)
    # We'll manually add home locations to route geometries after optimization
    solver = VRPSolver(
        distance_matrix=distance_matrix,
        duration_matrix=duration_matrix,
        num_vehicles=len(drivers),
        depot_index=0
        # Not using vehicle_starts/vehicle_ends to avoid OR-Tools segfaults
    )

    # Set service times for each location
    service_times = [0]  # Depot has 0 service time
    for addr in addresses:
        service_times.append(addr.service_time_minutes or 5)
    # Add zero service time for home locations
    for _ in drivers_ending_at_home:
        service_times.append(0)
    solver.set_service_times(service_times)

    # Set vehicle capacities (max stops per driver)
    # Use constraints from request if provided, otherwise fall back to driver properties
    capacities = []
    for driver in drivers:
        if request.driver_constraints and driver.id in request.driver_constraints:
            constraint = request.driver_constraints[driver.id].max_stops
            capacities.append(constraint if constraint is not None else 15)
        else:
            # Fallback to driver property or default
            capacities.append(driver.max_stops if driver.max_stops else 15)
    solver.set_vehicle_capacities(capacities)

    # Set max route duration per driver
    max_durations = []
    for driver in drivers:
        if request.driver_constraints and driver.id in request.driver_constraints:
            constraint = request.driver_constraints[driver.id].max_route_duration_minutes
            max_durations.append(constraint if constraint is not None else 120)
        else:
            # Fallback to driver property or default
            max_durations.append(driver.max_route_duration_minutes if driver.max_route_duration_minutes else 120)
    solver.set_max_route_durations(max_durations)

    # Calculate per-driver start time offsets
    # Collect all driver start times
    driver_start_times = []
    for driver in drivers:
        driver_start_time = request.start_time  # default to global
        if request.driver_constraints and driver.id in request.driver_constraints:
            constraint_start = request.driver_constraints[driver.id].start_time
            if constraint_start:
                driver_start_time = constraint_start
        driver_start_times.append(driver_start_time)

    # Helper function to convert time string to minutes from midnight
    def time_to_minutes(t: str) -> int:
        parts = t.split(':')
        return int(parts[0]) * 60 + int(parts[1])

    # Find earliest start time to use as base for all calculations
    # This ensures time windows and vehicle offsets are calculated consistently
    earliest_start = min(driver_start_times, key=time_to_minutes)
    earliest_start_minutes = time_to_minutes(earliest_start)

    # Use earliest start as base_time for time window calculations
    base_time = datetime.combine(request.date, datetime.strptime(earliest_start, "%H:%M").time())

    # Calculate vehicle offsets relative to earliest start (all >= 0)
    vehicle_start_offsets = []
    for driver_start_time in driver_start_times:
        offset = time_to_minutes(driver_start_time) - earliest_start_minutes
        vehicle_start_offsets.append(offset)

    solver.set_vehicle_start_offsets(vehicle_start_offsets)

    # Set time windows if addresses have preferred times
    # Use the maximum route duration for the depot window
    max_overall_duration = max(max_durations)
    time_windows = [(0, max_overall_duration)]  # Depot window

    # Note: base_time already defined above for per-driver start time calculations
    for addr in addresses:
        start_min = parse_time(addr.preferred_time_start, base_time) if addr.preferred_time_start else 0
        end_min = parse_time(addr.preferred_time_end, base_time) if addr.preferred_time_end else max_overall_duration
        time_windows.append((start_min, end_min))

    # Add time windows for home locations (no constraints)
    for _ in drivers_ending_at_home:
        time_windows.append((0, max_overall_duration))

    solver.set_time_windows(time_windows)

    # Set mandatory final stops for vehicles ending at home
    # This will force the solver to visit home locations as the last stop before depot
    if home_location_indices:
        mandatory_final_stops = {}
        for i, driver in enumerate(drivers):
            if driver.id in home_location_indices:
                mandatory_final_stops[i] = home_location_indices[driver.id]
        solver.set_vehicle_mandatory_final_stops(mandatory_final_stops)
        logger.info(f"Set mandatory final stops: {mandatory_final_stops}")
        print(f"Set mandatory final stops: {mandatory_final_stops}", flush=True)

    # Apply preferred driver constraints (hard constraint - addresses MUST go to their preferred driver)
    if preferred_driver_constraints:
        solver.set_allowed_vehicles_for_nodes(preferred_driver_constraints)
        logger.info(f"Applied preferred driver constraints for {len(preferred_driver_constraints)} addresses")
        print(f"Applied preferred driver constraints for {len(preferred_driver_constraints)} addresses", flush=True)

    # Validate solver inputs before calling solve to prevent segfaults
    try:
        # Check for empty inputs
        if len(addresses) == 0:
            raise HTTPException(status_code=400, detail="No addresses to optimize")
        if len(drivers) == 0:
            raise HTTPException(status_code=400, detail="No drivers available")

        # Check distance matrix
        if len(distance_matrix) != len(locations):
            raise HTTPException(
                status_code=500,
                detail=f"Distance matrix size mismatch: {len(distance_matrix)} vs {len(locations)} locations"
            )

        # Check for invalid coordinates
        for i, loc in enumerate(locations):
            if loc[0] is None or loc[1] is None or not (-90 <= loc[0] <= 90) or not (-180 <= loc[1] <= 180):
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid coordinates at location {i}: {loc}"
                )

        logger.info(f"Starting VRP solver with {len(addresses)} addresses, {len(drivers)} drivers, {len(locations)} total locations")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pre-solver validation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")

    # Solve VRP
    try:
        solution = solver.solve(time_limit_seconds=request.time_limit_seconds)
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"VRP Solver exception:\n{error_details}")
        raise HTTPException(
            status_code=500,
            detail=f"Solver error: {type(e).__name__}: {str(e)}"
        )

    if not solution:
        raise HTTPException(status_code=500, detail="No solution found. Try increasing time limit or reducing constraints.")

    # Log route solution details
    logger.info(f"VRP Solution: {solution['num_routes']} routes found")
    for i, route_data in enumerate(solution['routes']):
        stop_indices = [stop['location_index'] for stop in route_data['stops']]
        logger.info(f"Route {i+1} (vehicle {route_data['vehicle_id']}): stops at location indices {stop_indices}")
        print(f"Route {i+1} (vehicle {route_data['vehicle_id']}): stops at location indices {stop_indices}", flush=True)

    # Analyze dropped addresses and build detailed diagnostics
    dropped_address_details = []
    try:
        if solution['dropped_nodes']:
            # Filter out depot (index 0), everything else is a delivery address
            dropped_address_nodes = [
                node_idx for node_idx in solution['dropped_nodes']
                if node_idx != 0
            ]

            if dropped_address_nodes:
                # Get diagnostics from solver
                node_analysis = solver.analyze_dropped_nodes(dropped_address_nodes)

                # Build detailed messages for each dropped address
                for node_idx in dropped_address_nodes:
                    address = address_map[node_idx]
                    analysis = node_analysis[node_idx]

                    # Build human-readable reason
                    reasons = []
                    if 'narrow_time_window' in analysis['reasons']:
                        tw_str = f"{address.preferred_time_start or 'none'}-{address.preferred_time_end or 'none'}"
                        reasons.append(f"Time window too restrictive ({tw_str})")
                    if 'high_service_time' in analysis['reasons']:
                        reasons.append(f"Service time too long ({address.service_time_minutes} min)")
                    if 'capacity_or_duration' in analysis['reasons']:
                        reasons.append("All drivers at capacity or route duration exceeded")

                    dropped_address_details.append(DroppedAddressDetail(
                        address_id=address.id,
                        recipient_name=address.recipient_name or 'Unknown',
                        street=address.street,
                        reason=' | '.join(reasons) if reasons else 'Capacity or duration constraints',
                        time_window=f"{address.preferred_time_start or 'none'} - {address.preferred_time_end or 'none'}",
                        service_time_minutes=address.service_time_minutes
                    ))
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error analyzing dropped addresses:\n{error_details}")
        logger.error(f"Dropped nodes: {solution.get('dropped_nodes', [])}")
        logger.error(f"Address map keys: {list(address_map.keys())}")
        logger.error(f"Home location start idx: {len(addresses) + 1}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing dropped addresses: {type(e).__name__}: {str(e)}"
        )

    # Create or update DeliveryDay
    result = await db.execute(
        select(DeliveryDay).where(DeliveryDay.date == request.date)
    )
    delivery_day = result.scalar_one_or_none()

    if delivery_day:
        # Delete existing routes for this day
        result = await db.execute(
            select(Route).where(Route.delivery_day_id == delivery_day.id)
        )
        existing_routes = result.scalars().all()
        for route in existing_routes:
            await db.delete(route)
    else:
        # Create new delivery day
        delivery_day = DeliveryDay(
            date=request.date,
            depot_latitude=depot_lat,
            depot_longitude=depot_lon,
            depot_address=depot_address
        )
        db.add(delivery_day)

    # Update delivery day stats
    delivery_day.status = "optimized"
    delivery_day.total_stops = len(addresses) - len(solution['dropped_nodes'])
    delivery_day.total_drivers = solution['num_routes']
    delivery_day.total_distance_km = solution['total_distance_km']
    delivery_day.total_duration_minutes = solution['total_duration_minutes']
    delivery_day.updated_at = datetime.utcnow()

    await db.flush()

    # Create routes
    created_routes = []
    for i, route_data in enumerate(solution['routes']):
        driver = drivers[route_data['vehicle_id']]
        color = ROUTE_COLORS[i % len(ROUTE_COLORS)]

        # Get route geometry from OSRM
        # If driver ends at home, replace final depot return with home location
        route_locations = [locations[stop['location_index']] for stop in route_data['stops']]

        if driver.id in driver_home_locations:
            # Replace the last stop (depot return) with home location
            # route_locations is: [depot, stop1, stop2, ..., depot]
            # We want: [depot, stop1, stop2, ..., home] (END - no depot return)
            home_coords = driver_home_locations[driver.id]
            route_locations[-1] = home_coords
            logger.info(f"Route ends at home for driver {driver.name}, removed depot return")
            print(f"Route ends at home for driver {driver.name}, removed depot return", flush=True)

        try:
            geometry_data = await osrm_service.get_route_geometry(route_locations)
            route_geometry = json.dumps(geometry_data['geometry'])
            # If route ends at home, use OSRM's actual distance/duration
            # instead of OR-Tools values (which include depot return)
            if driver.id in driver_home_locations:
                actual_distance_km = geometry_data['distance_km']
                actual_duration_minutes = geometry_data['duration_minutes']
                logger.info(f"Using OSRM distance/duration for home-ending route: {actual_distance_km:.2f}km, {actual_duration_minutes:.2f}min")
                print(f"Using OSRM distance/duration: {actual_distance_km:.2f}km, {actual_duration_minutes:.2f}min", flush=True)
            else:
                actual_distance_km = route_data['distance_km']
                actual_duration_minutes = route_data['duration_minutes']
        except Exception as e:
            print(f"Warning: Failed to get route geometry: {e}")
            route_geometry = None
            actual_distance_km = route_data['distance_km']
            actual_duration_minutes = route_data['duration_minutes']

        # Calculate start/end times
        # Use earliest start time as base for formatting (cumulative time is relative to earliest start)
        # Convert earliest_start to minutes from midnight for proper time formatting
        earliest_start_offset = time_to_minutes(earliest_start)

        start_minutes = route_data['stops'][0]['time_minutes']
        # If route ends at home, recalculate end time based on actual duration
        if driver.id in driver_home_locations:
            end_minutes = int(start_minutes + actual_duration_minutes)
        else:
            end_minutes = route_data['stops'][-1]['time_minutes']

        start_time = format_time(int(start_minutes), earliest_start_offset)
        end_time = format_time(int(end_minutes), earliest_start_offset)

        route = Route(
            delivery_day_id=delivery_day.id,
            driver_id=driver.id,
            route_number=i + 1,
            color=color,
            total_stops=len(route_data['stops']) - 2,  # Exclude depot start/end
            total_distance_km=actual_distance_km,
            total_duration_minutes=actual_duration_minutes,
            route_geometry=route_geometry,
            start_time=start_time,
            end_time=end_time
        )
        db.add(route)
        await db.flush()

        # Create route stops
        for j, stop_data in enumerate(route_data['stops']):
            location_idx = stop_data['location_index']

            # Skip depot (index 0) and home locations (indices after addresses)
            # Only process actual delivery addresses
            if location_idx == 0 or location_idx not in address_map:
                continue

            address = address_map[location_idx]
            time_minutes = stop_data['time_minutes']

            # Calculate distance/duration from previous stop
            if j > 0:
                prev_idx = route_data['stops'][j - 1]['location_index']
                dist_km = distance_matrix[prev_idx][location_idx]
                dur_min = duration_matrix[prev_idx][location_idx]
            else:
                dist_km = 0.0
                dur_min = 0.0

            arrival_time = format_time(time_minutes, earliest_start_offset)
            departure_time = format_time(time_minutes + address.service_time_minutes, earliest_start_offset)

            route_stop = RouteStop(
                route_id=route.id,
                address_id=address.id,
                sequence=j,
                estimated_arrival=arrival_time,
                estimated_departure=departure_time,
                distance_from_previous_km=dist_km,
                duration_from_previous_minutes=dur_min
            )
            db.add(route_stop)

        created_routes.append(route)

    await db.commit()

    # Re-query routes with eager loading of relationships
    result = await db.execute(
        select(Route)
        .where(Route.delivery_day_id == delivery_day.id)
        .options(selectinload(Route.stops))
    )
    created_routes = list(result.scalars().all())

    # Filter dropped nodes to only include actual addresses (not depot)
    dropped_address_ids = [
        address_map[idx].id for idx in solution['dropped_nodes']
        if idx != 0
    ]

    # Build response
    return OptimizationResult(
        delivery_day_id=delivery_day.id,
        date=delivery_day.date,
        status=delivery_day.status,
        total_routes=len(created_routes),
        total_stops=delivery_day.total_stops,
        total_distance_km=delivery_day.total_distance_km,
        total_duration_minutes=delivery_day.total_duration_minutes,
        routes=[RouteSchema.model_validate(r) for r in created_routes],
        dropped_addresses=dropped_address_ids,
        dropped_address_details=dropped_address_details,
        message=f"Successfully optimized {len(addresses)} addresses into {len(created_routes)} routes"
    )


@router.get("/delivery-days", response_model=List[DeliveryDaySchema])
async def list_delivery_days(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all delivery days."""
    result = await db.execute(
        select(DeliveryDay).order_by(DeliveryDay.date.desc())
    )
    return result.scalars().all()


@router.get("/delivery-days/{date}", response_model=DeliveryDaySchema)
async def get_delivery_day(
    date: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get delivery day by date."""
    result = await db.execute(
        select(DeliveryDay).where(DeliveryDay.date == date)
    )
    delivery_day = result.scalar_one_or_none()

    if not delivery_day:
        raise HTTPException(status_code=404, detail="Delivery day not found")

    return delivery_day


@router.get("/routes/{delivery_day_id}", response_model=List[RouteSchema])
async def get_routes_for_day(
    delivery_day_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all routes for a delivery day."""
    result = await db.execute(
        select(Route)
        .where(Route.delivery_day_id == delivery_day_id)
        .options(selectinload(Route.stops))
    )
    return result.scalars().all()


@router.get("/routes/{route_id}/export")
async def export_route_csv(
    route_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Export a single route as CSV."""
    result = await db.execute(
        select(Route)
        .where(Route.id == route_id)
        .options(selectinload(Route.stops))
    )
    route = result.scalar_one_or_none()

    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    # Get driver info
    driver_result = await db.execute(select(Driver).where(Driver.id == route.driver_id))
    driver = driver_result.scalar_one_or_none()

    # Get delivery day info
    day_result = await db.execute(select(DeliveryDay).where(DeliveryDay.id == route.delivery_day_id))
    delivery_day = day_result.scalar_one_or_none()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'Route Number',
        'Driver Name',
        'Driver Phone',
        'Delivery Date',
        'Stop Sequence',
        'Recipient Name',
        'Phone',
        'Street Address',
        'City',
        'State',
        'Postal Code',
        'Estimated Arrival',
        'Estimated Departure',
        'Service Time (min)',
        'Distance from Previous (km)',
        'Duration from Previous (min)',
        'Delivery Notes',
        'Latitude',
        'Longitude'
    ])

    # Write route stops
    for stop in route.stops:
        # Get address details
        addr_result = await db.execute(select(Address).where(Address.id == stop.address_id))
        address = addr_result.scalar_one_or_none()

        if address:
            writer.writerow([
                route.route_number,
                driver.name if driver else '',
                driver.phone if driver else '',
                delivery_day.date if delivery_day else '',
                stop.sequence,
                address.recipient_name or '',
                address.phone or '',
                address.street,
                address.city,
                address.state or '',
                address.postal_code or '',
                stop.estimated_arrival or '',
                stop.estimated_departure or '',
                address.service_time_minutes,
                f"{stop.distance_from_previous_km:.2f}",
                f"{stop.duration_from_previous_minutes:.1f}",
                address.notes or '',
                address.latitude or '',
                address.longitude or ''
            ])

    # Prepare response
    output.seek(0)
    filename = f"route_{route.route_number}_{delivery_day.date if delivery_day else 'unknown'}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.delete("/delivery-days/{delivery_day_id}")
async def delete_delivery_day(
    delivery_day_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a delivery day and all its routes."""
    result = await db.execute(
        select(DeliveryDay).where(DeliveryDay.id == delivery_day_id)
    )
    delivery_day = result.scalar_one_or_none()

    if not delivery_day:
        raise HTTPException(status_code=404, detail="Delivery day not found")

    await db.delete(delivery_day)
    await db.commit()

    return {"message": "Delivery day deleted successfully"}


@router.get("/delivery-days/{delivery_day_id}/export")
async def export_delivery_day_csv(
    delivery_day_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Export all routes for a delivery day as CSV."""
    # Get delivery day
    day_result = await db.execute(select(DeliveryDay).where(DeliveryDay.id == delivery_day_id))
    delivery_day = day_result.scalar_one_or_none()

    if not delivery_day:
        raise HTTPException(status_code=404, detail="Delivery day not found")

    # Get all routes with stops
    routes_result = await db.execute(
        select(Route)
        .where(Route.delivery_day_id == delivery_day_id)
        .options(selectinload(Route.stops))
    )
    routes = list(routes_result.scalars().all())

    if not routes:
        raise HTTPException(status_code=404, detail="No routes found for this delivery day")

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'Route Number',
        'Driver Name',
        'Driver Phone',
        'Driver Vehicle',
        'Delivery Date',
        'Stop Sequence',
        'Recipient Name',
        'Phone',
        'Street Address',
        'City',
        'State',
        'Postal Code',
        'Estimated Arrival',
        'Estimated Departure',
        'Service Time (min)',
        'Distance from Previous (km)',
        'Duration from Previous (min)',
        'Delivery Notes',
        'Latitude',
        'Longitude'
    ])

    # Write all route stops
    for route in routes:
        # Get driver info
        driver_result = await db.execute(select(Driver).where(Driver.id == route.driver_id))
        driver = driver_result.scalar_one_or_none()

        for stop in route.stops:
            # Get address details
            addr_result = await db.execute(select(Address).where(Address.id == stop.address_id))
            address = addr_result.scalar_one_or_none()

            if address:
                writer.writerow([
                    route.route_number,
                    driver.name if driver else '',
                    driver.phone if driver else '',
                    driver.vehicle_type if driver else '',
                    delivery_day.date,
                    stop.sequence,
                    address.recipient_name or '',
                    address.phone or '',
                    address.street,
                    address.city,
                    address.state or '',
                    address.postal_code or '',
                    stop.estimated_arrival or '',
                    stop.estimated_departure or '',
                    address.service_time_minutes,
                    f"{stop.distance_from_previous_km:.2f}",
                    f"{stop.duration_from_previous_minutes:.1f}",
                    address.notes or '',
                    address.latitude or '',
                    address.longitude or ''
                ])

    # Prepare response
    output.seek(0)
    filename = f"delivery_routes_{delivery_day.date}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
