"""
Migration script to add preferred_driver_id column to addresses table
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.database import engine


async def run_migration():
    """Add preferred_driver_id column to addresses table"""

    migration_sql = """
    -- Add the preferred_driver_id column
    ALTER TABLE addresses ADD COLUMN preferred_driver_id INTEGER;

    -- Note: SQLite does not support adding foreign key constraints after table creation
    -- Foreign key will be enforced by SQLAlchemy relationship
    """

    print("Running migration: Add preferred_driver_id to addresses table")

    try:
        async with engine.begin() as conn:
            # Check if column already exists
            result = await conn.execute(
                "PRAGMA table_info(addresses)"
            )
            columns = [row[1] for row in result.fetchall()]

            if 'preferred_driver_id' in columns:
                print("✓ Column 'preferred_driver_id' already exists. Skipping migration.")
                return

            # Add the column
            await conn.execute(
                "ALTER TABLE addresses ADD COLUMN preferred_driver_id INTEGER"
            )

        print("✓ Migration completed successfully!")
        print("  - Added column: preferred_driver_id (INTEGER, nullable)")
        print("  - Note: Foreign key constraint will be enforced by SQLAlchemy")

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_migration())
