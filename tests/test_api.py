"""API tests. These don't need a real database:
the connection is replaced with a dummy and the query functions are faked.
"""
import pytest
from fastapi.testclient import TestClient

from api import db, queries
from api.main import app

FAKE_ROWS = [
    {
        "id": 1,
        "name": "Playground A",
        "amenity_type": "Playground",
        "park_name": "Victoria Park",
        "geometry": {"type": "Point", "coordinates": [-104.6110, 50.4470]},
        "distance_m": 45.2,
    },
    {
        "id": 2,
        "name": "Washroom",
        "amenity_type": "Washroom",
        "park_name": "Victoria Park",
        "geometry": {"type": "Point", "coordinates": [-104.6120, 50.4480]},
        "distance_m": 130.0,
    },
]


def fake_conn():
    yield None


@pytest.fixture
def client():
    app.dependency_overrides[db.get_conn] = fake_conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health_when_db_is_down(client, monkeypatch):
    monkeypatch.setattr(db, "check_connection", lambda: False)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "database unavailable", "database": False}


def test_amenity_types(client, monkeypatch):
    monkeypatch.setattr(
        queries, "amenity_types", lambda conn: [{"amenity_type": "Playground", "count": 3}]
    )
    response = client.get("/api/amenities/types")
    assert response.status_code == 200
    assert response.json()[0]["amenity_type"] == "Playground"


def test_list_amenities_returns_geojson(client, monkeypatch):
    monkeypatch.setattr(queries, "list_amenities", lambda conn, **kwargs: FAKE_ROWS)
    response = client.get("/api/amenities")
    body = response.json()

    assert response.status_code == 200
    assert body["type"] == "FeatureCollection"
    assert body["count"] == 2
    assert body["features"][0]["geometry"]["type"] == "Point"


def test_list_amenities_passes_filters(client, monkeypatch):
    seen = {}

    def fake_list(conn, amenity_type=None, bbox=None, limit=None):
        seen.update(amenity_type=amenity_type, bbox=bbox, limit=limit)
        return []

    monkeypatch.setattr(queries, "list_amenities", fake_list)
    client.get("/api/amenities?type=Playground&bbox=-104.7,50.4,-104.5,50.5&limit=10")

    assert seen == {"amenity_type": "Playground", "bbox": (-104.7, 50.4, -104.5, 50.5), "limit": 10}


def test_bad_bbox_gives_400(client):
    response = client.get("/api/amenities?bbox=1,2,3")
    assert response.status_code == 400


def test_near(client, monkeypatch):
    monkeypatch.setattr(queries, "amenities_near", lambda conn, lon, lat, radius, **kwargs: FAKE_ROWS)
    response = client.get("/api/amenities/near?lat=50.4475&lon=-104.6107&radius_m=500")
    body = response.json()

    assert response.status_code == 200
    assert body["features"][0]["properties"]["distance_m"] == 45.2


@pytest.mark.parametrize(
    "query",
    [
        "lat=50.4475&lon=-104.6107&radius_m=0",       # radius must be more than 0
        "lat=50.4475&lon=-104.6107&radius_m=99999",   # radius too big
        "lat=50.4475&lon=104.6107",                   # missing minus sign on longitude
        "lon=-104.6107",                              # lat missing
    ],
)
def test_near_rejects_bad_input(client, query):
    response = client.get(f"/api/amenities/near?{query}")
    assert response.status_code == 422


def test_nearest_limit(client, monkeypatch):
    monkeypatch.setattr(queries, "nearest_amenities", lambda conn, lon, lat, **kwargs: FAKE_ROWS[:1])
    response = client.get("/api/amenities/nearest?lat=50.4475&lon=-104.6107&limit=1")
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_get_amenity_not_found(client, monkeypatch):
    monkeypatch.setattr(queries, "get_amenity", lambda conn, amenity_id: None)
    response = client.get("/api/amenities/999")
    assert response.status_code == 404


def test_swagger_docs_load(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").json()["info"]["title"] == "Regina Park Amenities API"
