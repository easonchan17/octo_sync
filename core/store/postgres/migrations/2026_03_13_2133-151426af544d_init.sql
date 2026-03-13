BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 151426af544d

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

DROP INDEX fbref.idx_shooting_created_at;

DROP INDEX fbref.idx_shooting_kickoff_time;

DROP INDEX fbref.idx_shooting_match_team;

DROP INDEX fbref.idx_shooting_updated_at;

DROP TABLE fbref.shooting;

DROP INDEX fbref.idx_market_odds_away_team;

DROP INDEX fbref.idx_market_odds_created_at;

DROP INDEX fbref.idx_market_odds_home_team;

DROP INDEX fbref.idx_market_odds_kickoff_time;

DROP INDEX fbref.idx_market_odds_updated_at;

DROP TABLE fbref.market_odds;

DROP INDEX fbref.idx_goal_keeping_created_at;

DROP INDEX fbref.idx_goal_keeping_kickoff_time;

DROP INDEX fbref.idx_goal_keeping_match_team;

DROP INDEX fbref.idx_goal_keeping_updated_at;

DROP TABLE fbref.goal_keeping;

DROP INDEX fbref.idx_player_match_stats_created_at;

DROP INDEX fbref.idx_player_match_stats_match_player;

DROP INDEX fbref.idx_player_match_stats_team_code;

DROP INDEX fbref.idx_player_match_stats_updated_at;

DROP TABLE fbref.player_match_stats;

DROP INDEX fbref.idx_comp_teams_comp_name;

DROP INDEX fbref.idx_comp_teams_created_at;

DROP INDEX fbref.idx_comp_teams_season_comp_code_team_code;

DROP INDEX fbref.idx_comp_teams_team_code;

DROP INDEX fbref.idx_comp_teams_team_name;

DROP INDEX fbref.idx_comp_teams_updated_at;

DROP TABLE fbref.comp_teams;

DROP INDEX fbref.idx_passing_created_at;

DROP INDEX fbref.idx_passing_kickoff_time;

DROP INDEX fbref.idx_passing_match_team;

DROP INDEX fbref.idx_passing_updated_at;

DROP TABLE fbref.passing;

DROP INDEX fbref.idx_comp_sync_state_created_at;

DROP INDEX fbref.idx_comp_sync_state_season_comp_code;

DROP INDEX fbref.idx_comp_sync_state_updated_at;

DROP TABLE fbref.comp_sync_state;

DROP INDEX fbref.idx_fbref_fixtures_away_code_season;

DROP INDEX fbref.idx_fbref_fixtures_away_team;

DROP INDEX fbref.idx_fbref_fixtures_comp_code;

DROP INDEX fbref.idx_fbref_fixtures_created_at;

DROP INDEX fbref.idx_fbref_fixtures_home_code_season;

DROP INDEX fbref.idx_fbref_fixtures_home_team;

DROP INDEX fbref.idx_fbref_fixtures_time_home_away;

DROP INDEX fbref.idx_fbref_fixtures_updated_at;

DROP TABLE fbref.fbref_fixtures;

DROP INDEX fbref.idx_player_stats_sync_state_created_at;

DROP INDEX fbref.idx_player_stats_sync_state_updated_at;

DROP TABLE fbref.player_stats_sync_state;

DROP INDEX football_data.idx_match_odds_created_at;

DROP INDEX football_data.idx_match_odds_kickoff_time;

DROP INDEX football_data.idx_match_odds_match_code;

DROP INDEX football_data.idx_match_odds_match_id;

DROP INDEX football_data.idx_match_odds_updated_at;

DROP TABLE football_data.match_odds;

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

DROP INDEX fbref.idx_gca_created_at;

DROP INDEX fbref.idx_gca_kickoff_time;

DROP INDEX fbref.idx_gca_match_team;

DROP INDEX fbref.idx_gca_updated_at;

DROP TABLE fbref.gca;

DROP INDEX fbref.idx_match_stats_sync_state_created_at;

DROP INDEX fbref.idx_match_stats_sync_state_team_code_season;

DROP INDEX fbref.idx_match_stats_sync_state_updated_at;

DROP TABLE fbref.match_stats_sync_state;

DROP INDEX fbref.idx_defensive_actions_created_at;

DROP INDEX fbref.idx_defensive_actions_kickoff_time;

DROP INDEX fbref.idx_defensive_actions_match_team;

DROP INDEX fbref.idx_defensive_actions_updated_at;

DROP TABLE fbref.defensive_actions;

ALTER TABLE site_leagues DROP CONSTRAINT site_leagues_ref_league_id_fkey;

ALTER TABLE public.site_leagues ADD FOREIGN KEY(ref_league_id) REFERENCES public.leagues (id);

ALTER TABLE football_data.league_odds ALTER COLUMN season TYPE INTEGER USING season::integer;

ALTER TABLE football_data.odds_raw ADD COLUMN season INTEGER NOT NULL;

ALTER TABLE football_data.odds_raw ALTER COLUMN league_id TYPE VARCHAR(100);

DROP INDEX football_data.idx_odds_raw_league_id;

ALTER TABLE football_data.odds_raw DROP CONSTRAINT uq_odds_raw_source_url;

ALTER TABLE football_data.odds_raw ADD CONSTRAINT uq_odds_raw_season_league UNIQUE (season, league_id);

ALTER TABLE football_data.odds_raw DROP COLUMN csv_body;

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

DROP INDEX pinnacle.idx_league_raw_data_created_at;

DROP INDEX pinnacle.idx_league_raw_data_updated_at;

CREATE INDEX idx_league_raw_created_at ON pinnacle.league_raw (created_at);

CREATE INDEX idx_league_raw_updated_at ON pinnacle.league_raw (updated_at);

DROP INDEX pinnacle.idx_odds_raw_data_created_at;

DROP INDEX pinnacle.idx_odds_raw_data_updated_at;

CREATE INDEX idx_odds_raw_created_at ON pinnacle.odds_raw (created_at);

CREATE INDEX idx_odds_raw_updated_at ON pinnacle.odds_raw (updated_at);

INSERT INTO alembic_version (version_num) VALUES ('151426af544d') RETURNING alembic_version.version_num;

COMMIT;

