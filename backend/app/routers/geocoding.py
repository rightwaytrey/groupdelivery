from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import httpx
from app.config import settings
import asyncio
import time

router = APIRouter(prefix="/api/geocoding", tags=["geocoding"])

# Simple in-memory rate limiter
_last_request_time = 0.0


@router.get("/search")
async def search_addresses(
    q: str = Query(..., min_length=3, description="Search query"),
    limit: int = Query(5, ge=1, le=10, description="Max results"),
    countrycodes: Optional[str] = Query("us", description="Country codes to search"),
):
    """
    Search for addresses using Nominatim.
    Proxies requests to respect rate limits and provide consistent API.
    """
    global _last_request_time

    # Rate limiting: ensure at least 1 second between requests
    current_time = time.time()
    time_since_last = current_time - _last_request_time
    if time_since_last < settings.geocoding_rate_limit:
        await asyncio.sleep(settings.geocoding_rate_limit - time_since_last)

    _last_request_time = time.time()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": q,
                    "format": "json",
                    "addressdetails": 1,
                    "limit": limit,
                    "countrycodes": countrycodes,
                },
                headers={
                    "User-Agent": settings.geocoding_user_agent,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Geocoding service error")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="Geocoding service unavailable")
