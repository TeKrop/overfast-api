"""Abstract API Parser module"""
from abc import abstractmethod

from app.common.helpers import read_csv_data_file
from app.config import settings

from .abstract_parser import AbstractParser


class CSVParser(AbstractParser):
    """CSV Parser class used to define generic behavior for parsers used
    to extract data from local CSV files.
    """

    # Timeout to use for every CSV-based data
    timeout = settings.csv_cache_timeout

    # Name of CSV file to retrieve (without extension), also
    # used as a sub-folder name for storing related static files
    filename: str

    async def retrieve_and_parse_data(self) -> None:
        """Method used to retrieve data from CSV file and storing
        it into self.data attribute
        """

        # Read the CSV file
        self.csv_data = read_csv_data_file(f"{self.filename}.csv")

        # Parse the data
        self.data = self.parse_data()

        # Update the Parser Cache
        self.cache_manager.update_parser_cache(self.cache_key, self.data, self.timeout)

    @abstractmethod
    def parse_data(self) -> dict | list[dict]:
        """Main submethod of the parser, mainly doing the parsing of CSV data and
        returning a dict, which will be cached and used by the API. Can
        raise an error if there is an issue when parsing the data.
        """

    def get_static_url(self, key: str, extension: str = "jpg") -> str:
        """Method used to retrieve the URL of a local static file"""
        return f"{settings.app_base_url}/static/{self.filename}/{key}.{extension}"
