from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import asyncio
from typing import Optional, Tuple
from app.config import settings


class GeocodingService:
    """Service for geocoding addresses using Nominatim"""

    def __init__(self):
        self.geolocator = Nominatim(user_agent=settings.geocoding_user_agent)
        # Rate limit to respect Nominatim policy
        self.geocode = RateLimiter(
            self.geolocator.geocode,
            min_delay_seconds=settings.geocoding_rate_limit,
            max_retries=3,
        )

    async def geocode_address(
        self,
        street: str,
        city: str,
        state: Optional[str] = None,
        postal_code: Optional[str] = None,
        country: str = "USA",
    ) -> Tuple[Optional[float], Optional[float], str]:
        """
        Geocode an address to latitude/longitude.

        Returns:
            Tuple of (latitude, longitude, status)
            Status: 'success', 'not_found', 'error'
        """
        # Build address string
        parts = [street, city]
        if state:
            parts.append(state)
        if postal_code:
            parts.append(postal_code)
        parts.append(country)
        address_string = ", ".join(parts)

        try:
            # Run in thread pool to not block async event loop
            loop = asyncio.get_event_loop()
            location = await loop.run_in_executor(
                None, lambda: self.geocode(address_string)
            )

            if location:
                return (location.latitude, location.longitude, "success")
            return (None, None, "not_found")

        except (GeocoderTimedOut, GeocoderServiceError) as e:
            return (None, None, f"error: {str(e)[:100]}")
        except Exception as e:
            return (None, None, f"error: {str(e)[:100]}")

    async def batch_geocode(self, addresses: list[dict]) -> list[dict]:
        """
        Geocode multiple addresses with progress tracking.

        Args:
            addresses: List of dicts with street, city, state, postal_code, country

        Returns:
            List of dicts with added latitude, longitude, geocode_status
        """
        results = []
        for addr in addresses:
            lat, lng, status = await self.geocode_address(**addr)
            results.append(
                {**addr, "latitude": lat, "longitude": lng, "geocode_status": status}
            )
        return results


# Singleton instance
geocoding_service = GeocodingService()
