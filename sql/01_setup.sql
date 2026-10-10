-- Turn on PostGIS for this database (only needs to run once).
CREATE EXTENSION IF NOT EXISTS postgis;

-- Quick check that it worked.
SELECT postgis_full_version();
