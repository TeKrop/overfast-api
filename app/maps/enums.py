from enum import StrEnum

from app.helpers import read_csv_data_file

# Dynamically create the MapKey enum by using the CSV File
maps_data = read_csv_data_file("maps")
MapKey = StrEnum(
    "MapKey",
    {
        map_data["key"].upper().replace("-", "_"): map_data["key"]
        for map_data in maps_data
    },
)
MapKey.__doc__ = "Map keys used to identify Overwatch maps in general"
