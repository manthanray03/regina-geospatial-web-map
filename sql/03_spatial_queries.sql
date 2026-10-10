-- Spatial queries I used while testing the data.
-- Run them in psql or pgAdmin after loading the data.
-- Distances are in metres because the points are cast to geography.
-- Test location: around Regina City Hall (lon -104.6107, lat 50.4475).


-- 1. How many amenities of each type are there?
SELECT amenity_type, count(*) AS total
FROM park_amenities
GROUP BY amenity_type
ORDER BY total DESC;


-- 2. Everything within 500 m of City Hall, closest first.
SELECT id, name, amenity_type, park_name,
       round(ST_Distance(geom::geography,
             ST_SetSRID(ST_MakePoint(-104.6107, 50.4475), 4326)::geography)) AS distance_m
FROM park_amenities
WHERE ST_DWithin(geom::geography,
                 ST_SetSRID(ST_MakePoint(-104.6107, 50.4475), 4326)::geography,
                 500)
ORDER BY distance_m;


-- 3. The 5 closest playgrounds (nearest neighbour search with <->).
-- The <-> operator uses the GiST index, so it does not have to sort the whole table.
SELECT id, name, park_name,
       round(geom::geography <-> ST_SetSRID(ST_MakePoint(-104.6107, 50.4475), 4326)::geography) AS distance_m
FROM park_amenities
WHERE amenity_type ILIKE '%play%'
ORDER BY geom::geography <-> ST_SetSRID(ST_MakePoint(-104.6107, 50.4475), 4326)::geography
LIMIT 5;


-- 4. Make a 300 m buffer around a point and find what falls inside it.
-- ST_Buffer on geography gives a real 300 m circle, then cast back to geometry.
WITH area AS (
    SELECT ST_Buffer(ST_SetSRID(ST_MakePoint(-104.6152, 50.4326), 4326)::geography, 300)::geometry AS geom
)
SELECT a.id, a.name, a.amenity_type
FROM park_amenities a
JOIN area ON ST_Intersects(a.geom, area.geom);


-- 5. Playgrounds that have a washroom within 150 m.
SELECT p.id, p.name, p.park_name
FROM park_amenities p
WHERE p.amenity_type ILIKE '%play%'
  AND EXISTS (
      SELECT 1
      FROM park_amenities w
      WHERE w.amenity_type ILIKE '%washroom%'
        AND ST_DWithin(p.geom::geography, w.geom::geography, 150)
  );


-- 6. Number of amenities in each park (only works if the data has a park name).
SELECT park_name, count(*) AS amenities
FROM park_amenities
WHERE park_name IS NOT NULL
GROUP BY park_name
ORDER BY amenities DESC
LIMIT 20;


-- 7. Query tuning: compare the plan with and without the index.
-- With the index you should see an "Index Scan" or "Bitmap Index Scan" on
-- park_amenities_geog_idx. Without it you get a "Seq Scan" over every row.
EXPLAIN ANALYZE
SELECT id
FROM park_amenities
WHERE ST_DWithin(geom::geography,
                 ST_SetSRID(ST_MakePoint(-104.6107, 50.4475), 4326)::geography,
                 500);

-- Turn index scans off for this session only, then run the same EXPLAIN again.
SET enable_indexscan = off;
SET enable_bitmapscan = off;

EXPLAIN ANALYZE
SELECT id
FROM park_amenities
WHERE ST_DWithin(geom::geography,
                 ST_SetSRID(ST_MakePoint(-104.6107, 50.4475), 4326)::geography,
                 500);

RESET enable_indexscan;
RESET enable_bitmapscan;
