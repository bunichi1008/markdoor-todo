import pytest
from sqlalchemy import func, select

from app.models import Task


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": ""},
        {"title": " \t\n　"},
        {"title": "x" * 201},
        {"title": None},
        {"title": 123},
        {"title": True},
        {"title": []},
        {"title": "ok", "description": "x" * 5001},
        {"title": "ok", "description": 1},
        {"title": "ok", "completed": "true"},
        {"title": "ok", "completed": 1},
        {"title": "ok", "completed": None},
        {"title": "ok", "unknown": "value"},
        {"title": "ok", "id": 7},
        {"title": "ok", "created_at": "2026-01-01T00:00:00Z"},
        {"title": "ok", "updated_at": "2026-01-01T00:00:00Z"},
    ],
)
def test_invalid_create_does_not_change_database(client, application, payload):
    existing = client.post("/api/tasks", json={"title": "existing"}).json()
    assert client.post("/api/tasks", json=payload).status_code == 422
    assert client.get(f"/api/tasks/{existing['id']}").json() == existing
    with application.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Task)) == 1


def test_create_boundaries_and_trim(client):
    response = client.post(
        "/api/tasks", json={"title": "　 " + "あ" * 200 + " \n", "description": "文" * 5000}
    )
    assert response.status_code == 201
    task = client.get(f"/api/tasks/{response.json()['id']}").json()
    assert task["title"] == "あ" * 200
    assert task["description"] == "文" * 5000


def test_malformed_json(client):
    assert (
        client.post(
            "/api/tasks", content="{", headers={"Content-Type": "application/json"}
        ).status_code
        == 422
    )
