"""Parser Helpers module"""
from overfastapi.config import BLIZZARD_HOST


def get_full_url(url: str) -> str:
    """Get full URL from extracted URL. If URL begins with /, we use the
    blizzard host to get the full URL"""
    return f"{BLIZZARD_HOST}{url}" if url.startswith("/") else url
