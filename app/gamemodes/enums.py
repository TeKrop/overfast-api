from enum import StrEnum

from app.helpers import read_csv_data_file

# Dynamically create the MapGamemode enum by using the CSV File
gamemodes_data = read_csv_data_file("gamemodes")
MapGamemode = StrEnum(
    "MapGamemode",
    {
        gamemode["key"].upper().replace("-", "_"): gamemode["key"]
        for gamemode in gamemodes_data
    },
)
MapGamemode.__doc__ = "Maps gamemodes keys"
