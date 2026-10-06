from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.main import create_app
from app.models import Task


def test_startup_initializes_empty_database(application, client):
    assert "tasks" in inspect(application.state.engine).get_table_names()
    assert client.get("/openapi.json").status_code == 200


def test_application_databases_are_isolated(tmp_path):
    first = create_app(f"sqlite:///{tmp_path / 'first.sqlite3'}")
    second = create_app(f"sqlite:///{tmp_path / 'second.sqlite3'}")
    with TestClient(first), TestClient(second):
        with first.state.session_factory() as session:
            session.add(Task(title="first database"))
            session.commit()
        with second.state.session_factory() as session:
            assert session.query(Task).count() == 0
