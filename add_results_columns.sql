-- Add columns to runners table for results data
ALTER TABLE runners
ADD COLUMN IF NOT EXISTS starting_price DECIMAL(6,2),
ADD COLUMN IF NOT EXISTS finishing_position INTEGER;

-- Add column to races table for top 2 analysis
ALTER TABLE races
ADD COLUMN IF NOT EXISTS top_2_in_top_2 BOOLEAN;

-- Create index for faster queries on historical races
CREATE INDEX IF NOT EXISTS idx_races_date_status ON races(race_time, status);
CREATE INDEX IF NOT EXISTS idx_runners_position ON runners(race_id, finishing_position);
