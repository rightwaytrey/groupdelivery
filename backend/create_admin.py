#!/usr/bin/env python3
"""
Create initial admin user for Group Delivery app
Usage: python create_admin.py <username> <email> <password>
"""

import sys
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Setup password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_admin_user(username: str, email: str, password: str):
    """Create an admin user in the database."""

    # Create async engine
    engine = create_async_engine(
        "sqlite+aiosqlite:////app/data/delivery.db",
        echo=False
    )

    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        from app.models.user import User
        from app.database import Base

        # Create tables if they don't exist
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Check if user already exists
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.username == username))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"User '{username}' already exists")
            return False

        # Hash password
        hashed_password = pwd_context.hash(password)

        # Create admin user
        admin_user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            full_name="Administrator",
            is_active=True,
            is_superuser=True
        )

        session.add(admin_user)
        await session.commit()

        print(f"✓ Admin user '{username}' created successfully")
        return True


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python create_admin.py <username> <email> <password>")
        sys.exit(1)

    username = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]

    asyncio.run(create_admin_user(username, email, password))
