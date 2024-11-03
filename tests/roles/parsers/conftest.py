import pytest

from app.roles.parsers.roles_parser import RolesParser


@pytest.fixture(scope="package")
def roles_parser() -> RolesParser:
    return RolesParser()
