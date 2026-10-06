import pytest


def test_partial_update_preserves_omitted_fields_and_creation_time(client):
    original = client.post("/api/tasks", json={"title": "original", "description": "keep"}).json()
    path = f"/api/tasks/{original['id']}"
    response = client.patch(path, json={"title": " updated "})
    assert response.status_code == 200
    changed = response.json()
    assert changed["title"] == "updated"
    assert changed["description"] == "keep"
    assert changed["completed"] is False
    assert changed["created_at"] == original["created_at"]
    assert changed["updated_at"] > original["updated_at"]
    assert client.get(path).json() == changed
    assert client.patch(path, json={"description": None}).json()["description"] is None
    assert client.get(path).json()["description"] is None


def test_completed_is_explicit_and_idempotent(client):
    task = client.post("/api/tasks", json={"title": "state"}).json()
    path = f"/api/tasks/{task['id']}"
    for completed in (True, True, False, False):
        response = client.patch(path, json={"completed": completed})
        assert response.status_code == 200
        assert response.json()["completed"] is completed
        assert client.get(path).json()["completed"] is completed
        assert response.json()["created_at"] == task["created_at"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": None},
        {"title": "　 \n"},
        {"title": "x" * 201},
        {"title": 1},
        {"completed": None},
        {"completed": 1},
        {"completed": "false"},
        {"description": 1},
        {"description": "x" * 5001},
        {"extra": True},
        {"id": 2},
        {"created_at": "2026-01-01T00:00:00Z"},
        {"updated_at": "2026-01-01T00:00:00Z"},
        {"title": "would change", "completed": None},
    ],
)
def test_invalid_update_keeps_original(client, payload):
    task = client.post("/api/tasks", json={"title": "keep", "description": "keep"}).json()
    path = f"/api/tasks/{task['id']}"
    assert client.patch(path, json=payload).status_code == 422
    assert client.get(path).json() == task


def test_update_boundaries(client):
    task = client.post("/api/tasks", json={"title": "a"}).json()
    payload = {"title": "あ" * 200, "description": "文" * 5000, "completed": True}
    path = f"/api/tasks/{task['id']}"
    assert client.patch(path, json=payload).status_code == 200
    assert all(client.get(path).json()[key] == value for key, value in payload.items())


def test_update_missing(client):
    assert client.patch("/api/tasks/999", json={"title": "missing"}).status_code == 404
