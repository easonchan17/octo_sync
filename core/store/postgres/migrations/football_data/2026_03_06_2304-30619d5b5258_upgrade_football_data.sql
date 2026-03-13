BEGIN;

CREATE TABLE public.alembic_version_football_data (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_football_data_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> c8089868dc2f

CREATE TABLE football_data.countries (
    id SERIAL NOT NULL, 
    name VARCHAR(128) NOT NULL, 
    page_url VARCHAR(256) NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (name), 
    UNIQUE (page_url)
);

CREATE INDEX idx_countries_created_at ON football_data.countries (created_at);

CREATE INDEX idx_countries_updated_at ON football_data.countries (updated_at);

CREATE TABLE football_data.country_raw (
    id SERIAL NOT NULL, 
    name VARCHAR(128) NOT NULL, 
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
    html_body TEXT NOT NULL, 
    encoding VARCHAR(20), 
    PRIMARY KEY (id), 
    UNIQUE (name)
);

CREATE INDEX idx_country_raw_created_at ON football_data.country_raw (created_at);

CREATE INDEX idx_country_raw_not_parsed ON football_data.country_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_country_raw_updated_at ON football_data.country_raw (updated_at);

CREATE TABLE football_data.league_raw (
    id SERIAL NOT NULL, 
    country_id INTEGER NOT NULL, 
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
    html_body TEXT NOT NULL, 
    encoding VARCHAR(20), 
    PRIMARY KEY (id), 
    CONSTRAINT uq_fd_league_raw_source_url UNIQUE (source_url)
);

CREATE INDEX idx_fd_league_raw_created_at ON football_data.league_raw (created_at);

CREATE INDEX idx_fd_league_raw_not_parsed ON football_data.league_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_fd_league_raw_updated_at ON football_data.league_raw (updated_at);

CREATE TABLE football_data.match_odds (
    id SERIAL NOT NULL, 
    match_id INTEGER NOT NULL, 
    match_code VARCHAR(64), 
    kickoff_time TIMESTAMP WITH TIME ZONE NOT NULL, 
    home_team VARCHAR(64), 
    away_team VARCHAR(64), 
    home_open NUMERIC(10, 4), 
    draw_open NUMERIC(10, 4), 
    away_open NUMERIC(10, 4), 
    home_close NUMERIC(10, 4), 
    draw_close NUMERIC(10, 4), 
    away_close NUMERIC(10, 4), 
    ah_line_open NUMERIC(8, 2), 
    ah_home_open NUMERIC(10, 4), 
    ah_away_open NUMERIC(10, 4), 
    ah_line_close NUMERIC(8, 2), 
    ah_home_close NUMERIC(10, 4), 
    ah_away_close NUMERIC(10, 4), 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_match_odds_match_id UNIQUE (match_id)
);

CREATE INDEX idx_match_odds_created_at ON football_data.match_odds (created_at);

CREATE INDEX idx_match_odds_kickoff_time ON football_data.match_odds (kickoff_time);

CREATE INDEX idx_match_odds_match_code ON football_data.match_odds (match_code);

CREATE INDEX idx_match_odds_match_id ON football_data.match_odds (match_id);

CREATE INDEX idx_match_odds_updated_at ON football_data.match_odds (updated_at);

CREATE TABLE football_data.odds_raw (
    id SERIAL NOT NULL, 
    league_id INTEGER NOT NULL, 
    csv_body TEXT NOT NULL, 
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
    PRIMARY KEY (id), 
    CONSTRAINT uq_odds_raw_source_url UNIQUE (source_url)
);

CREATE INDEX idx_odds_raw_created_at ON football_data.odds_raw (created_at);

CREATE INDEX idx_odds_raw_league_id ON football_data.odds_raw (league_id);

CREATE INDEX idx_odds_raw_not_parsed ON football_data.odds_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_odds_raw_updated_at ON football_data.odds_raw (updated_at);

INSERT INTO public.alembic_version_football_data (version_num) VALUES ('c8089868dc2f') RETURNING public.alembic_version_football_data.version_num;

-- Running upgrade c8089868dc2f -> 30619d5b5258

ALTER TABLE football_data.countries DROP CONSTRAINT countries_page_url_key;

ALTER TABLE football_data.league_raw ADD COLUMN country_name VARCHAR(128) NOT NULL;

DROP INDEX football_data.idx_fd_league_raw_created_at;

DROP INDEX football_data.idx_fd_league_raw_not_parsed;

DROP INDEX football_data.idx_fd_league_raw_updated_at;

ALTER TABLE football_data.league_raw DROP CONSTRAINT uq_fd_league_raw_source_url;

CREATE INDEX idx_league_raw_created_at ON football_data.league_raw (created_at);

CREATE INDEX idx_league_raw_not_parsed ON football_data.league_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_league_raw_updated_at ON football_data.league_raw (updated_at);

ALTER TABLE football_data.league_raw ADD UNIQUE (country_name);

ALTER TABLE football_data.league_raw DROP COLUMN country_id;

UPDATE public.alembic_version_football_data SET version_num='30619d5b5258' WHERE public.alembic_version_football_data.version_num = 'c8089868dc2f';

COMMIT;

