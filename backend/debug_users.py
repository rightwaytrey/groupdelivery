#!/usr/bin/env python3
"""
Debug user accounts and test password verification
Usage: python debug_users.py [username] [password]
"""

import sys
import sqlite3
from passlib.context import CryptContext

# Setup password hashing - using argon2 to match the auth service
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

db_path = "/app/data/delivery.db"


def debug_users(test_username=None, test_password=None):
    """Show all users and optionally test password verification."""

    try:
        conn = sqlite3.connect(db_path, timeout=5)
        cursor = conn.cursor()

        # Get all users
        cursor.execute("""
            SELECT id, username, email, is_active, is_superuser, hashed_password
            FROM users
        """)
        users = cursor.fetchall()

        if not users:
            print("No users found in database")
            conn.close()
            return

        print(f"\n{'='*80}")
        print(f"Users in database ({len(users)} total):")
        print(f"{'='*80}\n")

        for user_id, username, email, is_active, is_superuser, hashed_pass in users:
            print(f"ID: {user_id}")
            print(f"Username: {username}")
            print(f"Email: {email}")
            print(f"Is Active: {is_active} (type: {type(is_active)})")
            print(f"Is Superuser: {is_superuser} (type: {type(is_superuser)})")
            print(f"Password Hash: {hashed_pass[:50]}...")
            print(f"Hash Algorithm: {'argon2' if hashed_pass.startswith('$argon2') else 'bcrypt' if hashed_pass.startswith('$2b$') else 'unknown'}")

            # Test password if provided
            if test_username and username == test_username and test_password:
                print(f"\n--- Testing password for {username} ---")
                try:
                    valid = pwd_context.verify(test_password, hashed_pass)
                    print(f"Password verification: {'✓ VALID' if valid else '✗ INVALID'}")
                except Exception as e:
                    print(f"Password verification error: {e}")

            print(f"\n{'-'*80}\n")

        conn.close()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) == 3:
        debug_users(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 1:
        debug_users()
    else:
        print("Usage: python debug_users.py [username] [password]")
        print("  No args: Show all users")
        print("  With args: Show all users and test password for specific user")
