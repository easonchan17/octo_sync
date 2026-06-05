INSERT INTO public.canonical_leagues (id, name, priority, status, created_at, updated_at)
VALUES
    (101, 'Premier League', 500, 1, NOW(), NOW()),
    (102, 'LaLiga', 500, 1, NOW(), NOW()),
    (103, 'Serie A', 500, 1, NOW(), NOW()),
    (104, 'Bundesliga', 500, 1, NOW(), NOW()),
    (105, 'Ligue 1', 500, 1, NOW(), NOW()),
    (301, 'World Cup', 500, 1, NOW(), NOW()),
    (311, 'World Cup Qualification CONCACAF', 500, 1, NOW(), NOW()),
    (312, 'World Cup Qualification CONMEBOL', 500, 1, NOW(), NOW()),
    (313, 'World Cup Qualification UEFA', 500, 1, NOW(), NOW()),
    (314, 'World Cup Qualification AFC', 500, 1, NOW(), NOW()),
    (315, 'World Cup Qualification CAF', 500, 1, NOW(), NOW()),
    (316, 'World Cup Qualification OFC', 500, 1, NOW(), NOW()),
    (317, 'World Cup Qualification Inter-confederation', 500, 1, NOW(), NOW()),
    (401, 'Champions League', 500, 1, NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    priority = EXCLUDED.priority,
    updated_at = NOW();


-- Functions calling league_service.resolve and league_service.get_site_leagues depend on the following data
-- Find the record in canonical_leagues via ref_league_id to get the league priority
INSERT INTO public.site_leagues (site_name, league_id, league_name, ref_league_id, status, created_at, updated_at)
VALUES
    ('fotmob', 42, 'Champions League', 401, 1, NOW(), NOW()),
    ('fotmob', 47, 'Premier League', 101, 1, NOW(), NOW()),
    ('fotmob', 53, 'Ligue 1', 105, 1, NOW(), NOW()),
    ('fotmob', 54, 'Bundesliga', 104, 1, NOW(), NOW()),
    ('fotmob', 55, 'Serie A', 103, 1, NOW(), NOW()),
    ('fotmob', 87, 'LaLiga', 102, 1, NOW(), NOW()),
    ('fotmob', 77, 'World Cup', 301, 1, NOW(), NOW()),
    ('fotmob', 10195, 'World Cup Qualification UEFA', 313, 1, NOW(), NOW()),
    ('fotmob', 10196, 'World Cup Qualification CAF', 315, 1, NOW(), NOW()),
    ('fotmob', 10197, 'World Cup Qualification AFC', 314, 1, NOW(), NOW()),
    ('fotmob', 10198, 'World Cup Qualification CONCACAF', 311, 1, NOW(), NOW()),
    ('fotmob', 10199, 'World Cup Qualification CONMEBOL', 312, 1, NOW(), NOW()),
    ('fotmob', 10200, 'World Cup Qualification OFC', 316, 1, NOW(), NOW()),
    ('fotmob', 10201, 'World Cup Qualification Inter-confederation', 317, 1, NOW(), NOW()),
    ('oddsportal', 91201, 'Premier League', 101, 1, NOW(), NOW()),
    ('oddsportal', 93113, 'LaLiga', 102, 1, NOW(), NOW()),
    ('oddsportal', 92615, 'Serie A', 103, 1, NOW(), NOW()),
    ('oddsportal', 93299, 'Bundesliga', 104, 1, NOW(), NOW()),
    ('oddsportal', 92251, 'Ligue 1', 105, 1, NOW(), NOW()),
    ('oddsportal', 77311, 'World Cup', 301, 1, NOW(), NOW()),
    ('oddsportal', 87559, 'Champions League', 401, 1, NOW(), NOW())
ON CONFLICT (site_name, league_id) DO UPDATE SET
    league_name = EXCLUDED.league_name,
    ref_league_id = EXCLUDED.ref_league_id,
    updated_at = NOW();
