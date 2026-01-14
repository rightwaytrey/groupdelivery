#!/usr/bin/env python3
"""
Check if an admin user exists in the database
Returns exit code 0 if admin exists, 1 if not
"""

import sys
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select


async def check_admin_exists():
    """Check if an admin user exists in the database."""

    try:
        # Create async engine with timeout
        engine = create_async_engine(
            "sqlite+aiosqlite:////app/data/delivery.db",
            echo=False,
            connect_args={"timeout": 5}
        )

        # Create session
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        async with async_session() as session:
            from app.models.user import User

            # Check if any admin user exists
            result = await session.execute(
                select(User).where(User.is_superuser == True).limit(1)
            )
            admin_user = result.scalar_one_or_none()

            if admin_user:
                return True
            return False

    except Exception as e:
        # If database or tables don't exist yet, no admin exists
        # Print error to stderr for debugging
        print(f"Note: Could not check admin user (this is normal on first deploy): {type(e).__name__}", file=sys.stderr)
        return False


if __name__ == "__main__":
    admin_exists = asyncio.run(check_admin_exists())
    sys.exit(0 if admin_exists else 1)
