BEGIN;

CREATE TABLE public.alembic_version_pinnacle (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pinnacle_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> a1ab1ab757da

COMMENT ON COLUMN pinnacle.pinnacle_fixtures.fixture_id IS 'References fotmob_fixtures.match_id';

INSERT INTO public.alembic_version_pinnacle (version_num) VALUES ('a1ab1ab757da') RETURNING public.alembic_version_pinnacle.version_num;

-- Running upgrade a1ab1ab757da -> b342ceb15a9f

ALTER TABLE pinnacle.pinnacle_fixtures ALTER COLUMN fixture_id DROP NOT NULL;

UPDATE public.alembic_version_pinnacle SET version_num='b342ceb15a9f' WHERE public.alembic_version_pinnacle.version_num = 'a1ab1ab757da';

-- Running upgrade b342ceb15a9f -> 631bb64eed57

UPDATE public.alembic_version_pinnacle SET version_num='631bb64eed57' WHERE public.alembic_version_pinnacle.version_num = 'b342ceb15a9f';

-- Running upgrade 631bb64eed57 -> f352d9f83cfd

ALTER TABLE pinnacle.pinnacle_fixtures ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE pinnacle.pinnacle_fixtures ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE pinnacle.pinnacle_moneyline ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE pinnacle.pinnacle_moneyline ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE pinnacle.pinnacle_spreads ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE pinnacle.pinnacle_spreads ALTER COLUMN updated_at SET NOT NULL;

UPDATE public.alembic_version_pinnacle SET version_num='f352d9f83cfd' WHERE public.alembic_version_pinnacle.version_num = '631bb64eed57';

-- Running upgrade f352d9f83cfd -> 239ea620858b

CREATE TABLE pinnacle.league_raw_data (
    id SERIAL NOT NULL, 
    sport_id INTEGER NOT NULL, 
    sport_name VARCHAR(100) NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    source_url VARCHAR(512), 
    is_fetched BOOLEAN, 
    fetch_attempts INTEGER, 
    last_fetch_error TEXT, 
    last_fetched_at TIMESTAMP WITH TIME ZONE, 
    is_parsed BOOLEAN, 
    parse_attempts INTEGER, 
    last_parse_error TEXT, 
    last_parsed_at TIMESTAMP WITH TIME ZONE, 
    total_fetch_count INTEGER, 
    total_parse_count INTEGER, 
    confirm_count INTEGER, 
    json_body JSONB NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (sport_id)
);

CREATE INDEX idx_league_raw_data_created_at ON pinnacle.league_raw_data (created_at);

CREATE INDEX idx_league_raw_data_updated_at ON pinnacle.league_raw_data (updated_at);

CREATE TABLE pinnacle.odds_raw_data (
    id SERIAL NOT NULL, 
    country_name VARCHAR(100) NOT NULL, 
    league_name VARCHAR(100) NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    source_url VARCHAR(512), 
    is_fetched BOOLEAN, 
    fetch_attempts INTEGER, 
    last_fetch_error TEXT, 
    last_fetched_at TIMESTAMP WITH TIME ZONE, 
    is_parsed BOOLEAN, 
    parse_attempts INTEGER, 
    last_parse_error TEXT, 
    last_parsed_at TIMESTAMP WITH TIME ZONE, 
    total_fetch_count INTEGER, 
    total_parse_count INTEGER, 
    confirm_count INTEGER, 
    json_body JSONB NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_odds_raw_data_country_league UNIQUE (country_name, league_name)
);

CREATE INDEX idx_odds_raw_data_created_at ON pinnacle.odds_raw_data (created_at);

CREATE INDEX idx_odds_raw_data_updated_at ON pinnacle.odds_raw_data (updated_at);

UPDATE public.alembic_version_pinnacle SET version_num='239ea620858b' WHERE public.alembic_version_pinnacle.version_num = 'f352d9f83cfd';

COMMIT;

