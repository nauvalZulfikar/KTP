from datetime import datetime

from fastapi.testclient import TestClient

TASK_BODY = {
    "unique_id": 1,
    "product_name": "Product 1",
    "order_processing_date": "2024-08-21T00:00:00",
    "promised_delivery_date": "2024-08-28T00:00:00",
    "quantity_required": 9000,
    "component": "C1",
    "machine_number": "M1",
    "run_time_per_1000": 10.0,
}


def test_list_tasks_empty(client: TestClient) -> None:
    r = client.get("/tasks")
    assert r.status_code == 200
    assert r.json() == []


def test_create_and_get_task(client: TestClient) -> None:
    r = client.post("/tasks", json=TASK_BODY)
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["id"] > 0
    assert created["unique_id"] == 1

    got = client.get(f"/tasks/{created['id']}")
    assert got.status_code == 200
    assert got.json()["product_name"] == "Product 1"


def test_patch_task(client: TestClient) -> None:
    created = client.post("/tasks", json=TASK_BODY).json()
    r = client.patch(f"/tasks/{created['id']}", json={"quantity_required": 5000})
    assert r.status_code == 200
    assert r.json()["quantity_required"] == 5000


def test_delete_task(client: TestClient) -> None:
    created = client.post("/tasks", json=TASK_BODY).json()
    r = client.delete(f"/tasks/{created['id']}")
    assert r.status_code == 204
    r2 = client.get(f"/tasks/{created['id']}")
    assert r2.status_code == 404


def test_get_missing_task_404(client: TestClient) -> None:
    assert client.get("/tasks/9999").status_code == 404
