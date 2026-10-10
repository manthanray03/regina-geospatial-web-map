"""Settings shared by the scripts and the API.

Values come from the .env file (copy .env.example to .env first).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
SQL_DIR = PROJECT_DIR / "sql"

load_dotenv(PROJECT_DIR / ".env")

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "regina_gis")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "change_me")

# Park amenities shapefile from the City of Regina open data portal
# https://open.regina.ca/dataset/parks-and-amenities
AMENITIES_URL = os.getenv(
    "AMENITIES_URL",
    "https://0pendatafiles.blob.core.windows.net/opendata/ParksAndAmenities/SHP_ZIP/shp.ParkAmenities.zip",
)
AMENITIES_ZIP = DATA_DIR / "park_amenities.zip"

# ogr2ogr comes with GDAL. On Windows it is in the OSGeo4W Shell that installs with QGIS.
OGR2OGR = os.getenv("OGR2OGR_PATH", "ogr2ogr")

# Only needed if the shapefile has no .prj file (for example EPSG:26913).
SOURCE_SRS = os.getenv("SOURCE_SRS", "")

# The shapefile column names are not documented on the portal, so the loader
# tries to guess them. If it guesses wrong, set these in .env.
NAME_COLUMN = os.getenv("NAME_COLUMN", "")
TYPE_COLUMN = os.getenv("TYPE_COLUMN", "")
PARK_COLUMN = os.getenv("PARK_COLUMN", "")


def conninfo():
    """Connection string for psycopg."""
    return (
        f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} "
        f"user={DB_USER} password={DB_PASSWORD}"
    )


def ogr_pg_source():
    """Connection string in the format ogr2ogr expects."""
    return "PG:" + conninfo()
