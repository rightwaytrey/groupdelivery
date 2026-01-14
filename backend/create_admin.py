#!/usr/bin/env python3
"""
Create initial admin user for Group Delivery app
Usage: python create_admin.py <username> <email> <password>
"""

import sys
import sqlite3
from datetime import datetime
from passlib.context import CryptContext

# Setup password hashing - using argon2 to match the auth service
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

db_path = "/app/data/delivery.db"


def create_admin_user(username: str, email: str, password: str):
    """Create an admin user in the database."""

    try:
        conn = sqlite3.connect(db_path, timeout=5)
        cursor = conn.cursor()

        # Create users table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                is_active BOOLEAN NOT NULL DEFAULT 1,
                is_superuser BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL,
                updated_at DATETIME
            )
        """)

        # Check if user already exists
        cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            print(f"User '{username}' already exists")
            conn.close()
            return False

        # Hash password
        hashed_password = pwd_context.hash(password)
        now = datetime.utcnow().isoformat()

        # Insert admin user
        cursor.execute("""
            INSERT INTO users (username, email, hashed_password, full_name, is_active, is_superuser, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, email, hashed_password, "Administrator", True, True, now, now))

        conn.commit()
        conn.close()

        print(f"✓ Admin user '{username}' created successfully")
        return True

    except Exception as e:
        print(f"Error creating admin user: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python create_admin.py <username> <email> <password>")
        sys.exit(1)

    username = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]

    success = create_admin_user(username, email, password)
    sys.exit(0 if success else 1)
