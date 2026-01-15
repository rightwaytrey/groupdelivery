import csv
import io
import re
from typing import Tuple
from fastapi import UploadFile


class CsvImportService:
    """Service for parsing and validating CSV imports"""

    REQUIRED_COLUMNS = {"street", "city"}
    OPTIONAL_COLUMNS = {
        "state",
        "postal_code",
        "country",
        "recipient_name",
        "phone",
        "notes",
        "service_time_minutes",
        "preferred_time_start",
        "preferred_time_end",
        "preferred_driver_id",
    }

    async def parse_csv(self, file: UploadFile) -> Tuple[list[dict], list[dict]]:
        """
        Parse and validate CSV file.

        Returns:
            Tuple of (valid_rows, errors)
        """
        content = await file.read()

        # Try to decode with different encodings
        try:
            decoded = content.decode("utf-8-sig")  # Handle BOM
        except UnicodeDecodeError:
            try:
                decoded = content.decode("latin-1")
            except UnicodeDecodeError:
                raise ValueError(
                    "Unable to decode CSV file. Please use UTF-8 encoding."
                )

        reader = csv.DictReader(io.StringIO(decoded))

        # Normalize column names (lowercase, strip spaces, replace spaces with underscores)
        if reader.fieldnames:
            reader.fieldnames = [
                col.strip().lower().replace(" ", "_") for col in reader.fieldnames
            ]

        # Validate required columns exist
        if not self.REQUIRED_COLUMNS.issubset(set(reader.fieldnames or [])):
            missing = self.REQUIRED_COLUMNS - set(reader.fieldnames or [])
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        valid_rows = []
        errors = []

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
            try:
                validated = self._validate_row(row)
                validated["_row_number"] = row_num
                valid_rows.append(validated)
            except ValueError as e:
                errors.append({"row": row_num, "error": str(e)})

        return valid_rows, errors

    def _validate_row(self, row: dict) -> dict:
        """Validate and clean a single row"""
        cleaned = {}

        # Required fields
        street = row.get("street", "").strip()
        city = row.get("city", "").strip()

        if not street:
            raise ValueError("Street is required and cannot be empty")
        if not city:
            raise ValueError("City is required and cannot be empty")

        cleaned["street"] = street
        cleaned["city"] = city

        # Optional string fields
        cleaned["state"] = row.get("state", "").strip() or None
        cleaned["postal_code"] = row.get("postal_code", "").strip() or None
        cleaned["country"] = row.get("country", "").strip() or "USA"
        cleaned["recipient_name"] = row.get("recipient_name", "").strip() or None
        cleaned["phone"] = row.get("phone", "").strip() or None
        cleaned["notes"] = row.get("notes", "").strip() or None

        # Numeric field - service time
        service_time = row.get("service_time_minutes", "5").strip()
        try:
            cleaned["service_time_minutes"] = (
                int(service_time) if service_time else 5
            )
            if cleaned["service_time_minutes"] < 1 or cleaned["service_time_minutes"] > 60:
                cleaned["service_time_minutes"] = 5
        except ValueError:
            cleaned["service_time_minutes"] = 5

        # Time window fields
        cleaned["preferred_time_start"] = (
            row.get("preferred_time_start", "").strip() or None
        )
        cleaned["preferred_time_end"] = (
            row.get("preferred_time_end", "").strip() or None
        )

        # Preferred driver ID (optional integer)
        preferred_driver_id = row.get("preferred_driver_id", "").strip()
        if preferred_driver_id:
            try:
                cleaned["preferred_driver_id"] = int(preferred_driver_id)
            except ValueError:
                raise ValueError(f"Invalid preferred_driver_id: {preferred_driver_id}")
        else:
            cleaned["preferred_driver_id"] = None

        return cleaned


# Singleton instance
csv_import_service = CsvImportService()


class DriverCsvImportService:
    """Service for parsing and validating driver CSV imports"""

    REQUIRED_COLUMNS = {"name"}
    OPTIONAL_COLUMNS = {
        "email",
        "phone",
        "vehicle_type",
        "max_stops",
        "max_route_duration_minutes",
        "home_address",
    }

    async def parse_csv(self, file: UploadFile) -> Tuple[list[dict], list[dict]]:
        """
        Parse and validate CSV file.

        Returns:
            Tuple of (valid_rows, errors)
        """
        content = await file.read()

        # Try to decode with different encodings
        try:
            decoded = content.decode("utf-8-sig")  # Handle BOM
        except UnicodeDecodeError:
            try:
                decoded = content.decode("latin-1")
            except UnicodeDecodeError:
                raise ValueError(
                    "Unable to decode CSV file. Please use UTF-8 encoding."
                )

        reader = csv.DictReader(io.StringIO(decoded))

        # Normalize column names (lowercase, strip spaces, replace spaces with underscores)
        if reader.fieldnames:
            reader.fieldnames = [
                col.strip().lower().replace(" ", "_") for col in reader.fieldnames
            ]

        # Validate required columns exist
        if not self.REQUIRED_COLUMNS.issubset(set(reader.fieldnames or [])):
            missing = self.REQUIRED_COLUMNS - set(reader.fieldnames or [])
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        valid_rows = []
        errors = []

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
            try:
                validated = self._validate_row(row)
                validated["_row_number"] = row_num
                valid_rows.append(validated)
            except ValueError as e:
                errors.append({"row": row_num, "error": str(e)})

        return valid_rows, errors

    def _validate_row(self, row: dict) -> dict:
        """Validate and clean a single row"""
        cleaned = {}

        # Required field
        name = row.get("name", "").strip()
        if not name:
            raise ValueError("Name is required and cannot be empty")
        cleaned["name"] = name

        # Optional string fields
        cleaned["email"] = row.get("email", "").strip() or None
        cleaned["phone"] = row.get("phone", "").strip() or None
        cleaned["vehicle_type"] = row.get("vehicle_type", "").strip() or None
        cleaned["home_address"] = row.get("home_address", "").strip() or None

        # Validate email format if provided
        if cleaned["email"]:
            email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if not re.match(email_pattern, cleaned["email"]):
                raise ValueError(f"Invalid email format: {cleaned['email']}")

        # Numeric field - max_stops
        max_stops = row.get("max_stops", "15").strip()
        try:
            cleaned["max_stops"] = int(max_stops) if max_stops else 15
            if cleaned["max_stops"] < 1:
                raise ValueError("max_stops must be a positive integer")
        except ValueError:
            raise ValueError(f"Invalid max_stops value: {max_stops}")

        # Numeric field - max_route_duration_minutes
        max_duration = row.get("max_route_duration_minutes", "240").strip()
        try:
            cleaned["max_route_duration_minutes"] = int(max_duration) if max_duration else 240
            if cleaned["max_route_duration_minutes"] < 1:
                raise ValueError("max_route_duration_minutes must be a positive integer")
        except ValueError:
            raise ValueError(f"Invalid max_route_duration_minutes value: {max_duration}")

        return cleaned


# Singleton instance
driver_csv_import_service = DriverCsvImportService()
