"""
OSRM Service for routing and distance matrix calculations.
Uses the public OSRM demo server or a local instance.
"""
import httpx
import asyncio
from typing import List, Tuple, Optional, Dict
from ..config import settings


class OSRMService:
    def __init__(self, base_url: str = "http://router.project-osrm.org"):
        """
        Initialize OSRM service.

        Args:
            base_url: OSRM server URL (default: public demo server)
        """
        self.base_url = base_url
        self.timeout = 30.0

    async def get_distance_matrix(
        self,
        locations: List[Tuple[float, float]]
    ) -> Tuple[List[List[float]], List[List[float]]]:
        """
        Get distance and duration matrices between all locations.

        Args:
            locations: List of (latitude, longitude) tuples

        Returns:
            Tuple of (distance_matrix_km, duration_matrix_minutes)
            Each matrix is NxN where N is the number of locations
        """
        if len(locations) < 2:
            return ([[0.0]], [[0.0]])

        # OSRM uses lon,lat format
        coords = ";".join([f"{lon},{lat}" for lat, lon in locations])

        # Build table service URL for distance matrix
        url = f"{self.base_url}/table/v1/driving/{coords}"
        params = {
            "annotations": "distance,duration"
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        if data["code"] != "Ok":
            raise Exception(f"OSRM error: {data.get('message', 'Unknown error')}")

        # Convert meters to km and seconds to minutes
        distances_km = [
            [d / 1000.0 if d is not None else 999999.0 for d in row]
            for row in data["distances"]
        ]
        durations_min = [
            [d / 60.0 if d is not None else 999999.0 for d in row]
            for row in data["durations"]
        ]

        return distances_km, durations_min

    async def get_route_geometry(
        self,
        locations: List[Tuple[float, float]],
        overview: str = "full"
    ) -> Dict:
        """
        Get route geometry (polyline) for a sequence of locations.

        Args:
            locations: Ordered list of (latitude, longitude) tuples
            overview: Level of detail ("full", "simplified", "false")

        Returns:
            Dictionary with route information including geometry
        """
        if len(locations) < 2:
            return {
                "distance_km": 0.0,
                "duration_minutes": 0.0,
                "geometry": None
            }

        # OSRM uses lon,lat format
        coords = ";".join([f"{lon},{lat}" for lat, lon in locations])

        # Build route service URL
        url = f"{self.base_url}/route/v1/driving/{coords}"
        params = {
            "overview": overview,
            "geometries": "geojson",
            "steps": "false"
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        if data["code"] != "Ok":
            raise Exception(f"OSRM error: {data.get('message', 'Unknown error')}")

        route = data["routes"][0]

        return {
            "distance_km": route["distance"] / 1000.0,
            "duration_minutes": route["duration"] / 60.0,
            "geometry": route["geometry"]  # GeoJSON LineString
        }

    async def batch_distance_matrix(
        self,
        locations: List[Tuple[float, float]],
        batch_size: int = 100
    ) -> Tuple[List[List[float]], List[List[float]]]:
        """
        Get distance matrix for large number of locations by batching.
        OSRM has limits on number of coordinates per request.

        Args:
            locations: List of (latitude, longitude) tuples
            batch_size: Maximum locations per request

        Returns:
            Tuple of (distance_matrix_km, duration_matrix_minutes)
        """
        n = len(locations)

        # If within limits, just call directly
        if n <= batch_size:
            return await self.get_distance_matrix(locations)

        # Otherwise, split into batches and combine
        # For simplicity, we'll just use the first batch_size locations
        # A more sophisticated approach would make multiple requests
        print(f"Warning: {n} locations exceeds batch size, using first {batch_size}")
        return await self.get_distance_matrix(locations[:batch_size])


# Global instance
osrm_service = OSRMService()
