BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 52f6dfe3663e

CREATE TABLE canonical_leagues (
    id BIGSERIAL NOT NULL, 
    country_code VARCHAR(3), 
    country_name VARCHAR(100), 
    name VARCHAR(200) NOT NULL, 
    priority INTEGER, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX idx_canonical_leagues_created_at ON canonical_leagues (created_at);

CREATE INDEX idx_canonical_leagues_priority ON canonical_leagues (priority);

CREATE INDEX idx_canonical_leagues_updated_at ON canonical_leagues (updated_at);

CREATE TABLE fotmob.active_fixture_raw (
    id SERIAL NOT NULL, 
    match_date DATE NOT NULL, 
    last_kickoff_time TIMESTAMP WITH TIME ZONE, 
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
    next_fetch_at TIMESTAMP WITH TIME ZONE, 
    json_body JSONB NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (match_date)
);

CREATE INDEX idx_active_fixture_raw_created_at ON fotmob.active_fixture_raw (created_at);

CREATE INDEX idx_active_fixture_raw_next_fetch_at ON fotmob.active_fixture_raw (next_fetch_at);

CREATE INDEX idx_active_fixture_raw_not_fetched ON fotmob.active_fixture_raw (match_date) WHERE is_fetched = false;

CREATE INDEX idx_active_fixture_raw_not_parsed ON fotmob.active_fixture_raw (match_date) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_active_fixture_raw_updated_at ON fotmob.active_fixture_raw (updated_at);

CREATE TABLE fotmob.elo_rating_build_logs (
    id SERIAL NOT NULL, 
    from_checkpoint TIMESTAMP WITH TIME ZONE NOT NULL, 
    checkpoint TIMESTAMP WITH TIME ZONE NOT NULL, 
    match_count INTEGER, 
    next_build_at TIMESTAMP WITH TIME ZONE, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (checkpoint)
);

CREATE INDEX idx_elo_rating_build_logs_checkpoint ON fotmob.elo_rating_build_logs (checkpoint);

CREATE INDEX idx_elo_rating_build_logs_created_at ON fotmob.elo_rating_build_logs (created_at);

CREATE INDEX idx_elo_rating_build_logs_updated_at ON fotmob.elo_rating_build_logs (updated_at);

CREATE TABLE fotmob.elo_ratings (
    id SERIAL NOT NULL, 
    team_id INTEGER NOT NULL, 
    match_id INTEGER NOT NULL, 
    kickoff_time TIMESTAMP WITH TIME ZONE NOT NULL, 
    season INTEGER NOT NULL, 
    pre_rating NUMERIC(10, 4) NOT NULL, 
    expected_score NUMERIC(10, 4) NOT NULL, 
    post_rating NUMERIC(10, 4) NOT NULL, 
    game_count INTEGER NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_elo_ratings_team_match UNIQUE (team_id, match_id)
);

CREATE INDEX idx_elo_ratings_created_at ON fotmob.elo_ratings (created_at);

CREATE INDEX idx_elo_ratings_kickoff_time ON fotmob.elo_ratings (kickoff_time);

CREATE INDEX idx_elo_ratings_season ON fotmob.elo_ratings (season);

CREATE INDEX idx_elo_ratings_team_match ON fotmob.elo_ratings (team_id, match_id);

CREATE INDEX idx_elo_ratings_team_time ON fotmob.elo_ratings (team_id, kickoff_time);

CREATE INDEX idx_elo_ratings_updated_at ON fotmob.elo_ratings (updated_at);

CREATE TABLE fotmob.fixtures (
    id SERIAL NOT NULL, 
    match_code VARCHAR(64) NOT NULL, 
    match_id INTEGER NOT NULL, 
    league_name VARCHAR(200) NOT NULL, 
    league_id INTEGER NOT NULL, 
    kickoff_time TIMESTAMP WITH TIME ZONE NOT NULL, 
    round VARCHAR(128), 
    page_url VARCHAR(512) NOT NULL, 
    home_team VARCHAR(100) NOT NULL, 
    home_id INTEGER NOT NULL, 
    home_code VARCHAR(16) NOT NULL, 
    away_team VARCHAR(100) NOT NULL, 
    away_id INTEGER NOT NULL, 
    away_code VARCHAR(16) NOT NULL, 
    season INTEGER, 
    home_score INTEGER, 
    away_score INTEGER, 
    match_status INTEGER NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (match_code), 
    UNIQUE (match_id)
);

CREATE INDEX idx_fixtures_away_id ON fotmob.fixtures (away_id);

CREATE INDEX idx_fixtures_created_at ON fotmob.fixtures (created_at);

CREATE INDEX idx_fixtures_home_id ON fotmob.fixtures (home_id);

CREATE INDEX idx_fixtures_kickoff_time ON fotmob.fixtures (kickoff_time);

CREATE INDEX idx_fixtures_league_id_kickoff_time ON fotmob.fixtures (league_id, kickoff_time);

CREATE INDEX idx_fixtures_league_id_season ON fotmob.fixtures (league_id, season);

CREATE INDEX idx_fixtures_updated_at ON fotmob.fixtures (updated_at);

CREATE TABLE fotmob.form_cache_build_logs (
    id SERIAL NOT NULL, 
    built_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    checkpoint TIMESTAMP WITH TIME ZONE NOT NULL, 
    match_count INTEGER NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX idx_form_cache_build_logs_built_at ON fotmob.form_cache_build_logs (built_at);

CREATE INDEX idx_form_cache_build_logs_created_at ON fotmob.form_cache_build_logs (created_at);

CREATE INDEX idx_form_cache_build_logs_updated_at ON fotmob.form_cache_build_logs (updated_at);

CREATE TABLE fotmob.history_fixture_raw (
    id SERIAL NOT NULL, 
    league_id INTEGER NOT NULL, 
    season INTEGER NOT NULL, 
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
    next_fetch_at TIMESTAMP WITH TIME ZONE, 
    json_body JSONB NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_history_fixture_raw_league_season UNIQUE (league_id, season)
);

CREATE INDEX idx_history_fixture_raw_created_at ON fotmob.history_fixture_raw (created_at);

CREATE INDEX idx_history_fixture_raw_next_fetch_at ON fotmob.history_fixture_raw (next_fetch_at);

CREATE INDEX idx_history_fixture_raw_not_parsed ON fotmob.history_fixture_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_history_fixture_raw_updated_at ON fotmob.history_fixture_raw (updated_at);

CREATE TABLE fotmob.league_raw (
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
    next_fetch_at TIMESTAMP WITH TIME ZONE, 
    json_body JSONB NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (sport)
);

CREATE INDEX idx_fotmob_league_raw_created_at ON fotmob.league_raw (created_at);

CREATE INDEX idx_fotmob_league_raw_next_fetch_at ON fotmob.league_raw (next_fetch_at);

CREATE INDEX idx_fotmob_league_raw_not_parsed ON fotmob.league_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_fotmob_league_raw_updated_at ON fotmob.league_raw (updated_at);

CREATE TABLE fotmob.leagues (
    id SERIAL NOT NULL, 
    league_id INTEGER NOT NULL, 
    league_name VARCHAR(200) NOT NULL, 
    page_url VARCHAR(512) NOT NULL, 
    country_name VARCHAR(128) NOT NULL, 
    country_code VARCHAR(8) NOT NULL, 
    min_season INTEGER, 
    max_season INTEGER, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (league_id)
);

CREATE INDEX idx_fotmob_leagues_country_name ON fotmob.leagues (country_name);

CREATE INDEX idx_fotmob_leagues_created_at ON fotmob.leagues (created_at);

CREATE INDEX idx_fotmob_leagues_updated_at ON fotmob.leagues (updated_at);

CREATE TABLE fotmob.match_lineups (
    id SERIAL NOT NULL, 
    match_id INTEGER NOT NULL, 
    team_id INTEGER NOT NULL, 
    team_name VARCHAR(100), 
    member_id INTEGER NOT NULL, 
    member_name VARCHAR(128) NOT NULL, 
    opta_id VARCHAR(64), 
    age INTEGER, 
    country_code VARCHAR(3), 
    country_name VARCHAR(100), 
    shirt_number INTEGER, 
    position_id INTEGER, 
    position VARCHAR(3), 
    usual_playing_position_id INTEGER, 
    role SMALLINT, 
    is_captain BOOLEAN, 
    rating FLOAT, 
    market_value BIGINT, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_match_lineups_match_team_member_id UNIQUE (match_id, team_id, member_id)
);

CREATE INDEX idx_match_lineups_created_at ON fotmob.match_lineups (created_at);

CREATE INDEX idx_match_lineups_updated_at ON fotmob.match_lineups (updated_at);

CREATE TABLE fotmob.match_player_stats (
    id SERIAL NOT NULL, 
    match_id INTEGER NOT NULL, 
    opta_id VARCHAR(64) NOT NULL, 
    player_id INTEGER NOT NULL, 
    player_name VARCHAR(128) NOT NULL, 
    rating FLOAT, 
    fantasy_points INTEGER, 
    minutes_played INTEGER, 
    shots INTEGER, 
    shots_on_target INTEGER, 
    shots_blocked INTEGER, 
    shots_inside_box INTEGER, 
    shots_freekick INTEGER, 
    shots_fastbreak INTEGER, 
    shots_setpiece INTEGER, 
    shots_corner INTEGER, 
    shots_header INTEGER, 
    shots_penalty INTEGER, 
    shots_individual_play INTEGER, 
    shots_throw_in_set_piece INTEGER, 
    goals INTEGER, 
    goals_inside_box INTEGER, 
    goals_freekick INTEGER, 
    goals_fastbreak INTEGER, 
    goals_setpiece INTEGER, 
    goals_corner INTEGER, 
    goals_header INTEGER, 
    goals_penalty INTEGER, 
    goals_individual_play INTEGER, 
    goals_throw_in_set_piece INTEGER, 
    xg_inside_box FLOAT, 
    xg_freekick FLOAT, 
    xg_fastbreak FLOAT, 
    xg_setpiece FLOAT, 
    xg_corner FLOAT, 
    xg_header FLOAT, 
    xg_individual_play FLOAT, 
    xg_throw_in_set_piece FLOAT, 
    xgot_inside_box FLOAT, 
    xgot_freekick FLOAT, 
    xgot_fastbreak FLOAT, 
    xgot_setpiece FLOAT, 
    xgot_corner FLOAT, 
    xgot_header FLOAT, 
    xgot_individual_play FLOAT, 
    xgot_throw_in_set_piece FLOAT, 
    touches INTEGER, 
    touches_opp_box INTEGER, 
    passes_into_final_third INTEGER, 
    passes INTEGER, 
    passes_completed INTEGER, 
    long_passes INTEGER, 
    long_passes_completed INTEGER, 
    dispossessed INTEGER, 
    chances_created INTEGER, 
    assists INTEGER, 
    xg FLOAT, 
    npxg FLOAT, 
    xgot FLOAT, 
    xa FLOAT, 
    tackles INTEGER, 
    blocks INTEGER, 
    clearances INTEGER, 
    headed_clearance INTEGER, 
    interceptions INTEGER, 
    recoveries INTEGER, 
    dribbled_past INTEGER, 
    duels_won INTEGER, 
    duels_lost INTEGER, 
    ground_duels INTEGER, 
    ground_duels_won INTEGER, 
    aerials INTEGER, 
    aerials_won INTEGER, 
    fouls_suffered INTEGER, 
    fouls_committed INTEGER, 
    saves INTEGER, 
    goals_conceded INTEGER, 
    xgot_faced FLOAT, 
    goals_prevented FLOAT, 
    keeper_sweeper INTEGER, 
    keeper_high_claim INTEGER, 
    keeper_diving_save INTEGER, 
    saves_inside_box INTEGER, 
    punches INTEGER, 
    throws INTEGER, 
    team_id INTEGER, 
    position_id INTEGER, 
    usual_position INTEGER, 
    is_goalkeeper BOOLEAN, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_match_player_stats_match_id_opta_id_player_id_player_name UNIQUE (match_id, opta_id, player_id, player_name)
);

CREATE INDEX idx_match_player_stats_created_at ON fotmob.match_player_stats (created_at);

CREATE INDEX idx_match_player_stats_match_id_opta_id_player_id_player_name ON fotmob.match_player_stats (match_id, opta_id, player_id, player_name);

CREATE INDEX idx_match_player_stats_updated_at ON fotmob.match_player_stats (updated_at);

CREATE TABLE fotmob.match_raw (
    id SERIAL NOT NULL, 
    match_id INTEGER NOT NULL, 
    kickoff_time TIMESTAMP WITH TIME ZONE NOT NULL, 
    match_status INTEGER, 
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
    next_fetch_at TIMESTAMP WITH TIME ZONE, 
    json_body JSONB NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (match_id)
);

CREATE INDEX idx_match_raw_created_at ON fotmob.match_raw (created_at);

CREATE INDEX idx_match_raw_kickoff_time ON fotmob.match_raw (kickoff_time);

CREATE INDEX idx_match_raw_next_fetch_at ON fotmob.match_raw (next_fetch_at);

CREATE INDEX idx_match_raw_not_fetched ON fotmob.match_raw (match_id) WHERE is_fetched = false;

CREATE INDEX idx_match_raw_not_parsed ON fotmob.match_raw (kickoff_time) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_match_raw_updated_at ON fotmob.match_raw (updated_at);

CREATE TABLE fotmob.match_shot_stats (
    id SERIAL NOT NULL, 
    match_id INTEGER NOT NULL, 
    event_id BIGINT NOT NULL, 
    period VARCHAR(16), 
    min INTEGER, 
    min_added INTEGER, 
    x FLOAT, 
    y FLOAT, 
    team_id INTEGER, 
    keeper_id INTEGER, 
    player_id INTEGER, 
    shot_type VARCHAR(32), 
    event_type VARCHAR(32), 
    situation VARCHAR(32), 
    is_blocked BOOLEAN, 
    is_own_goal BOOLEAN, 
    is_on_target BOOLEAN, 
    is_saved_off_line BOOLEAN, 
    is_inside_box BOOLEAN, 
    xg FLOAT, 
    xgot FLOAT, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_match_shot_stats_match_id_event_id UNIQUE (match_id, event_id)
);

CREATE INDEX idx_match_shot_stats_created_at ON fotmob.match_shot_stats (created_at);

CREATE INDEX idx_match_shot_stats_match_team_player ON fotmob.match_shot_stats (match_id, team_id, player_id);

CREATE INDEX idx_match_shot_stats_updated_at ON fotmob.match_shot_stats (updated_at);

CREATE TABLE fotmob.match_stats (
    id SERIAL NOT NULL, 
    match_id INTEGER NOT NULL, 
    lineup_type VARCHAR(16), 
    home_formation VARCHAR(16), 
    away_formation VARCHAR(16), 
    home_possession INTEGER, 
    away_possession INTEGER, 
    home_goals_penalty INTEGER, 
    away_goals_penalty INTEGER, 
    home_shots INTEGER, 
    away_shots INTEGER, 
    home_shots_on_target INTEGER, 
    away_shots_on_target INTEGER, 
    home_shots_off_target INTEGER, 
    away_shots_off_target INTEGER, 
    home_hit_woodwork INTEGER, 
    away_hit_woodwork INTEGER, 
    home_shots_inside_box INTEGER, 
    away_shots_inside_box INTEGER, 
    home_shots_outside_box INTEGER, 
    away_shots_outside_box INTEGER, 
    home_big_chances INTEGER, 
    away_big_chances INTEGER, 
    home_big_chances_missed INTEGER, 
    away_big_chances_missed INTEGER, 
    home_xg FLOAT, 
    away_xg FLOAT, 
    home_xg_open_play FLOAT, 
    away_xg_open_play FLOAT, 
    home_xg_set_play FLOAT, 
    away_xg_set_play FLOAT, 
    home_npxg FLOAT, 
    away_npxg FLOAT, 
    home_xg_on_target FLOAT, 
    away_xg_on_target FLOAT, 
    home_passes INTEGER, 
    away_passes INTEGER, 
    home_passes_completed INTEGER, 
    away_passes_completed INTEGER, 
    home_own_half_passes INTEGER, 
    away_own_half_passes INTEGER, 
    home_opp_half_passes INTEGER, 
    away_opp_half_passes INTEGER, 
    home_long_passes INTEGER, 
    away_long_passes INTEGER, 
    home_long_passes_completed INTEGER, 
    away_long_passes_completed INTEGER, 
    home_crosses INTEGER, 
    away_crosses INTEGER, 
    home_crosses_completed INTEGER, 
    away_crosses_completed INTEGER, 
    home_throws INTEGER, 
    away_throws INTEGER, 
    home_corners INTEGER, 
    away_corners INTEGER, 
    home_tackles INTEGER, 
    away_tackles INTEGER, 
    home_interceptions INTEGER, 
    away_interceptions INTEGER, 
    home_shot_blocks INTEGER, 
    away_shot_blocks INTEGER, 
    home_clearances INTEGER, 
    away_clearances INTEGER, 
    home_keeper_saves INTEGER, 
    away_keeper_saves INTEGER, 
    home_duels_won INTEGER, 
    away_duels_won INTEGER, 
    home_ground_duels INTEGER, 
    away_ground_duels INTEGER, 
    home_ground_duels_won INTEGER, 
    away_ground_duels_won INTEGER, 
    home_aerials INTEGER, 
    away_aerials INTEGER, 
    home_aerials_won INTEGER, 
    away_aerials_won INTEGER, 
    home_dribbles INTEGER, 
    away_dribbles INTEGER, 
    home_dribbles_completed INTEGER, 
    away_dribbles_completed INTEGER, 
    home_offsides INTEGER, 
    away_offsides INTEGER, 
    home_fouls_committed INTEGER, 
    away_fouls_committed INTEGER, 
    home_yellow_cards INTEGER, 
    away_yellow_cards INTEGER, 
    home_red_cards INTEGER, 
    away_red_cards INTEGER, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (match_id)
);

CREATE INDEX idx_match_stats_created_at ON fotmob.match_stats (created_at);

CREATE INDEX idx_match_stats_match_id ON fotmob.match_stats (match_id);

CREATE INDEX idx_match_stats_updated_at ON fotmob.match_stats (updated_at);

CREATE TABLE fotmob.season_raw (
    id SERIAL NOT NULL, 
    league_id INTEGER NOT NULL, 
    league_name VARCHAR(200) NOT NULL, 
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
    next_fetch_at TIMESTAMP WITH TIME ZONE, 
    json_body JSONB NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (league_id)
);

CREATE INDEX idx_fotmob_season_raw_created_at ON fotmob.season_raw (created_at);

CREATE INDEX idx_fotmob_season_raw_next_fetch_at ON fotmob.season_raw (next_fetch_at);

CREATE INDEX idx_fotmob_season_raw_not_parsed ON fotmob.season_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_fotmob_season_raw_updated_at ON fotmob.season_raw (updated_at);

CREATE TABLE oddsportal.fixture_mapping_logs (
    id SERIAL NOT NULL, 
    match_code VARCHAR(64) NOT NULL, 
    attempts INTEGER NOT NULL, 
    last_attempted_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    next_attempt_at TIMESTAMP WITH TIME ZONE, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (match_code)
);

CREATE INDEX idx_fixture_mapping_logs_created_at ON oddsportal.fixture_mapping_logs (created_at);

CREATE INDEX idx_fixture_mapping_logs_updated_at ON oddsportal.fixture_mapping_logs (updated_at);

CREATE TABLE oddsportal.fixtures (
    id SERIAL NOT NULL, 
    match_id INTEGER, 
    league_id INTEGER NOT NULL, 
    season INTEGER NOT NULL, 
    kickoff_time TIMESTAMP WITH TIME ZONE NOT NULL, 
    home_id INTEGER, 
    away_id INTEGER, 
    home_name VARCHAR(200) NOT NULL, 
    away_name VARCHAR(200) NOT NULL, 
    match_url VARCHAR(512) NOT NULL, 
    match_code VARCHAR(64) NOT NULL, 
    home_url VARCHAR(512), 
    home_code VARCHAR(200), 
    away_url VARCHAR(512), 
    away_code VARCHAR(200), 
    ref_match_id INTEGER, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (match_code), 
    UNIQUE (match_id), 
    UNIQUE (ref_match_id)
);

CREATE INDEX idx_fixtures_created_at ON oddsportal.fixtures (created_at);

CREATE INDEX idx_fixtures_kickoff_time ON oddsportal.fixtures (kickoff_time);

CREATE INDEX idx_fixtures_league_id ON oddsportal.fixtures (league_id);

CREATE INDEX idx_fixtures_season ON oddsportal.fixtures (season);

CREATE INDEX idx_fixtures_updated_at ON oddsportal.fixtures (updated_at);

CREATE TABLE oddsportal.history_fixture_progress (
    id SERIAL NOT NULL, 
    league_id INTEGER NOT NULL, 
    season INTEGER NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    total INTEGER NOT NULL, 
    total_page INTEGER NOT NULL, 
    page_size INTEGER NOT NULL, 
    page INTEGER NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_history_fixture_progress_league_season UNIQUE (league_id, season)
);

CREATE INDEX idx_history_fixture_progress_created_at ON oddsportal.history_fixture_progress (created_at);

CREATE INDEX idx_history_fixture_progress_updated_at ON oddsportal.history_fixture_progress (updated_at);

CREATE TABLE oddsportal.history_fixture_raw (
    id SERIAL NOT NULL, 
    league_id INTEGER NOT NULL, 
    season INTEGER NOT NULL, 
    page INTEGER NOT NULL, 
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
    next_fetch_at TIMESTAMP WITH TIME ZONE, 
    json_body JSONB NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_history_fixture_raw_league_season_page UNIQUE (league_id, season, page)
);

CREATE INDEX idx_history_fixture_raw_created_at ON oddsportal.history_fixture_raw (created_at);

CREATE INDEX idx_history_fixture_raw_next_fetch_at ON oddsportal.history_fixture_raw (next_fetch_at);

CREATE INDEX idx_history_fixture_raw_not_parsed ON oddsportal.history_fixture_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_history_fixture_raw_updated_at ON oddsportal.history_fixture_raw (updated_at);

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
    next_fetch_at TIMESTAMP WITH TIME ZONE, 
    json_body JSONB NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (sport)
);

CREATE INDEX idx_league_raw_created_at ON oddsportal.league_raw (created_at);

CREATE INDEX idx_league_raw_next_fetch_at ON oddsportal.league_raw (next_fetch_at);

CREATE INDEX idx_league_raw_not_parsed ON oddsportal.league_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_league_raw_updated_at ON oddsportal.league_raw (updated_at);

CREATE TABLE oddsportal.leagues (
    id SERIAL NOT NULL, 
    league_id INTEGER NOT NULL, 
    league_name VARCHAR(200) NOT NULL, 
    page_url VARCHAR(512) NOT NULL, 
    country_name VARCHAR(128) NOT NULL, 
    country_code VARCHAR(8) NOT NULL, 
    min_season INTEGER, 
    max_season INTEGER, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (league_id)
);

CREATE INDEX idx_leagues_country_name ON oddsportal.leagues (country_name);

CREATE INDEX idx_leagues_created_at ON oddsportal.leagues (created_at);

CREATE INDEX idx_leagues_updated_at ON oddsportal.leagues (updated_at);

CREATE TABLE oddsportal.odds_1x2 (
    id SERIAL NOT NULL, 
    match_code VARCHAR(64) NOT NULL, 
    betting_type_id INTEGER NOT NULL, 
    scope_id INTEGER NOT NULL, 
    bookmaker_id INTEGER NOT NULL, 
    quote_type VARCHAR(8) NOT NULL, 
    closing_home_odds FLOAT, 
    closing_draw_odds FLOAT, 
    closing_away_odds FLOAT, 
    opening_home_odds FLOAT, 
    opening_draw_odds FLOAT, 
    opening_away_odds FLOAT, 
    closing_home_volume INTEGER, 
    closing_draw_volume INTEGER, 
    closing_away_volume INTEGER, 
    opening_home_volume INTEGER, 
    opening_draw_volume INTEGER, 
    opening_away_volume INTEGER, 
    home_movement VARCHAR(8), 
    draw_movement VARCHAR(8), 
    away_movement VARCHAR(8), 
    closing_home_change_time TIMESTAMP WITH TIME ZONE, 
    closing_draw_change_time TIMESTAMP WITH TIME ZONE, 
    closing_away_change_time TIMESTAMP WITH TIME ZONE, 
    opening_home_change_time TIMESTAMP WITH TIME ZONE, 
    opening_draw_change_time TIMESTAMP WITH TIME ZONE, 
    opening_away_change_time TIMESTAMP WITH TIME ZONE, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_odds_1x2_match_betting_scope_bookmaker_quote_type UNIQUE (match_code, betting_type_id, scope_id, bookmaker_id, quote_type)
);

CREATE INDEX idx_odds_1x2_created_at ON oddsportal.odds_1x2 (created_at);

CREATE INDEX idx_odds_1x2_match_code ON oddsportal.odds_1x2 (match_code);

CREATE INDEX idx_odds_1x2_match_code_type_scope_quote ON oddsportal.odds_1x2 (match_code, betting_type_id, scope_id, quote_type);

CREATE INDEX idx_odds_1x2_updated_at ON oddsportal.odds_1x2 (updated_at);

CREATE TABLE oddsportal.odds_ah (
    id SERIAL NOT NULL, 
    match_code VARCHAR(64) NOT NULL, 
    betting_type_id INTEGER NOT NULL, 
    scope_id INTEGER NOT NULL, 
    bookmaker_id INTEGER NOT NULL, 
    quote_type VARCHAR(8) NOT NULL, 
    handicap FLOAT, 
    closing_home_odds FLOAT, 
    closing_away_odds FLOAT, 
    opening_handicap FLOAT, 
    opening_home_odds FLOAT, 
    opening_away_odds FLOAT, 
    closing_home_volume INTEGER, 
    closing_away_volume INTEGER, 
    opening_home_volume INTEGER, 
    opening_away_volume INTEGER, 
    home_movement VARCHAR(8), 
    away_movement VARCHAR(8), 
    closing_home_change_time TIMESTAMP WITH TIME ZONE, 
    closing_away_change_time TIMESTAMP WITH TIME ZONE, 
    opening_home_change_time TIMESTAMP WITH TIME ZONE, 
    opening_away_change_time TIMESTAMP WITH TIME ZONE, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_odds_ah_match_betting_scope_bookmaker_quote_type_handicap UNIQUE (match_code, betting_type_id, scope_id, bookmaker_id, quote_type, handicap)
);

CREATE INDEX idx_odds_ah_created_at ON oddsportal.odds_ah (created_at);

CREATE INDEX idx_odds_ah_match_code ON oddsportal.odds_ah (match_code);

CREATE INDEX idx_odds_ah_type_scope_quote_match_bookmaker ON oddsportal.odds_ah (betting_type_id, scope_id, quote_type, match_code, bookmaker_id);

CREATE INDEX idx_odds_ah_updated_at ON oddsportal.odds_ah (updated_at);

CREATE TABLE oddsportal.odds_raw (
    id SERIAL NOT NULL, 
    match_code VARCHAR(64) NOT NULL, 
    betting_type_id INTEGER NOT NULL, 
    scope_id INTEGER NOT NULL, 
    kickoff_time TIMESTAMP WITH TIME ZONE, 
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
    next_fetch_at TIMESTAMP WITH TIME ZONE, 
    json_body JSONB NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_odds_raw_match_betting_scope UNIQUE (match_code, betting_type_id, scope_id)
);

CREATE INDEX idx_odds_raw_created_at ON oddsportal.odds_raw (created_at);

CREATE INDEX idx_odds_raw_next_fetch_at ON oddsportal.odds_raw (next_fetch_at);

CREATE INDEX idx_odds_raw_not_parsed ON oddsportal.odds_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_odds_raw_updated_at ON oddsportal.odds_raw (updated_at);

CREATE TABLE oddsportal.season_raw (
    id SERIAL NOT NULL, 
    league_id INTEGER NOT NULL, 
    league_name VARCHAR(200) NOT NULL, 
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
    next_fetch_at TIMESTAMP WITH TIME ZONE, 
    html_body TEXT NOT NULL, 
    encoding VARCHAR(20), 
    PRIMARY KEY (id), 
    UNIQUE (league_id)
);

CREATE INDEX idx_season_raw_created_at ON oddsportal.season_raw (created_at);

CREATE INDEX idx_season_raw_next_fetch_at ON oddsportal.season_raw (next_fetch_at);

CREATE INDEX idx_season_raw_not_parsed ON oddsportal.season_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_season_raw_updated_at ON oddsportal.season_raw (updated_at);

CREATE TABLE oddsportal.upcoming_fixture_raw (
    id SERIAL NOT NULL, 
    league_id INTEGER NOT NULL, 
    season INTEGER NOT NULL, 
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
    next_fetch_at TIMESTAMP WITH TIME ZONE, 
    html_body TEXT NOT NULL, 
    encoding VARCHAR(20), 
    PRIMARY KEY (id), 
    UNIQUE (league_id)
);

CREATE INDEX idx_upcoming_fixture_raw_created_at ON oddsportal.upcoming_fixture_raw (created_at);

CREATE INDEX idx_upcoming_fixture_raw_next_fetch_at ON oddsportal.upcoming_fixture_raw (next_fetch_at);

CREATE INDEX idx_upcoming_fixture_raw_not_parsed ON oddsportal.upcoming_fixture_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_upcoming_fixture_raw_updated_at ON oddsportal.upcoming_fixture_raw (updated_at);

CREATE TABLE sites (
    id SERIAL NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    url TEXT NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (name)
);

CREATE INDEX idx_sites_created_at ON sites (created_at);

CREATE INDEX idx_sites_updated_at ON sites (updated_at);

CREATE INDEX idx_sites_url ON sites (url);

CREATE TABLE sys_vals (
    module VARCHAR(64) NOT NULL, 
    key VARCHAR(128) NOT NULL, 
    val_datetime TIMESTAMP WITH TIME ZONE, 
    val_int INTEGER, 
    val_json JSONB, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pkey_sys_vals_module_key PRIMARY KEY (module, key)
);

CREATE INDEX idx_sys_vals_created_at ON sys_vals (created_at);

CREATE INDEX idx_sys_vals_updated_at ON sys_vals (updated_at);

CREATE TABLE training_records (
    id SERIAL NOT NULL, 
    model_version VARCHAR(256) NOT NULL, 
    model_type VARCHAR(256) NOT NULL, 
    model_path TEXT NOT NULL, 
    dataset_name VARCHAR(256) NOT NULL, 
    feature_names JSONB NOT NULL, 
    training_params JSONB NOT NULL, 
    best_params JSONB NOT NULL, 
    train_score FLOAT NOT NULL, 
    test_score FLOAT NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (model_version)
);

CREATE INDEX idx_training_records_created_at ON training_records (created_at);

CREATE INDEX idx_training_records_dataset_name ON training_records (dataset_name);

CREATE INDEX idx_training_records_model_type ON training_records (model_type);

CREATE INDEX idx_training_records_test_score ON training_records (test_score);

CREATE INDEX idx_training_records_train_score ON training_records (train_score);

CREATE INDEX idx_training_records_updated_at ON training_records (updated_at);

CREATE TABLE site_leagues (
    id SERIAL NOT NULL, 
    site_name VARCHAR(100) NOT NULL, 
    country_code VARCHAR(3), 
    country_name VARCHAR(100), 
    league_id VARCHAR(100) NOT NULL, 
    league_name VARCHAR(200) NOT NULL, 
    extra_data JSONB, 
    ref_league_id BIGINT, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT site_leagues_ref_league_id_fkey FOREIGN KEY(ref_league_id) REFERENCES canonical_leagues (id), 
    CONSTRAINT uq_site_league_league_id_site UNIQUE (ref_league_id, site_name), 
    CONSTRAINT uq_site_league_site_code UNIQUE (site_name, league_id)
);

CREATE INDEX idx_site_leagues_created_at ON site_leagues (created_at);

CREATE INDEX idx_site_leagues_updated_at ON site_leagues (updated_at);

INSERT INTO alembic_version (version_num) VALUES ('52f6dfe3663e') RETURNING alembic_version.version_num;

-- Running upgrade 52f6dfe3663e -> f63b97641fce

ALTER TABLE oddsportal.history_fixture_progress ADD COLUMN expired_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX idx_history_fixture_progress_expired_at ON oddsportal.history_fixture_progress (expired_at);

ALTER TABLE oddsportal.odds_ah DROP COLUMN opening_handicap;

UPDATE alembic_version SET version_num='f63b97641fce' WHERE alembic_version.version_num = '52f6dfe3663e';

-- Running upgrade f63b97641fce -> e500c77679bd

CREATE TABLE assets (
    id SERIAL NOT NULL, 
    source_url VARCHAR(512) NOT NULL, 
    source_site VARCHAR(16) NOT NULL, 
    asset_type VARCHAR(16) NOT NULL, 
    entity_type VARCHAR(16) NOT NULL, 
    asset_usage VARCHAR(16) NOT NULL, 
    file_name VARCHAR(64) NOT NULL, 
    file_ext VARCHAR(10), 
    is_fetched BOOLEAN, 
    fetch_attempts INTEGER, 
    last_fetch_error TEXT, 
    next_fetch_at TIMESTAMP WITH TIME ZONE, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (source_url)
);

CREATE INDEX idx_assets_created_at ON assets (created_at);

CREATE INDEX idx_assets_pending_fetch ON assets (source_site, next_fetch_at);

CREATE INDEX idx_assets_updated_at ON assets (updated_at);

UPDATE alembic_version SET version_num='e500c77679bd' WHERE alembic_version.version_num = 'f63b97641fce';

-- Running upgrade e500c77679bd -> 1441adc10e24

CREATE TABLE asset_scan_progress (
    id SERIAL NOT NULL, 
    site_name VARCHAR(16) NOT NULL, 
    asset_type VARCHAR(16) NOT NULL, 
    entity_type VARCHAR(16) NOT NULL, 
    asset_usage VARCHAR(16) NOT NULL, 
    last_scanned_id INTEGER NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_site_asset_scan_progress UNIQUE (site_name, asset_type, entity_type, asset_usage)
);

CREATE INDEX idx_asset_scan_progress_created_at ON asset_scan_progress (created_at);

CREATE INDEX idx_asset_scan_progress_updated_at ON asset_scan_progress (updated_at);

UPDATE alembic_version SET version_num='1441adc10e24' WHERE alembic_version.version_num = 'e500c77679bd';

-- Running upgrade 1441adc10e24 -> 069b86d2ef0f

ALTER TABLE site_leagues ALTER COLUMN league_id TYPE INTEGER USING league_id::integer;

UPDATE alembic_version SET version_num='069b86d2ef0f' WHERE alembic_version.version_num = '1441adc10e24';

-- Running upgrade 069b86d2ef0f -> 88ecf687fe6e

ALTER TABLE fotmob.leagues ADD COLUMN valid_seasons JSONB;

ALTER TABLE oddsportal.leagues ADD COLUMN valid_seasons JSONB;

UPDATE alembic_version SET version_num='88ecf687fe6e' WHERE alembic_version.version_num = '069b86d2ef0f';

-- Running upgrade 88ecf687fe6e -> 394ffb958ddd

ALTER TABLE training_records ADD COLUMN is_recommended BOOLEAN DEFAULT false NOT NULL;

ALTER TABLE fotmob.match_lineups ADD COLUMN player_code VARCHAR(16);

UPDATE alembic_version SET version_num='394ffb958ddd' WHERE alembic_version.version_num = '88ecf687fe6e';

-- Running upgrade 394ffb958ddd -> be9f4e64f750

ALTER TABLE fotmob.match_lineups ALTER COLUMN player_code SET NOT NULL;

UPDATE alembic_version SET version_num='be9f4e64f750' WHERE alembic_version.version_num = '394ffb958ddd';

-- Running upgrade be9f4e64f750 -> 18ce00cfc3ff

ALTER TABLE training_records ADD COLUMN model_family VARCHAR(256);

CREATE INDEX idx_training_records_model_family ON training_records (model_family);

UPDATE alembic_version SET version_num='18ce00cfc3ff' WHERE alembic_version.version_num = 'be9f4e64f750';

-- Running upgrade 18ce00cfc3ff -> f4985dde388d

ALTER TABLE training_records ALTER COLUMN model_family SET NOT NULL;

UPDATE alembic_version SET version_num='f4985dde388d' WHERE alembic_version.version_num = '18ce00cfc3ff';

-- Running upgrade f4985dde388d -> b60c23f4a462

ALTER TABLE fotmob.match_shot_stats ADD COLUMN on_goal_shot_x FLOAT;

ALTER TABLE fotmob.match_shot_stats ADD COLUMN on_goal_shot_y FLOAT;

ALTER TABLE fotmob.match_shot_stats ADD COLUMN goal_y FLOAT;

ALTER TABLE fotmob.match_shot_stats ADD COLUMN goal_z FLOAT;

ALTER TABLE fotmob.match_shot_stats ADD COLUMN team_code VARCHAR(16);

ALTER TABLE fotmob.match_shot_stats ADD COLUMN player_code VARCHAR(16);

ALTER TABLE fotmob.match_shot_stats ADD COLUMN player_name VARCHAR(128);

ALTER TABLE fotmob.match_shot_stats ADD COLUMN keeper_code VARCHAR(16);

UPDATE alembic_version SET version_num='b60c23f4a462' WHERE alembic_version.version_num = 'f4985dde388d';

-- Running upgrade b60c23f4a462 -> 1e8d700861d0

ALTER TABLE fotmob.match_lineups ADD COLUMN team_code VARCHAR(16);

ALTER TABLE fotmob.match_shot_stats ALTER COLUMN team_code SET NOT NULL;

ALTER TABLE fotmob.match_shot_stats ALTER COLUMN player_code SET NOT NULL;

ALTER TABLE fotmob.match_shot_stats ALTER COLUMN player_name SET NOT NULL;

UPDATE alembic_version SET version_num='1e8d700861d0' WHERE alembic_version.version_num = 'b60c23f4a462';

-- Running upgrade 1e8d700861d0 -> a1684211cb84

ALTER TABLE fotmob.match_lineups ADD COLUMN player_id INTEGER NOT NULL;

ALTER TABLE fotmob.match_lineups ADD COLUMN player_name VARCHAR(128) NOT NULL;

ALTER TABLE fotmob.match_lineups ALTER COLUMN team_code SET NOT NULL;

ALTER TABLE fotmob.match_lineups ALTER COLUMN team_name SET NOT NULL;

ALTER TABLE fotmob.match_lineups DROP CONSTRAINT uq_match_lineups_match_team_member_id;

ALTER TABLE fotmob.match_lineups ADD CONSTRAINT uq_match_lineups_match_team_player_id UNIQUE (match_id, team_id, player_id);

ALTER TABLE fotmob.match_lineups DROP COLUMN member_name;

ALTER TABLE fotmob.match_lineups DROP COLUMN member_id;

ALTER TABLE fotmob.match_shot_stats ALTER COLUMN team_id SET NOT NULL;

ALTER TABLE fotmob.match_shot_stats ALTER COLUMN player_id SET NOT NULL;

UPDATE alembic_version SET version_num='a1684211cb84' WHERE alembic_version.version_num = '1e8d700861d0';

-- Running upgrade a1684211cb84 -> 90981f1afb14

CREATE TABLE fotmob.match_predictions (
    id BIGSERIAL NOT NULL, 
    match_id INTEGER NOT NULL, 
    match_code VARCHAR(16) NOT NULL, 
    model_version VARCHAR(64) NOT NULL, 
    home_prob FLOAT NOT NULL, 
    draw_prob FLOAT NOT NULL, 
    away_prob FLOAT NOT NULL, 
    prediction SMALLINT NOT NULL, 
    actual_result SMALLINT, 
    is_correct BOOLEAN, 
    predicted_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    next_predict_at TIMESTAMP WITH TIME ZONE, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_match_predictions_match_model UNIQUE (match_code, model_version)
);

CREATE INDEX idx_match_predictions_created_at ON fotmob.match_predictions (created_at);

CREATE INDEX idx_match_predictions_match_id ON fotmob.match_predictions (match_id);

CREATE INDEX idx_match_predictions_predicted_at ON fotmob.match_predictions (predicted_at);

CREATE INDEX idx_match_predictions_updated_at ON fotmob.match_predictions (updated_at);

UPDATE alembic_version SET version_num='90981f1afb14' WHERE alembic_version.version_num = 'a1684211cb84';

-- Running upgrade 90981f1afb14 -> 62ac227eb3a8

CREATE TABLE chat_conversations (
    id BIGSERIAL NOT NULL, 
    conversation_id VARCHAR(64) NOT NULL, 
    user_id VARCHAR(64) NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (conversation_id)
);

CREATE INDEX idx_chat_conversations_created_at ON chat_conversations (created_at);

CREATE INDEX idx_chat_conversations_updated_at ON chat_conversations (updated_at);

CREATE INDEX idx_chat_conversations_user_id ON chat_conversations (user_id);

CREATE TABLE feedback_issues (
    id BIGSERIAL NOT NULL, 
    conversation_id VARCHAR(64) NOT NULL, 
    user_id VARCHAR(64) NOT NULL, 
    title VARCHAR(200) NOT NULL, 
    description TEXT NOT NULL, 
    category VARCHAR(50) NOT NULL, 
    severity VARCHAR(20) NOT NULL, 
    match_code VARCHAR(16), 
    raw_context JSONB, 
    resolved_at TIMESTAMP WITH TIME ZONE, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX idx_feedback_issues_category ON feedback_issues (category);

CREATE INDEX idx_feedback_issues_conversation_id ON feedback_issues (conversation_id);

CREATE INDEX idx_feedback_issues_created_at ON feedback_issues (created_at);

CREATE INDEX idx_feedback_issues_severity ON feedback_issues (severity);

CREATE INDEX idx_feedback_issues_updated_at ON feedback_issues (updated_at);

CREATE INDEX idx_feedback_issues_user_id ON feedback_issues (user_id);

UPDATE alembic_version SET version_num='62ac227eb3a8' WHERE alembic_version.version_num = '90981f1afb14';

-- Running upgrade 62ac227eb3a8 -> caeb90e54990

CREATE TABLE users (
    id BIGSERIAL NOT NULL, 
    email VARCHAR(255) NOT NULL, 
    last_login TIMESTAMP WITH TIME ZONE, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (email)
);

CREATE INDEX idx_users_created_at ON users (created_at);

CREATE INDEX idx_users_last_login ON users (last_login);

CREATE INDEX idx_users_updated_at ON users (updated_at);

UPDATE alembic_version SET version_num='caeb90e54990' WHERE alembic_version.version_num = '62ac227eb3a8';

-- Running upgrade caeb90e54990 -> 1e03fff74720

ALTER TABLE fotmob.fixtures ADD COLUMN "group" VARCHAR(32);

UPDATE alembic_version SET version_num='1e03fff74720' WHERE alembic_version.version_num = 'caeb90e54990';

-- Running upgrade 1e03fff74720 -> d9ee76f3aaa2

ALTER TABLE fotmob.fixtures ADD COLUMN group_name VARCHAR(32);

ALTER TABLE fotmob.fixtures DROP COLUMN "group";

UPDATE alembic_version SET version_num='d9ee76f3aaa2' WHERE alembic_version.version_num = '1e03fff74720';

-- Running upgrade d9ee76f3aaa2 -> 086b977ffe49

ALTER TABLE fotmob.fixtures ADD COLUMN sub_league_id INTEGER;

UPDATE alembic_version SET version_num='086b977ffe49' WHERE alembic_version.version_num = 'd9ee76f3aaa2';

COMMIT;

