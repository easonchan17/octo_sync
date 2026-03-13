BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 84eb03fe348c

CREATE TABLE football_data.countries (
    id SERIAL NOT NULL, 
    name VARCHAR(128) NOT NULL, 
    page_url VARCHAR(256) NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (name)
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

CREATE TABLE football_data.league_odds (
    id SERIAL NOT NULL, 
    country_name VARCHAR(128) NOT NULL, 
    season INTEGER NOT NULL, 
    league_id VARCHAR(100) NOT NULL, 
    league_name VARCHAR(200) NOT NULL, 
    odds_url VARCHAR(512) NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_league_odds_season_league UNIQUE (season, league_id)
);

CREATE INDEX idx_league_odds_created_at ON football_data.league_odds (created_at);

CREATE INDEX idx_league_odds_season ON football_data.league_odds (season);

CREATE INDEX idx_league_odds_updated_at ON football_data.league_odds (updated_at);

CREATE TABLE football_data.league_raw (
    id SERIAL NOT NULL, 
    country_name VARCHAR(128) NOT NULL, 
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
    UNIQUE (country_name)
);

CREATE INDEX idx_league_raw_created_at ON football_data.league_raw (created_at);

CREATE INDEX idx_league_raw_not_parsed ON football_data.league_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_league_raw_updated_at ON football_data.league_raw (updated_at);

CREATE TABLE football_data.odds (
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
    CONSTRAINT uq_odds_match_id UNIQUE (match_id)
);

CREATE INDEX idx_odds_created_at ON football_data.odds (created_at);

CREATE INDEX idx_odds_kickoff_time ON football_data.odds (kickoff_time);

CREATE INDEX idx_odds_match_code ON football_data.odds (match_code);

CREATE INDEX idx_odds_match_id ON football_data.odds (match_id);

CREATE INDEX idx_odds_updated_at ON football_data.odds (updated_at);

CREATE TABLE football_data.odds_raw (
    id SERIAL NOT NULL, 
    season INTEGER NOT NULL, 
    league_id VARCHAR(100) NOT NULL, 
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
    CONSTRAINT uq_odds_raw_season_league UNIQUE (season, league_id)
);

CREATE INDEX idx_odds_raw_created_at ON football_data.odds_raw (created_at);

CREATE INDEX idx_odds_raw_not_parsed ON football_data.odds_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_odds_raw_updated_at ON football_data.odds_raw (updated_at);

CREATE TABLE fotmob.elo_ratings (
    id SERIAL NOT NULL, 
    team_code CHAR(8) NOT NULL, 
    match_code CHAR(8) NOT NULL, 
    kickoff_time TIMESTAMP WITH TIME ZONE NOT NULL, 
    season INTEGER NOT NULL, 
    venue VARCHAR(16) NOT NULL, 
    goal_diff INTEGER NOT NULL, 
    pre_rating NUMERIC(10, 4) NOT NULL, 
    expected_score NUMERIC(10, 4) NOT NULL, 
    post_rating NUMERIC(10, 4) NOT NULL, 
    game_count INTEGER NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_elo_ratings_team_match UNIQUE (team_code, match_code)
);

CREATE INDEX idx_elo_ratings_created_at ON fotmob.elo_ratings (created_at);

CREATE INDEX idx_elo_ratings_kickoff_time ON fotmob.elo_ratings (kickoff_time);

CREATE INDEX idx_elo_ratings_season ON fotmob.elo_ratings (season);

CREATE INDEX idx_elo_ratings_team_match ON fotmob.elo_ratings (team_code, match_code);

CREATE INDEX idx_elo_ratings_team_time ON fotmob.elo_ratings (team_code, kickoff_time);

CREATE INDEX idx_elo_ratings_updated_at ON fotmob.elo_ratings (updated_at);

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

CREATE TABLE pinnacle.league_raw (
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

CREATE INDEX idx_league_raw_created_at ON pinnacle.league_raw (created_at);

CREATE INDEX idx_league_raw_updated_at ON pinnacle.league_raw (updated_at);

CREATE TABLE pinnacle.odds_raw (
    id SERIAL NOT NULL, 
    league_id INTEGER NOT NULL, 
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
    UNIQUE (league_id)
);

CREATE INDEX idx_odds_raw_created_at ON pinnacle.odds_raw (created_at);

CREATE INDEX idx_odds_raw_updated_at ON pinnacle.odds_raw (updated_at);

DROP INDEX fbref.idx_match_stats_sync_state_created_at;

DROP INDEX fbref.idx_match_stats_sync_state_team_code_season;

DROP INDEX fbref.idx_match_stats_sync_state_updated_at;

DROP TABLE fbref.match_stats_sync_state;

DROP TABLE alembic_version_fbref;

DROP INDEX fbref.idx_passing_created_at;

DROP INDEX fbref.idx_passing_kickoff_time;

DROP INDEX fbref.idx_passing_match_team;

DROP INDEX fbref.idx_passing_updated_at;

DROP TABLE fbref.passing;

DROP INDEX fbref.idx_goal_keeping_created_at;

DROP INDEX fbref.idx_goal_keeping_kickoff_time;

DROP INDEX fbref.idx_goal_keeping_match_team;

DROP INDEX fbref.idx_goal_keeping_updated_at;

DROP TABLE fbref.goal_keeping;

DROP TABLE alembic_version_pinnacle;

DROP INDEX fbref.idx_comp_teams_comp_name;

DROP INDEX fbref.idx_comp_teams_created_at;

DROP INDEX fbref.idx_comp_teams_season_comp_code_team_code;

DROP INDEX fbref.idx_comp_teams_team_code;

DROP INDEX fbref.idx_comp_teams_team_name;

DROP INDEX fbref.idx_comp_teams_updated_at;

DROP TABLE fbref.comp_teams;

DROP INDEX fbref.idx_defensive_actions_created_at;

DROP INDEX fbref.idx_defensive_actions_kickoff_time;

DROP INDEX fbref.idx_defensive_actions_match_team;

DROP INDEX fbref.idx_defensive_actions_updated_at;

DROP TABLE fbref.defensive_actions;

DROP TABLE alembic_version_fotmob;

DROP INDEX fbref.idx_shooting_created_at;

DROP INDEX fbref.idx_shooting_kickoff_time;

DROP INDEX fbref.idx_shooting_match_team;

DROP INDEX fbref.idx_shooting_updated_at;

DROP TABLE fbref.shooting;

DROP INDEX fbref.idx_player_stats_sync_state_created_at;

DROP INDEX fbref.idx_player_stats_sync_state_updated_at;

DROP TABLE fbref.player_stats_sync_state;

DROP INDEX fbref.idx_match_results_away_code;

DROP INDEX fbref.idx_match_results_away_team;

DROP INDEX fbref.idx_match_results_comp_code;

DROP INDEX fbref.idx_match_results_comp_name;

DROP INDEX fbref.idx_match_results_created_at;

DROP INDEX fbref.idx_match_results_home_code;

DROP INDEX fbref.idx_match_results_home_team;

DROP INDEX fbref.idx_match_results_kickoff_time;

DROP INDEX fbref.idx_match_results_season;

DROP INDEX fbref.idx_match_results_updated_at;

DROP TABLE fbref.match_results;

DROP INDEX fbref.idx_elo_ratings_created_at;

DROP INDEX fbref.idx_elo_ratings_kickoff_time;

DROP INDEX fbref.idx_elo_ratings_season;

DROP INDEX fbref.idx_elo_ratings_team_match;

DROP INDEX fbref.idx_elo_ratings_team_time;

DROP INDEX fbref.idx_elo_ratings_updated_at;

DROP TABLE fbref.elo_ratings;

DROP INDEX fbref.idx_player_match_stats_created_at;

DROP INDEX fbref.idx_player_match_stats_match_player;

DROP INDEX fbref.idx_player_match_stats_team_code;

DROP INDEX fbref.idx_player_match_stats_updated_at;

DROP TABLE fbref.player_match_stats;

DROP INDEX fbref.idx_gca_created_at;

DROP INDEX fbref.idx_gca_kickoff_time;

DROP INDEX fbref.idx_gca_match_team;

DROP INDEX fbref.idx_gca_updated_at;

DROP TABLE fbref.gca;

DROP TABLE alembic_version_public;

DROP INDEX fbref.idx_fbref_fixtures_away_code_season;

DROP INDEX fbref.idx_fbref_fixtures_away_team;

DROP INDEX fbref.idx_fbref_fixtures_comp_code;

DROP INDEX fbref.idx_fbref_fixtures_created_at;

DROP INDEX fbref.idx_fbref_fixtures_home_code_season;

DROP INDEX fbref.idx_fbref_fixtures_home_team;

DROP INDEX fbref.idx_fbref_fixtures_time_home_away;

DROP INDEX fbref.idx_fbref_fixtures_updated_at;

DROP TABLE fbref.fbref_fixtures;

DROP INDEX fbref.idx_market_odds_away_team;

DROP INDEX fbref.idx_market_odds_created_at;

DROP INDEX fbref.idx_market_odds_home_team;

DROP INDEX fbref.idx_market_odds_kickoff_time;

DROP INDEX fbref.idx_market_odds_updated_at;

DROP TABLE fbref.market_odds;

DROP INDEX fbref.idx_comp_sync_state_created_at;

DROP INDEX fbref.idx_comp_sync_state_season_comp_code;

DROP INDEX fbref.idx_comp_sync_state_updated_at;

DROP TABLE fbref.comp_sync_state;

ALTER TABLE leagues ADD COLUMN country_code VARCHAR(3);

ALTER TABLE leagues ADD COLUMN country_name VARCHAR(100);

ALTER TABLE leagues DROP CONSTRAINT leagues_name_key;

ALTER TABLE site_leagues ADD COLUMN country_code VARCHAR(3);

ALTER TABLE site_leagues ADD COLUMN country_name VARCHAR(100);

ALTER TABLE site_leagues ALTER COLUMN league_name SET NOT NULL;

ALTER TABLE site_leagues DROP CONSTRAINT site_leagues_ref_league_id_fkey;

ALTER TABLE public.site_leagues ADD FOREIGN KEY(ref_league_id) REFERENCES public.leagues (id);

DROP INDEX fotmob.idx_fixture_raw_data_created_at;

DROP INDEX fotmob.idx_fixture_raw_data_not_fetched;

DROP INDEX fotmob.idx_fixture_raw_data_not_parsed;

DROP INDEX fotmob.idx_fixture_raw_data_refetch;

DROP INDEX fotmob.idx_fixture_raw_data_updated_at;

CREATE INDEX idx_fixture_raw_created_at ON fotmob.fixture_raw (created_at);

CREATE INDEX idx_fixture_raw_not_fetched ON fotmob.fixture_raw (match_date) WHERE is_fetched = false;

CREATE INDEX idx_fixture_raw_not_parsed ON fotmob.fixture_raw (match_date) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_fixture_raw_refetch ON fotmob.fixture_raw (is_parsed, confirm_count, match_date);

CREATE INDEX idx_fixture_raw_updated_at ON fotmob.fixture_raw (updated_at);

ALTER TABLE fotmob.fixtures ALTER COLUMN league_name TYPE VARCHAR(200);

DROP INDEX fotmob.idx_match_raw_data_created_at;

DROP INDEX fotmob.idx_match_raw_data_kickoff_time;

DROP INDEX fotmob.idx_match_raw_data_not_fetched;

DROP INDEX fotmob.idx_match_raw_data_not_parsed;

DROP INDEX fotmob.idx_match_raw_data_refetch;

DROP INDEX fotmob.idx_match_raw_data_updated_at;

CREATE INDEX idx_match_raw_created_at ON fotmob.match_raw (created_at);

CREATE INDEX idx_match_raw_kickoff_time ON fotmob.match_raw (kickoff_time);

CREATE INDEX idx_match_raw_not_fetched ON fotmob.match_raw (match_id) WHERE is_fetched = false;

CREATE INDEX idx_match_raw_not_parsed ON fotmob.match_raw (kickoff_time) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_match_raw_refetch ON fotmob.match_raw (is_parsed, confirm_count, kickoff_time);

CREATE INDEX idx_match_raw_updated_at ON fotmob.match_raw (updated_at);

ALTER TABLE pinnacle.fixtures ALTER COLUMN league_name TYPE VARCHAR(200);

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

INSERT INTO alembic_version (version_num) VALUES ('84eb03fe348c') RETURNING alembic_version.version_num;

COMMIT;

