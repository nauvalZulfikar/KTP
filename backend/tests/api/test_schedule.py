from datetime import datetime

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import TaskRow


def _seed_tasks(session: Session) -> None:
    tasks = [
        TaskRow(
            unique_id=7,
            product_name="Product 2",
            component="C1",
            machine_number="M1",
            quantity_required=4000,
            run_time_per_1000=30.0,
            order_processing_date=datetime(2024, 8, 21),
            promised_delivery_date=datetime(2024, 8, 27),
        ),
        TaskRow(
            unique_id=8,
            product_name="Product 2",
            component="C2",
            machine_number="M2",
            quantity_required=4000,
            run_time_per_1000=30.0,
            order_processing_date=datetime(2024, 8, 21),
            promised_delivery_date=datetime(2024, 8, 27),
        ),
    ]
    session.add_all(tasks)
    session.commit()


def test_run_without_tasks_returns_400(client: TestClient) -> None:
    r = client.post("/schedule/run", json={})
    assert r.status_code == 400
    assert "import data" in r.json()["detail"].lower()


def test_run_creates_assignments(client: TestClient, session: Session) -> None:
    _seed_tasks(session)
    r = client.post("/schedule/run", json={"notes": "first run"})
    assert r.status_code == 201, r.text
    run = r.json()
    assert run["id"] > 0
    assert run["notes"] == "first run"

    detail = client.get(f"/runs/{run['id']}").json()
    assert len(detail["assignments"]) == 2
    start_times = [a["start_time"] for a in detail["assignments"]]
    assert start_times == sorted(start_times)


def test_list_runs_descending(client: TestClient, session: Session) -> None:
    _seed_tasks(session)
    r1 = client.post("/schedule/run", json={}).json()
    r2 = client.post("/schedule/run", json={"notes": "second"}).json()
    runs = client.get("/runs").json()
    assert [r["id"] for r in runs] == [r2["id"], r1["id"]]


def test_get_missing_run_404(client: TestClient) -> None:
    assert client.get("/runs/9999").status_code == 404
    assert client.get("/runs/9999/metrics").status_code == 404


def test_metrics_has_expected_shape(client: TestClient, session: Session) -> None:
    _seed_tasks(session)
    run = client.post("/schedule/run", json={}).json()
    metrics = client.get(f"/runs/{run['id']}/metrics").json()
    assert set(metrics.keys()) == {
        "machine_utilization",
        "component_waiting_days",
        "product_waiting_days",
        "late_counts",
    }
    assert "M1" in metrics["machine_utilization"]
    assert 0 <= metrics["machine_utilization"]["M1"] <= 1
