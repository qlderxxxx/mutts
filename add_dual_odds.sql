-- Add new odds columns and remove old fixed_odds column
ALTER TABLE runners ADD COLUMN ghr_odds DECIMAL(10,2);
ALTER TABLE runners ADD COLUMN sportsbet_odds DECIMAL(10,2);
ALTER TABLE runners DROP COLUMN fixed_odds;
