-- Replace 'Angle Park' and IDs as needed
UPDATE races
SET meeting_url = REPLACE(meeting_url, '/220126/', '/250176/')
WHERE meeting_name = 'Angle Park' 
  AND meeting_url LIKE '%/220126/%';
