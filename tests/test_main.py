"""Smoke tests for the app's top-level routes.

Both the home dashboard (``/``) and its JSON counterpart (``/api/v1/dashboard/``)
run aggregation queries, so they need a real database — hence the container-backed
``client`` fixture rather than a bare ``TestClient``. Exercised here against an
empty schema, which drives the dashboard's zero-data path.
"""


def test_read_main(client):
    # The home page is now the dashboard; on an empty DB it renders its
    # zero-data state rather than 500-ing.
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_dashboard_api_empty(client):
    response = client.get("/api/v1/dashboard/")
    assert response.status_code == 200
    body = response.json()
    assert body["counts"] == {
        "students": 0,
        "teachers": 0,
        "groups": 0,
        "disciplines": 0,
        "grades": 0,
    }
    assert body["overall_average"] is None
    # Every point on the 1–12 scale is present even with no grades.
    assert [b["grade"] for b in body["grade_distribution"]] == list(range(1, 13))
    assert all(b["count"] == 0 for b in body["grade_distribution"])
