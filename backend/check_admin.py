#!/usr/bin/env python3
"""Check if an admin user exists in the database"""
import sqlite3
import sys

db_path = "/app/data/delivery.db"

try:
    conn = sqlite3.connect(db_path, timeout=2)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE is_superuser = 1 LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    sys.exit(0 if result else 1)
except Exception:
    # If database doesn't exist or query fails, no admin exists
    sys.exit(1)
