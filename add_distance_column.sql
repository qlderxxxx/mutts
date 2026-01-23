-- Add distance_meters column to races table
ALTER TABLE races ADD COLUMN IF NOT EXISTS distance_meters INTEGER;

-- Create index for filtering by distance
CREATE INDEX IF NOT EXISTS idx_races_distance ON races(distance_meters);
