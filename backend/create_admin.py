#!/usr/bin/env python3
"""
Create an admin user for the Group Delivery Optimizer application.
Run this script to create the first user account.
"""
import asyncio
import sys
import getpass
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import User
from app.services.auth import get_password_hash


async def create_admin_user():
    print("=" * 60)
    print("Create Admin User for Group Delivery Optimizer")
    print("=" * 60)
    print()

    # Get user input
    print("Enter details for the admin user:")
    username = input("Username: ").strip()
    if not username or len(username) < 3:
        print("Error: Username must be at least 3 characters")
        sys.exit(1)

    email = input("Email: ").strip()
    if not email or "@" not in email:
        print("Error: Invalid email address")
        sys.exit(1)

    full_name = input("Full Name (optional): ").strip() or None

    password = getpass.getpass("Password (min 8 characters): ")
    if len(password) < 8:
        print("Error: Password must be at least 8 characters")
        sys.exit(1)

    password_confirm = getpass.getpass("Confirm Password: ")
    if password != password_confirm:
        print("Error: Passwords do not match")
        sys.exit(1)

    # Create user in database
    async with AsyncSessionLocal() as db:
        # Check if username exists
        result = await db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            print(f"\nError: Username '{username}' already exists")
            sys.exit(1)

        # Check if email exists
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            print(f"\nError: Email '{email}' already registered")
            sys.exit(1)

        # Create user
        hashed_password = get_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=True  # First user is always superuser
        )

        db.add(new_user)
        await db.commit()

    print("\n" + "=" * 60)
    print("✓ Admin user created successfully!")
    print("=" * 60)
    print(f"Username: {username}")
    print(f"Email: {email}")
    print("\nYou can now log in to the application with these credentials.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(create_admin_user())
