def get_role_from_icon_url(url: str) -> str:
    """Extracts the role key name from the associated icon URL"""
    return url.split("/")[-1].split(".")[0].lower()
