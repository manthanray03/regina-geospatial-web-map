"""REST API for Regina park amenities.

Start it from the project folder:
    uvicorn api.main:app --reload

Swagger docs:  http://127.0.0.1:8000/docs
Web map:       http://127.0.0.1:8000/
"""
from pathlib import Path
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from api import db, queries
from api.utils import parse_bbox, to_feature, to_feature_collection

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(
    title="Regina Park Amenities API",
    version="0.1.0",
    description=(
        "Serves City of Regina park amenity points from PostGIS as GeoJSON. "
        "Distances are in metres. Coordinates are WGS 84 (longitude, latitude)."
    ),
)

# Lat/lon limits cover Saskatchewan, so a typo (like a missing minus sign) gets a clear error.
Lat = Annotated[float, Query(ge=49, le=60, description="Latitude, e.g. 50.4475")]
Lon = Annotated[float, Query(ge=-110, le=-101, description="Longitude, e.g. -104.6107")]
AmenityType = Annotated[
    Optional[str],
    Query(alias="type", description="Only return this amenity type (see /api/amenities/types)"),
]


@app.get("/api/health", tags=["status"], summary="Check the API and database")
def health():
    ok = db.check_connection()
    return {"status": "ok" if ok else "database unavailable", "database": ok}


@app.get("/api/amenities/types", tags=["amenities"], summary="List amenity types with counts")
def amenity_types(conn=Depends(db.get_conn)):
    return queries.amenity_types(conn)


@app.get("/api/amenities", tags=["amenities"], summary="All amenities as GeoJSON")
def list_amenities(
    amenity_type: AmenityType = None,
    bbox: Annotated[
        Optional[str], Query(description="minLon,minLat,maxLon,maxLat (for example the map view)")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=10000)] = 2000,
    conn=Depends(db.get_conn),
):
    box = None
    if bbox:
        try:
            box = parse_bbox(bbox)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    rows = queries.list_amenities(conn, amenity_type=amenity_type, bbox=box, limit=limit)
    return to_feature_collection(rows)


@app.get("/api/amenities/near", tags=["search"], summary="Amenities within a distance of a point")
def amenities_near(
    lat: Lat,
    lon: Lon,
    radius_m: Annotated[float, Query(gt=0, le=5000, description="Search radius in metres")] = 500,
    amenity_type: AmenityType = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    conn=Depends(db.get_conn),
):
    rows = queries.amenities_near(conn, lon, lat, radius_m, amenity_type=amenity_type, limit=limit)
    return to_feature_collection(rows)


@app.get("/api/amenities/nearest", tags=["search"], summary="The closest amenities to a point")
def nearest_amenities(
    lat: Lat,
    lon: Lon,
    amenity_type: AmenityType = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 5,
    conn=Depends(db.get_conn),
):
    rows = queries.nearest_amenities(conn, lon, lat, amenity_type=amenity_type, limit=limit)
    return to_feature_collection(rows)


@app.get("/api/amenities/{amenity_id}", tags=["amenities"], summary="One amenity by id")
def get_amenity(amenity_id: int, conn=Depends(db.get_conn)):
    row = queries.get_amenity(conn, amenity_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Amenity not found")
    return to_feature(row)


# The web map (HTML, CSS, JS). Mounted last so it doesn't hide the /api routes.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
