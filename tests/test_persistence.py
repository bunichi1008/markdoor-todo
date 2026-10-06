import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.main import create_app


def test_data_survives_new_application_and_connection(database_url):
    with TestClient(create_app(database_url)) as first:
        task = first.post("/api/tasks", json={"title": "persistent"}).json()
        task = first.patch(f"/api/tasks/{task['id']}", json={"completed": True}).json()
    with TestClient(create_app(database_url)) as restarted:
        assert restarted.get(f"/api/tasks/{task['id']}").json() == task
        assert restarted.get("/api/tasks").json()["total"] == 1


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
@pytest.mark.parametrize("error_type", ["database", "unexpected"])
def test_failed_write_rolls_back_and_hides_details(
    client, application, monkeypatch, caplog, operation, error_type
):
    original = client.post("/api/tasks", json={"title": "original"}).json()
    path = f"/api/tasks/{original['id']}"
    rollbacks = []

    class FailingSession(Session):
        def commit(self):
            self.flush()  # Execute real SQL, then fail before COMMIT.
            if error_type == "database":
                raise OperationalError("private SQL", {}, RuntimeError("private detail"))
            raise RuntimeError("private detail")

        def rollback(self):
            rollbacks.append(True)
            super().rollback()

    with monkeypatch.context() as patch:
        patch.setattr(
            application.state,
            "session_factory",
            sessionmaker(
                bind=application.state.engine, class_=FailingSession, expire_on_commit=False
            ),
        )
        with TestClient(application, raise_server_exceptions=False) as failing_client:
            with caplog.at_level(logging.ERROR):
                if operation == "create":
                    response = failing_client.post("/api/tasks", json={"title": "unsaved"})
                elif operation == "update":
                    response = failing_client.patch(path, json={"title": "unsaved"})
                else:
                    response = failing_client.delete(path)
        assert response.status_code == 500
        assert response.json() == {"detail": "処理に失敗しました。時間をおいて再試行してください。"}
        assert "private" not in response.text
        assert rollbacks == [True]
        assert "private detail" in caplog.text
    assert client.get(path).json() == original
    assert client.get("/api/tasks").json()["total"] == 1
    assert client.post("/api/tasks", json={"title": "recovered"}).status_code == 201


def test_database_read_failure_is_logged_and_hidden(client, application, monkeypatch, caplog):
    class UnavailableSession(Session):
        def get(self, *args, **kwargs):
            raise OperationalError("private SQL", {}, RuntimeError("private read failure"))

    monkeypatch.setattr(
        application.state,
        "session_factory",
        sessionmaker(bind=application.state.engine, class_=UnavailableSession),
    )
    with TestClient(application, raise_server_exceptions=False) as failing_client:
        with caplog.at_level(logging.ERROR):
            response = failing_client.get("/api/tasks/1")
    assert response.status_code == 500
    assert "private" not in response.text
    assert response.json()["detail"]
    assert "private read failure" in caplog.text
