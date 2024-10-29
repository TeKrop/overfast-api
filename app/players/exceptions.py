from app.exceptions import OverfastError


class SearchDataRetrievalError(OverfastError):
    """Generic search data retrieval Exception (namecards, titles, etc.)"""

    message = "Error while retrieving search data"
