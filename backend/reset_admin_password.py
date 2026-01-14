#!/usr/bin/env python3
"""
Reset admin user password
Usage: python reset_admin_password.py <username> <new_password>
"""

import sys
import sqlite3
from datetime import datetime
from passlib.context import CryptContext

# Setup password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db_path = "/app/data/delivery.db"


def reset_password(username: str, new_password: str):
    """Reset password for a user."""

    try:
        conn = sqlite3.connect(db_path, timeout=5)
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT id, is_superuser FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if not user:
            print(f"Error: User '{username}' not found")
            conn.close()
            return False

        user_id, is_superuser = user
        role = "admin" if is_superuser else "user"

        # Hash new password
        hashed_password = pwd_context.hash(new_password)
        now = datetime.utcnow().isoformat()

        # Update password
        cursor.execute("""
            UPDATE users
            SET hashed_password = ?, updated_at = ?
            WHERE id = ?
        """, (hashed_password, now, user_id))

        conn.commit()
        conn.close()

        print(f"✓ Password reset successfully for {role} user '{username}'")
        return True

    except Exception as e:
        print(f"Error resetting password: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python reset_admin_password.py <username> <new_password>")
        sys.exit(1)

    username = sys.argv[1]
    new_password = sys.argv[2]

    if len(new_password) < 8:
        print("Error: Password must be at least 8 characters")
        sys.exit(1)

    success = reset_password(username, new_password)
    sys.exit(0 if success else 1)
