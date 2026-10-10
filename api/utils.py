"""Small helpers that don't need the database (easy to unit test)."""


def parse_bbox(text):
    """Turn "minLon,minLat,maxLon,maxLat" into four floats.

    Raises ValueError if the text is not a valid box.
    """
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox needs 4 numbers: minLon,minLat,maxLon,maxLat")

    try:
        min_lon, min_lat, max_lon, max_lat = (float(p) for p in parts)
    except ValueError:
        raise ValueError("bbox values must be numbers")

    if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
        raise ValueError("longitude must be between -180 and 180")
    if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise ValueError("latitude must be between -90 and 90")
    if min_lon >= max_lon or min_lat >= max_lat:
        raise ValueError("min values must be smaller than max values")

    return min_lon, min_lat, max_lon, max_lat


def to_feature(row):
    """One database row -> one GeoJSON Feature."""
    row = dict(row)
    geometry = row.pop("geometry")
    feature_id = row.get("id")
    return {"type": "Feature", "id": feature_id, "geometry": geometry, "properties": row}


def to_feature_collection(rows):
    features = [to_feature(r) for r in rows]
    return {"type": "FeatureCollection", "count": len(features), "features": features}
