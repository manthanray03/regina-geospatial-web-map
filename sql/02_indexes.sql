-- Indexes for park_amenities. load_data.py runs this after building the table.

-- Spatial index on the geometry. Used by bounding box (&&) searches.
CREATE INDEX IF NOT EXISTS park_amenities_geom_idx
    ON park_amenities USING GIST (geom);

-- Index on the geography version of the point. The API measures distance in
-- metres with geom::geography, and this lets ST_DWithin and <-> use an index
-- instead of checking every row.
CREATE INDEX IF NOT EXISTS park_amenities_geog_idx
    ON park_amenities USING GIST ((geom::geography));

-- Normal index for filtering by type (playground, washroom, etc.).
CREATE INDEX IF NOT EXISTS park_amenities_type_idx
    ON park_amenities (amenity_type);

-- Update table stats so the planner picks the indexes.
ANALYZE park_amenities;
