BEGIN;

CREATE TABLE public.alembic_version_oddsportal (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_oddsportal_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 6d666563142c

CREATE TABLE oddsportal.league_raw (
    id SERIAL NOT NULL, 
    sport VARCHAR(64) NOT NULL, 
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
    UNIQUE (sport)
);

CREATE INDEX idx_league_raw_created_at ON oddsportal.league_raw (created_at);

CREATE INDEX idx_league_raw_not_parsed ON oddsportal.league_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_league_raw_updated_at ON oddsportal.league_raw (updated_at);

INSERT INTO public.alembic_version_oddsportal (version_num) VALUES ('6d666563142c') RETURNING public.alembic_version_oddsportal.version_num;

COMMIT;

