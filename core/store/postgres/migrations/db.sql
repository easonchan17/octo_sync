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


UPDATE public.site_leagues SET ref_league_id = 101 WHERE league_id = '1980' and site_name = 'pinnacle';
UPDATE public.site_leagues SET ref_league_id = 102 WHERE league_id = '2196' and site_name = 'pinnacle';
UPDATE public.site_leagues SET ref_league_id = 103 WHERE league_id = '2436' and site_name = 'pinnacle';
UPDATE public.site_leagues SET ref_league_id = 104 WHERE league_id = '9320' and site_name = 'pinnacle';
UPDATE public.site_leagues SET ref_league_id = 105 WHERE league_id = '2036' and site_name = 'pinnacle';


-- 1. Pinnacle Fixtures, Moneylines, Spreads, Odds Raw
ALTER TABLE pinnacle.pinnacle_fixtures RENAME TO fixtures;
ALTER TABLE pinnacle.pinnacle_moneyline RENAME TO moneylines;
ALTER TABLE pinnacle.pinnacle_spreads RENAME TO spreads;
ALTER TABLE pinnacle.odds_raw_data RENAME TO odds_raw;

-- 2. Pinnacle League Raw
ALTER TABLE pinnacle.league_raw_data RENAME TO league_raw;

-- 3. Fotmob Fixture Raw
ALTER TABLE fotmob.fixture_raw_data RENAME TO fixture_raw;

-- 4. Fotmob Match Raw
ALTER TABLE fotmob.match_raw_data RENAME TO match_raw;