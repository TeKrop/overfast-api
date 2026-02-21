from enum import StrEnum

from app.adapters.csv import CSVReader

# Dynamically create the MapGamemode enum by using the CSV File
gamemodes_data = CSVReader.read_csv_file("gamemodes")
MapGamemode = StrEnum(
    "MapGamemode",
    {
        gamemode["key"].upper().replace("-", "_"): gamemode["key"]
        for gamemode in gamemodes_data
    },
)
MapGamemode.__doc__ = "Maps gamemodes keys"
