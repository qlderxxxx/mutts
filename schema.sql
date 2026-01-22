-- Greyhound Micro-Field Finder Database Schema
-- Run this in your Supabase SQL Editor

-- Create races table
CREATE TABLE IF NOT EXISTS races (
    id BIGSERIAL PRIMARY KEY,
    meeting_name TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    race_time TIMESTAMPTZ NOT NULL,
    status TEXT DEFAULT 'upcoming',
    active_runner_count INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(meeting_name, race_number, race_time)
);

-- Create runners table
CREATE TABLE IF NOT EXISTS runners (
    id BIGSERIAL PRIMARY KEY,
    race_id BIGINT NOT NULL REFERENCES races(id) ON DELETE CASCADE,
    dog_name TEXT NOT NULL,
    box_number INTEGER NOT NULL,
    fixed_odds DECIMAL(10, 2),
    is_scratched BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(race_id, box_number)
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_races_time ON races(race_time);
CREATE INDEX IF NOT EXISTS idx_races_active_count ON races(active_runner_count);
CREATE INDEX IF NOT EXISTS idx_races_time_count ON races(race_time, active_runner_count);
CREATE INDEX IF NOT EXISTS idx_runners_race_id ON runners(race_id);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_races_updated_at
    BEFORE UPDATE ON races
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_runners_updated_at
    BEFORE UPDATE ON runners
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS)
ALTER TABLE races ENABLE ROW LEVEL SECURITY;
ALTER TABLE runners ENABLE ROW LEVEL SECURITY;

-- Create policies for public access (read and write)
-- This allows the scraper to insert/update data using the anon key
CREATE POLICY "Allow all operations on races"
    ON races FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow all operations on runners"
    ON runners FOR ALL
    USING (true)
    WITH CHECK (true);
