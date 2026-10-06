import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def pytest_addoption(parser):
    parser.addoption("--browser", action="store_true", help="Run real Chromium UI tests")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--browser"):
        for item in items:
            if "browser" in item.keywords:
                item.add_marker(pytest.mark.skip(reason="Enable with --browser"))


@pytest.fixture
def database_url(tmp_path):
    return f"sqlite:///{tmp_path / 'test.sqlite3'}"


@pytest.fixture
def application(database_url):
    return create_app(database_url)


@pytest.fixture
def client(application):
    with TestClient(application) as test_client:
        yield test_client
