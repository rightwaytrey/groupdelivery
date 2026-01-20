"""
Migration script to add gender fields to drivers and addresses tables
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.database import engine
from sqlalchemy import text


async def run_migration():
    """Add gender column to drivers and gender preference columns to addresses"""

    print("Running migration: Add gender fields to drivers and addresses tables")

    try:
        async with engine.begin() as conn:
            # Check if columns already exist
            drivers_result = await conn.execute(
                text("PRAGMA table_info(drivers)")
            )
            drivers_columns = [row[1] for row in drivers_result.fetchall()]

            addresses_result = await conn.execute(
                text("PRAGMA table_info(addresses)")
            )
            addresses_columns = [row[1] for row in addresses_result.fetchall()]

            changes_made = []

            # Add gender column to drivers table
            if 'gender' not in drivers_columns:
                await conn.execute(
                    text("ALTER TABLE drivers ADD COLUMN gender VARCHAR(10)")
                )
                changes_made.append("Added column: drivers.gender (VARCHAR(10), nullable)")
            else:
                print("✓ Column 'drivers.gender' already exists. Skipping.")

            # Add prefers_male_driver column to addresses table
            if 'prefers_male_driver' not in addresses_columns:
                await conn.execute(
                    text("ALTER TABLE addresses ADD COLUMN prefers_male_driver BOOLEAN DEFAULT 0")
                )
                changes_made.append("Added column: addresses.prefers_male_driver (BOOLEAN, default=FALSE)")
            else:
                print("✓ Column 'addresses.prefers_male_driver' already exists. Skipping.")

            # Add prefers_female_driver column to addresses table
            if 'prefers_female_driver' not in addresses_columns:
                await conn.execute(
                    text("ALTER TABLE addresses ADD COLUMN prefers_female_driver BOOLEAN DEFAULT 0")
                )
                changes_made.append("Added column: addresses.prefers_female_driver (BOOLEAN, default=FALSE)")
            else:
                print("✓ Column 'addresses.prefers_female_driver' already exists. Skipping.")

        if changes_made:
            print("✓ Migration completed successfully!")
            for change in changes_made:
                print(f"  - {change}")
        else:
            print("✓ All columns already exist. No changes needed.")

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_migration())
