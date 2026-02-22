from enum import StrEnum

from app.adapters.csv import CSVReader

# Dynamically create the MapKey enum by using the CSV File
maps_data = CSVReader.read_csv_file("maps")
MapKey = StrEnum(
    "MapKey",
    {
        map_data["key"].upper().replace("-", "_"): map_data["key"]
        for map_data in maps_data
    },
)
MapKey.__doc__ = "Map keys used to identify Overwatch maps in general"
