"""CSV reader for domain static data files"""

import csv
from pathlib import Path


class CSVReader:
    """Reads CSV data files bundled with the application."""

    @staticmethod
    def read_csv_file(filename: str) -> list[dict[str, str]]:
        """Read a CSV file by name (without extension) from the data/ directory."""
        csv_path = Path(__file__).parent / "data" / f"{filename}.csv"
        with csv_path.open(encoding="utf-8") as csv_file:
            return list(csv.DictReader(csv_file, delimiter=","))
