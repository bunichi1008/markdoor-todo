"""Measure listing/filtering through TestClient using a disposable 1,000-row SQLite DB."""

import json
import os
import platform
import sqlite3
import statistics
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.main import create_app
from app.models import Task


def main():
    results = {}
    with TemporaryDirectory(prefix="markdoor-benchmark-") as directory:
        application = create_app(f"sqlite:///{Path(directory) / 'benchmark.sqlite3'}")
        with TestClient(application) as client:
            with application.state.session_factory() as session:
                session.add_all(Task(title=f"Task {i}", completed=bool(i % 2)) for i in range(1000))
                session.commit()
            for name, query, total in [
                ("all", "limit=50&offset=0", 1000),
                ("incomplete", "completed=false&limit=50&offset=0", 500),
                ("completed", "completed=true&limit=50&offset=0", 500),
                ("last_page", "limit=50&offset=950", 1000),
            ]:
                samples = []
                for attempt in range(55):
                    start = perf_counter()
                    response = client.get(f"/api/tasks?{query}")
                    duration = (perf_counter() - start) * 1000
                    assert response.status_code == 200
                    assert response.json()["total"] == total
                    assert len(response.json()["items"]) == 50
                    if attempt >= 5:
                        samples.append(duration)
                results[name] = {
                    "median_ms": round(statistics.median(samples), 3),
                    "p95_ms": round(sorted(samples)[47], 3),
                    "max_ms": round(max(samples), 3),
                }
    print(
        json.dumps(
            {
                "measured_at_jst": datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(),
                "python": platform.python_version(),
                "platform": platform.platform(),
                "logical_cpus": os.cpu_count(),
                "sqlite": sqlite3.sqlite_version,
                "rows": 1000,
                "samples_per_query": 50,
                "warmup_per_query": 5,
                "method": (
                    "TestClient; full ASGI response including JSON; no TCP or browser rendering"
                ),
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
