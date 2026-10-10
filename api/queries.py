"""SQL used by the API. Every query returns rows as dicts.

All values from the user are passed as parameters (%s / %(name)s),
never pasted into the SQL string.
"""

COLUMNS = "id, name, amenity_type, park_name, ST_AsGeoJSON(geom)::json AS geometry"

# A point built from the lon/lat the user sent, as geography so distances are in metres.
POINT = "ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography"


def amenity_types(conn):
    return conn.execute(
        """
        SELECT amenity_type, count(*)::int AS count
        FROM park_amenities
        GROUP BY amenity_type
        ORDER BY count DESC, amenity_type
        """
    ).fetchall()


def list_amenities(conn, amenity_type=None, bbox=None, limit=2000):
    conditions = []
    params = []

    if amenity_type:
        conditions.append("amenity_type = %s")
        params.append(amenity_type)

    if bbox:
        # && is a fast bounding box check that uses the GiST index on geom
        conditions.append("geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)")
        params.extend(bbox)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(limit)

    return conn.execute(
        f"SELECT {COLUMNS} FROM park_amenities {where} ORDER BY id LIMIT %s",
        params,
    ).fetchall()


def amenities_near(conn, lon, lat, radius_m, amenity_type=None, limit=200):
    return conn.execute(
        f"""
        SELECT {COLUMNS},
               ROUND(ST_Distance(geom::geography, {POINT})::numeric, 1)::float8 AS distance_m
        FROM park_amenities
        WHERE ST_DWithin(geom::geography, {POINT}, %(radius)s)
          AND (%(type)s::text IS NULL OR amenity_type = %(type)s)
        ORDER BY distance_m
        LIMIT %(limit)s
        """,
        {"lon": lon, "lat": lat, "radius": radius_m, "type": amenity_type, "limit": limit},
    ).fetchall()


def nearest_amenities(conn, lon, lat, amenity_type=None, limit=5):
    # <-> is the nearest neighbour operator. With the geography index it only
    # looks at the closest points instead of sorting the whole table.
    return conn.execute(
        f"""
        SELECT {COLUMNS},
               ROUND((geom::geography <-> {POINT})::numeric, 1)::float8 AS distance_m
        FROM park_amenities
        WHERE (%(type)s::text IS NULL OR amenity_type = %(type)s)
        ORDER BY geom::geography <-> {POINT}
        LIMIT %(limit)s
        """,
        {"lon": lon, "lat": lat, "type": amenity_type, "limit": limit},
    ).fetchall()


def get_amenity(conn, amenity_id):
    return conn.execute(
        f"SELECT {COLUMNS} FROM park_amenities WHERE id = %s",
        (amenity_id,),
    ).fetchone()
