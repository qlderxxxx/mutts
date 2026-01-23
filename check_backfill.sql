-- Check results for Jan 21
SELECT 
    meeting_name, 
    COUNT(*) as total_races,
    COUNT(CASE WHEN status = 'resulted' THEN 1 END) as resulted_races,
    STRING_AGG(CASE WHEN status = 'resulted' THEN race_number::text END, ', ' ORDER BY race_number) as resulted_race_nums
FROM races
WHERE race_time LIKE '2026-01-21%'
GROUP BY meeting_name
ORDER BY meeting_name;
