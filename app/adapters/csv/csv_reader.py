"""CSV reader adapter for reading static data from CSV files"""

import csv
from pathlib import Path


class CSVReader:
    """Adapter for reading CSV data files"""

    @staticmethod
    def read_csv_file(filename: str) -> list[dict[str, str]]:
        """
        Read a CSV file from app/adapters/csv/data/ directory

        Args:
            filename: Name of the CSV file without extension (e.g., "heroes", "maps", "gamemodes")

        Returns:
            List of dictionaries with CSV rows
        """
        csv_path = Path(__file__).parent / "data" / f"{filename}.csv"
        with csv_path.open(encoding="utf-8") as csv_file:
            return list(csv.DictReader(csv_file, delimiter=","))

    @staticmethod
    def read_csv_file_legacy(filename: str) -> list[dict[str, str]]:
        """
        Legacy method for reading CSV files from old location app/{module}/data/{module}.csv
        This is kept for backward compatibility during migration.

        Args:
            filename: Name of the module/CSV file (e.g., "heroes", "maps", "gamemodes")

        Returns:
            List of dictionaries with CSV rows
        """
        csv_path = Path.cwd() / "app" / filename / "data" / f"{filename}.csv"
        with csv_path.open(encoding="utf-8") as csv_file:
            return list(csv.DictReader(csv_file, delimiter=","))
