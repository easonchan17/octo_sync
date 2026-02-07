-- Insert leagues from LEAGUE_CONFIG
-- Generated from core/store/league_provider.py (legacy)

INSERT INTO public.leagues (id, name, is_popular, priority, sites, status, created_at, updated_at)
VALUES
    (
        101,
        'Premier League',
        false,
        0,
        '{
            "fbref": {"id": "9"},
            "fotmob": {"id": 47, "name": "premier-league"},
            "pinnacle": {"id": 1980},
            "football-data": {"id": "9", "name": "E0", "timezone": "Europe/London"}
        }'::jsonb,
        1,
        NOW(),
        NOW()
    ),
    (
        102,
        'LaLiga',
        false,
        0,
        '{}'::jsonb,
        1,
        NOW(),
        NOW()
    )
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    sites = EXCLUDED.sites,
    updated_at = NOW();
