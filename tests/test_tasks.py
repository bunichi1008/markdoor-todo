from datetime import UTC, datetime


def test_create_and_read_task(client):
    before = datetime.now(UTC)
    response = client.post("/api/tasks", json={"title": "面接準備", "description": "APIを作る"})
    assert response.status_code == 201
    task = response.json()
    assert isinstance(task["id"], int)
    assert task["id"] > 0
    assert task["title"] == "面接準備"
    assert task["description"] == "APIを作る"
    assert task["completed"] is False
    for field in ("created_at", "updated_at"):
        timestamp = datetime.fromisoformat(task[field])
        assert timestamp.utcoffset().total_seconds() == 0
        assert before <= timestamp <= datetime.now(UTC)
    fetched = client.get(f"/api/tasks/{task['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == task


def test_create_minimal_task(client):
    first = client.post("/api/tasks", json={"title": "first"}).json()
    second = client.post("/api/tasks", json={"title": "second"}).json()
    assert first["description"] is None
    assert first["completed"] is False
    assert second["id"] > first["id"]


def test_get_missing_task(client):
    assert client.get("/api/tasks/999").status_code == 404
