"""Export the amenities from PostGIS to GeoJSON and publish them to ArcGIS Online
as a hosted feature layer, using the ArcGIS API for Python.

Needs an ArcGIS account that is allowed to publish hosted layers. A basic
public ArcGIS Online account can't do this; an ArcGIS Location Platform
account (has a free tier) or an ArcGIS Online trial can.

Set ARCGIS_USERNAME and ARCGIS_PASSWORD in .env, then run from the project folder:
    python -m arcgis_online.publish_to_arcgis
    python -m arcgis_online.publish_to_arcgis --public   (also share with everyone)
"""
import argparse
import json
import os
import sys

import psycopg

from etl import config

TITLE = "Regina Park Amenities"
TAGS = "Regina, Saskatchewan, parks, amenities, open data"
SNIPPET = "Park amenity points from the City of Regina open data portal, loaded through PostGIS."
GEOJSON_PATH = config.DATA_DIR / "park_amenities.geojson"


def export_geojson(path):
    """Build one GeoJSON FeatureCollection in PostGIS and save it to a file."""
    with psycopg.connect(config.conninfo()) as conn:
        row = conn.execute(
            """
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(json_agg(json_build_object(
                    'type', 'Feature',
                    'geometry', ST_AsGeoJSON(geom)::json,
                    'properties', json_build_object(
                        'id', id,
                        'name', name,
                        'amenity_type', amenity_type,
                        'park_name', park_name
                    )
                )), '[]'::json)
            )
            FROM park_amenities
            """
        ).fetchone()

    collection = row[0]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(collection), encoding="utf-8")
    print(f"Exported {len(collection['features'])} features to {path}")


def add_item(gis, path):
    """Upload the GeoJSON file as an item.

    Newer versions of the arcgis package add items through folders. Older
    versions use gis.content.add, so fall back to that if needed.
    """
    try:
        from arcgis.gis import ItemProperties, ItemTypeEnum

        props = ItemProperties(
            title=TITLE,
            item_type=ItemTypeEnum.GEOJSON,
            tags=TAGS,
            snippet=SNIPPET,
        )
        root_folder = gis.content.folders.get()
        job = root_folder.add(item_properties=props, file=str(path))
        return job.result()
    except (ImportError, AttributeError, TypeError):
        props = {"title": TITLE, "type": "GeoJson", "tags": TAGS, "snippet": SNIPPET}
        return gis.content.add(props, data=str(path))


def share_public(item):
    try:
        item.sharing.sharing_level = "EVERYONE"
    except AttributeError:
        item.share(everyone=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--public", action="store_true", help="share the layer with everyone")
    args = parser.parse_args()

    username = os.getenv("ARCGIS_USERNAME")
    password = os.getenv("ARCGIS_PASSWORD")
    portal = os.getenv("ARCGIS_URL", "https://www.arcgis.com")
    if not username or not password:
        sys.exit("Set ARCGIS_USERNAME and ARCGIS_PASSWORD in .env first.")

    # imported here so the rest of the project works without the arcgis package
    from arcgis.gis import GIS

    export_geojson(GEOJSON_PATH)

    gis = GIS(portal, username, password)
    print(f"Signed in to {portal} as {gis.users.me.username}")

    item = add_item(gis, GEOJSON_PATH)
    print(f"Uploaded GeoJSON item: {item.id}")

    layer = item.publish()
    print(f"Published hosted feature layer: {layer.title}")
    print(f"Open it here: {layer.homepage}")

    if args.public:
        share_public(layer)
        print("Shared with everyone.")


if __name__ == "__main__":
    main()
