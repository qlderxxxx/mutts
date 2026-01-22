-- One-time backfill of meeting_url for existing races
-- This constructs the form guide URL from meeting_name and race_time

UPDATE races
SET meeting_url = 
    'https://www.thegreyhoundrecorder.com.au/form-guides/' || 
    LOWER(REPLACE(meeting_name, ' ', '-')) || 
    '/fields/' || 
    TO_CHAR(race_time, 'DDMMYY') || 
    '/'
WHERE meeting_url IS NULL;

-- Verify the update
SELECT 
    meeting_name,
    TO_CHAR(race_time, 'YYYY-MM-DD') as race_date,
    meeting_url,
    COUNT(*) as race_count
FROM races
WHERE meeting_url IS NOT NULL
GROUP BY meeting_name, TO_CHAR(race_time, 'YYYY-MM-DD'), meeting_url
ORDER BY race_date DESC, meeting_name;
