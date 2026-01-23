-- Check what meeting URLs we actually have in the database
SELECT 
    meeting_name,
    TO_CHAR(race_time, 'YYYY-MM-DD') as race_date,
    meeting_url,
    status,
    COUNT(*) as race_count
FROM races
WHERE race_time >= '2026-01-20'
GROUP BY meeting_name, TO_CHAR(race_time, 'YYYY-MM-DD'), meeting_url, status
ORDER BY race_date DESC, meeting_name
LIMIT 20;
