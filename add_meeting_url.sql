-- Add meeting_url column to races table
-- This stores the form guide URL for each meeting, which we can convert to results URL

ALTER TABLE races ADD COLUMN IF NOT EXISTS meeting_url TEXT;

-- Add index for efficient querying
CREATE INDEX IF NOT EXISTS idx_races_meeting_url ON races(meeting_url);
