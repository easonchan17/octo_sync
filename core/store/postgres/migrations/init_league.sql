INSERT INTO public.canonical_leagues (id, name, priority, status, created_at, updated_at)
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


-- Functions calling league_service.resolve and league_service.get_site_leagues depend on the following data
-- Find the record in canonical_leagues via ref_league_id to get the league priority
INSERT INTO public.site_leagues (site_name, league_id, league_name, ref_league_id, status, created_at, updated_at)
VALUES
    ('fotmob', '47', 'Premier League', 101, 1, NOW(), NOW()),
    ('fotmob', '53', 'Ligue 1', 105, 1, NOW(), NOW()),
    ('fotmob', '54', 'Bundesliga', 104, 1, NOW(), NOW()),
    ('fotmob', '55', 'Serie A', 103, 1, NOW(), NOW()),
    ('fotmob', '87', 'LaLiga', 102, 1, NOW(), NOW()),
    ('oddsportal', '91201', 'Premier League', 101, 1, NOW(), NOW()),
    ('oddsportal', '93113', 'LaLiga', 102, 1, NOW(), NOW()),
    ('oddsportal', '92615', 'Serie A', 103, 1, NOW(), NOW()),
    ('oddsportal', '93299', 'Bundesliga', 104, 1, NOW(), NOW()),
    ('oddsportal', '92251', 'Ligue 1', 105, 1, NOW(), NOW())
ON CONFLICT (site_name, league_id) DO UPDATE SET
    league_name = EXCLUDED.league_name,
    ref_league_id = EXCLUDED.ref_league_id,
    updated_at = NOW();
