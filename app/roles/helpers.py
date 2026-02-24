def get_role_from_icon_url(url: str) -> str:
    """Extracts the role key name from the associated icon URL"""
    return url.rsplit("/", maxsplit=1)[-1].split(".", maxsplit=1)[0].lower()
