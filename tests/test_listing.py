from datetime import UTC, datetime, timedelta

import pytest

from app.models import Task


def test_empty_list_defaults(client):
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_filters_total_order_and_page_boundaries(client, application):
    stamp = datetime(2026, 1, 1, tzinfo=UTC)
    with application.state.session_factory() as session:
        session.add_all(
            [
                Task(id=1, title="first", completed=False, created_at=stamp),
                Task(id=2, title="tie", completed=True, created_at=stamp),
                Task(id=3, title="older", completed=False, created_at=stamp - timedelta(days=1)),
                Task(id=4, title="newest", completed=True, created_at=stamp + timedelta(days=1)),
            ]
        )
        session.commit()
    for query, expected in [
        ("", [4, 2, 1, 3]),
        ("completed=true&", [4, 2]),
        ("completed=false&", [1, 3]),
    ]:
        for offset in range(len(expected) + 2):
            result = client.get(f"/api/tasks?{query}limit=1&offset={offset}").json()
            assert result["total"] == len(expected)
            assert result["limit"] == 1
            assert result["offset"] == offset
            assert [item["id"] for item in result["items"]] == expected[offset : offset + 1]
    assert len(client.get("/api/tasks?limit=100").json()["items"]) == 4


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=101",
        "limit=-1",
        "limit=abc",
        "offset=-1",
        "offset=1.5",
        "completed=invalid",
    ],
)
def test_invalid_query(client, query):
    assert client.get(f"/api/tasks?{query}").status_code == 422


def test_delete_and_subsequent_operations(client):
    task = client.post("/api/tasks", json={"title": "remove"}).json()
    path = f"/api/tasks/{task['id']}"
    response = client.delete(path)
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(path).status_code == 404
    assert client.patch(path, json={"completed": True}).status_code == 404
    assert client.delete(path).status_code == 404
    assert client.get("/api/tasks").json()["total"] == 0


def test_delete_missing(client):
    assert client.delete("/api/tasks/999").status_code == 404
