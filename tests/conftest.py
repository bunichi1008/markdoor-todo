import pytest
from fastapi.testclient import TestClient

from app.main import create_app


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
