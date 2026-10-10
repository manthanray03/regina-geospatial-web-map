"""Load the park amenities shapefile into PostgreSQL/PostGIS.

Steps:
  1. ogr2ogr (GDAL) copies the raw shapefile into a staging table and
     reprojects it to WGS 84 (EPSG:4326), which web maps use.
  2. Python looks at the staging columns and builds a clean table
     (park_amenities) with the same column names every time.
  3. sql/02_indexes.sql adds the spatial indexes.

Run from the project folder:
    python -m etl.load_data
"""
import subprocess
import sys
import zipfile

import psycopg
from psycopg import sql

from etl import config

STAGING_TABLE = "staging_park_amenities"

# Shapefile column names are cut to 10 characters, so these are short.
NAME_GUESSES = ["name", "amenity_nm", "asset_name", "label", "descriptio", "descr", "comments"]
TYPE_GUESSES = ["amenity", "amenity_ty", "type", "asset_type", "category", "class", "facility", "feature"]
PARK_GUESSES = ["park_name", "parkname", "park", "park_nm", "site_name", "location"]


def shapefile_in_zip(zip_path):
    """GDAL path to the first .shp inside the zip (it may be inside a folder)."""
    with zipfile.ZipFile(zip_path) as z:
        shp_files = [n for n in z.namelist() if n.lower().endswith(".shp")]
    if not shp_files:
        sys.exit(f"No .shp file found in {zip_path}")
    return f"/vsizip/{zip_path.as_posix()}/{shp_files[0]}"


def run_ogr2ogr():
    zip_path = config.AMENITIES_ZIP
    if not zip_path.exists():
        sys.exit(f"{zip_path} not found. Run: python -m etl.download_data")

    cmd = [
        config.OGR2OGR,
        "-f", "PostgreSQL",
        config.ogr_pg_source(),
        shapefile_in_zip(zip_path),
        "-nln", STAGING_TABLE,
        "-t_srs", "EPSG:4326",
        "-dim", "XY",  # drop Z values, the table only stores 2D points
        "-lco", "GEOMETRY_NAME=geom",
        "-lco", "FID=gid",
        "-lco", "LAUNDER=YES",
        "-overwrite",
    ]
    if config.SOURCE_SRS:
        cmd += ["-s_srs", config.SOURCE_SRS]

    print("Running ogr2ogr...")
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        sys.exit(
            "Could not find ogr2ogr. Install GDAL (it comes with QGIS) or set "
            "OGR2OGR_PATH in .env to the full path of ogr2ogr."
        )


def staging_columns(conn):
    rows = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s AND column_name NOT IN ('gid', 'geom')
        ORDER BY ordinal_position
        """,
        (STAGING_TABLE,),
    ).fetchall()
    return [r[0] for r in rows]


def pick_column(columns, setting, guesses, label):
    """Use the column from .env if set, otherwise take the first guess that exists."""
    if setting:
        if setting.lower() not in columns:
            sys.exit(f"{label} column '{setting}' is not in the shapefile. Columns are: {columns}")
        return setting.lower()

    for guess in guesses:
        if guess in columns:
            return guess
    return None


def text_or_null(column):
    if column is None:
        return sql.SQL("NULL::text")
    return sql.SQL("NULLIF(TRIM({}::text), '')").format(sql.Identifier(column))


def build_clean_table(conn, name_col, type_col, park_col):
    conn.execute("DROP TABLE IF EXISTS park_amenities")
    conn.execute(
        """
        CREATE TABLE park_amenities (
            id           serial PRIMARY KEY,
            source_id    integer,
            name         text,
            amenity_type text NOT NULL,
            park_name    text,
            geom         geometry(Point, 4326) NOT NULL
        )
        """
    )

    insert = sql.SQL(
        """
        INSERT INTO park_amenities (source_id, name, amenity_type, park_name, geom)
        SELECT gid,
               {name},
               COALESCE({type}, 'Unknown'),
               {park},
               ST_PointOnSurface(ST_Force2D(geom))
        FROM {staging}
        WHERE geom IS NOT NULL AND NOT ST_IsEmpty(geom)
        """
    ).format(
        name=text_or_null(name_col),
        type=text_or_null(type_col),
        park=text_or_null(park_col),
        staging=sql.Identifier(STAGING_TABLE),
    )
    conn.execute(insert)


def run_sql_file(conn, filename):
    path = config.SQL_DIR / filename
    print(f"Running {path.name}")
    conn.execute(path.read_text(encoding="utf-8"))


def main():
    # PostGIS has to be turned on before ogr2ogr can create a geometry column.
    with psycopg.connect(config.conninfo()) as conn:
        run_sql_file(conn, "01_setup.sql")

    run_ogr2ogr()

    with psycopg.connect(config.conninfo()) as conn:
        columns = staging_columns(conn)
        print("Columns in the shapefile:", ", ".join(columns))

        name_col = pick_column(columns, config.NAME_COLUMN, NAME_GUESSES, "Name")
        type_col = pick_column(columns, config.TYPE_COLUMN, TYPE_GUESSES, "Type")
        park_col = pick_column(columns, config.PARK_COLUMN, PARK_GUESSES, "Park")
        print(f"Using name={name_col}, type={type_col}, park={park_col}")

        if type_col is None:
            print("Warning: could not find an amenity type column. Set TYPE_COLUMN in .env.")

        build_clean_table(conn, name_col, type_col, park_col)
        run_sql_file(conn, "02_indexes.sql")

        total = conn.execute("SELECT count(*) FROM park_amenities").fetchone()[0]
        print(f"Loaded {total} park amenities.")

        print("Top amenity types:")
        top = conn.execute(
            """
            SELECT amenity_type, count(*) AS n
            FROM park_amenities
            GROUP BY amenity_type
            ORDER BY n DESC
            LIMIT 10
            """
        ).fetchall()
        for amenity_type, n in top:
            print(f"  {amenity_type}: {n}")


if __name__ == "__main__":
    main()
