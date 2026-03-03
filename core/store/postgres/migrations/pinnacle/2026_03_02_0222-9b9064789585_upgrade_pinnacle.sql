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

-- Running upgrade 239ea620858b -> 0e803ac6a3ce

UPDATE public.alembic_version_pinnacle SET version_num='0e803ac6a3ce' WHERE public.alembic_version_pinnacle.version_num = '239ea620858b';

-- Running upgrade 0e803ac6a3ce -> fix_odds_raw_data

TRUNCATE TABLE pinnacle.odds_raw_data;

ALTER TABLE pinnacle.odds_raw_data ADD COLUMN league_id INTEGER NOT NULL;

ALTER TABLE pinnacle.odds_raw_data ADD CONSTRAINT uq_odds_raw_data_league_id UNIQUE (league_id);

ALTER TABLE pinnacle.odds_raw_data DROP CONSTRAINT uq_odds_raw_data_country_league;

ALTER TABLE pinnacle.odds_raw_data DROP COLUMN country_name;

UPDATE public.alembic_version_pinnacle SET version_num='fix_odds_raw_data' WHERE public.alembic_version_pinnacle.version_num = '0e803ac6a3ce';

-- Running upgrade fix_odds_raw_data -> fcbbf2b9d4fc

UPDATE public.alembic_version_pinnacle SET version_num='fcbbf2b9d4fc' WHERE public.alembic_version_pinnacle.version_num = 'fix_odds_raw_data';

-- Running upgrade fcbbf2b9d4fc -> a9e3e43cc332

ALTER TABLE pinnacle.odds_raw_data DROP COLUMN league_name;

UPDATE public.alembic_version_pinnacle SET version_num='a9e3e43cc332' WHERE public.alembic_version_pinnacle.version_num = 'fcbbf2b9d4fc';

-- Running upgrade a9e3e43cc332 -> a1ce6caaa752

DROP INDEX pinnacle.idx_pinnacle_fixtures_away_team;

DROP INDEX pinnacle.idx_pinnacle_fixtures_created_at;

DROP INDEX pinnacle.idx_pinnacle_fixtures_home_team;

DROP INDEX pinnacle.idx_pinnacle_fixtures_kickoff_time;

DROP INDEX pinnacle.idx_pinnacle_fixtures_league_id;

DROP INDEX pinnacle.idx_pinnacle_fixtures_updated_at;

CREATE INDEX idx_fixtures_away_team ON pinnacle.fixtures (away_team);

CREATE INDEX idx_fixtures_created_at ON pinnacle.fixtures (created_at);

CREATE INDEX idx_fixtures_home_team ON pinnacle.fixtures (home_team);

CREATE INDEX idx_fixtures_kickoff_time ON pinnacle.fixtures (kickoff_time);

CREATE INDEX idx_fixtures_league_id ON pinnacle.fixtures (league_id);

CREATE INDEX idx_fixtures_updated_at ON pinnacle.fixtures (updated_at);

DROP INDEX pinnacle.idx_pinnacle_moneyline_created_at;

DROP INDEX pinnacle.idx_pinnacle_moneyline_match_id;

DROP INDEX pinnacle.idx_pinnacle_moneyline_updated_at;

CREATE INDEX idx_moneylines_created_at ON pinnacle.moneylines (created_at);

CREATE INDEX idx_moneylines_match_id ON pinnacle.moneylines (match_id);

CREATE INDEX idx_moneylines_updated_at ON pinnacle.moneylines (updated_at);

DROP INDEX pinnacle.idx_pinnacle_spreads_created_at;

DROP INDEX pinnacle.idx_pinnacle_spreads_match_id;

DROP INDEX pinnacle.idx_pinnacle_spreads_updated_at;

CREATE INDEX idx_spreads_created_at ON pinnacle.spreads (created_at);

CREATE INDEX idx_spreads_match_id ON pinnacle.spreads (match_id);

CREATE INDEX idx_spreads_updated_at ON pinnacle.spreads (updated_at);

UPDATE public.alembic_version_pinnacle SET version_num='a1ce6caaa752' WHERE public.alembic_version_pinnacle.version_num = 'a9e3e43cc332';

-- Running upgrade a1ce6caaa752 -> 9b9064789585

DROP INDEX pinnacle.idx_league_raw_data_created_at;

DROP INDEX pinnacle.idx_league_raw_data_updated_at;

CREATE INDEX idx_league_raw_created_at ON pinnacle.league_raw (created_at);

CREATE INDEX idx_league_raw_updated_at ON pinnacle.league_raw (updated_at);

DROP INDEX pinnacle.idx_odds_raw_data_created_at;

DROP INDEX pinnacle.idx_odds_raw_data_updated_at;

CREATE INDEX idx_odds_raw_created_at ON pinnacle.odds_raw (created_at);

CREATE INDEX idx_odds_raw_updated_at ON pinnacle.odds_raw (updated_at);

UPDATE public.alembic_version_pinnacle SET version_num='9b9064789585' WHERE public.alembic_version_pinnacle.version_num = 'a1ce6caaa752';

COMMIT;

