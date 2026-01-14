#!/usr/bin/env python3
"""
Create a default admin user with credentials: admin / admin123456
IMPORTANT: Change these credentials after first login!
"""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import User
from app.services.auth import get_password_hash


async def create_default_admin():
    async with AsyncSessionLocal() as db:
        # Check if any users exist
        result = await db.execute(select(User))
        existing_users = result.scalars().all()

        if existing_users:
            print("Users already exist. Skipping admin creation.")
            print(f"Found {len(existing_users)} existing user(s)")
            return

        # Create default admin user
        username = "admin"
        password = "admin123456"
        email = "admin@localhost"

        hashed_password = get_password_hash(password)
        admin_user = User(
            username=username,
            email=email,
            full_name="System Administrator",
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=True
        )

        db.add(admin_user)
        await db.commit()

        print("=" * 60)
        print("✓ Default admin user created!")
        print("=" * 60)
        print(f"Username: {username}")
        print(f"Password: {password}")
        print()
        print("⚠️  IMPORTANT: Change these credentials immediately after login!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(create_default_admin())
