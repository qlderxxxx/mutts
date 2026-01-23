-- Clean up invalid races (0, 1, or 2 runners) which are likely scrape errors or abandoned races
DELETE FROM races 
WHERE active_runner_count < 3;

-- Optional: You might want to keep 3 if they are legitimate scratchings down from 4?
-- The user said "no 0 or 1 runner fields allowed".
