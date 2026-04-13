-- Leagues: id aligned with LeagueID enum (101-105), priority LEVEL_MAJOR=500, status ACTIVE=1
INSERT INTO public.leagues (id, name, priority, status, created_at, updated_at)
VALUES
    (101, 'Premier League', 500, 1, NOW(), NOW()),
    (102, 'LaLiga', 500, 1, NOW(), NOW()),
    (103, 'Serie A', 500, 1, NOW(), NOW()),
    (104, 'Bundesliga', 500, 1, NOW(), NOW()),
    (105, 'Ligue 1', 500, 1, NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    priority = EXCLUDED.priority,
    updated_at = NOW();

-- Site leagues (fotmob): league_id = FotMob ID, ref_league_id = public.leagues.id
-- 47 Premier League -> 101, 53 Ligue 1 -> 105, 54 Bundesliga -> 104, 55 Serie A -> 103, 87 LaLiga -> 102
INSERT INTO public.site_leagues (site_name, league_id, league_name, ref_league_id, status, created_at, updated_at)
VALUES
    ('fotmob', '47', 'Premier League', 101, 1, NOW(), NOW()),
    ('fotmob', '53', 'Ligue 1', 105, 1, NOW(), NOW()),
    ('fotmob', '54', 'Bundesliga', 104, 1, NOW(), NOW()),
    ('fotmob', '55', 'Serie A', 103, 1, NOW(), NOW()),
    ('fotmob', '87', 'LaLiga', 102, 1, NOW(), NOW())
ON CONFLICT (site_name, league_id) DO UPDATE SET
    league_name = EXCLUDED.league_name,
    ref_league_id = EXCLUDED.ref_league_id,
    updated_at = NOW();

-- pinnacle rename tables
ALTER TABLE pinnacle.pinnacle_fixtures RENAME TO fixtures;
ALTER TABLE pinnacle.pinnacle_moneyline RENAME TO moneylines;
ALTER TABLE pinnacle.pinnacle_spreads RENAME TO spreads;
ALTER TABLE pinnacle.odds_raw_data RENAME TO odds_raw;
ALTER TABLE pinnacle.league_raw_data RENAME TO league_raw;

-- fotmob rename raw data tables
ALTER TABLE fotmob.fixture_raw_data RENAME TO fixture_raw;
ALTER TABLE fotmob.match_raw_data RENAME TO match_raw;

-- oddsportal site_leagues: set ref_league_id for the 5 major leagues
UPDATE public.site_leagues SET ref_league_id = 101 WHERE league_id = '91201' AND site_name = 'oddsportal';  -- Premier League (England)
UPDATE public.site_leagues SET ref_league_id = 102 WHERE league_id = '93113' AND site_name = 'oddsportal';  -- LaLiga (Spain)
UPDATE public.site_leagues SET ref_league_id = 103 WHERE league_id = '92615' AND site_name = 'oddsportal';  -- Serie A (Italy)
UPDATE public.site_leagues SET ref_league_id = 104 WHERE league_id = '93299' AND site_name = 'oddsportal';  -- Bundesliga (Germany)
UPDATE public.site_leagues SET ref_league_id = 105 WHERE league_id = '92251' AND site_name = 'oddsportal';  -- Ligue 1 (France)
