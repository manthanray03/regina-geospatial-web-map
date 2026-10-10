"""Download the park amenities shapefile from the City of Regina open data portal.

Run from the project folder:
    python -m etl.download_data
"""
import sys
import zipfile

import requests

from etl import config


def download(url, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url}")

    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with open(target, "wb") as f:
            for chunk in response.iter_content(chunk_size=64 * 1024):
                f.write(chunk)

    size_kb = target.stat().st_size / 1024
    print(f"Saved {target} ({size_kb:.0f} KB)")


def check_zip(path):
    """Make sure the zip actually has a shapefile in it before we load it."""
    with zipfile.ZipFile(path) as z:
        names = z.namelist()

    shp_files = [n for n in names if n.lower().endswith(".shp")]
    if not shp_files:
        sys.exit(f"No .shp file found in {path}. Files in zip: {names}")

    if not any(n.lower().endswith(".prj") for n in names):
        print("Warning: no .prj file in the zip, so the coordinate system is unknown.")
        print("Set SOURCE_SRS in .env (for example EPSG:26913) before loading.")

    print("Shapefile(s) in zip:", ", ".join(shp_files))


if __name__ == "__main__":
    download(config.AMENITIES_URL, config.AMENITIES_ZIP)
    check_zip(config.AMENITIES_ZIP)
