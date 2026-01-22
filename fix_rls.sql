-- Fix RLS policies to allow scraper to write data
-- Run this in Supabase SQL Editor

-- Drop existing policies
DROP POLICY IF EXISTS "Allow public read access on races" ON races;
DROP POLICY IF EXISTS "Allow public read access on runners" ON runners;

-- Create new policies that allow both read and write
CREATE POLICY "Allow all operations on races"
    ON races FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow all operations on runners"
    ON runners FOR ALL
    USING (true)
    WITH CHECK (true);
