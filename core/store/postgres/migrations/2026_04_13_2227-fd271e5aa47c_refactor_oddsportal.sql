BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 19d04cf87682

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

CREATE TABLE fotmob.fixture_raw (
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
    confirm_count INTEGER, 
    json_body JSONB NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (match_date)
);

CREATE INDEX idx_fixture_raw_created_at ON fotmob.fixture_raw (created_at);

CREATE INDEX idx_fixture_raw_not_fetched ON fotmob.fixture_raw (match_date) WHERE is_fetched = false;

CREATE INDEX idx_fixture_raw_not_parsed ON fotmob.fixture_raw (match_date) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_fixture_raw_refetch ON fotmob.fixture_raw (is_parsed, confirm_count, match_date);

CREATE INDEX idx_fixture_raw_updated_at ON fotmob.fixture_raw (updated_at);

CREATE TABLE fotmob.fixtures (
    id SERIAL NOT NULL, 
    match_id INTEGER NOT NULL, 
    league_name VARCHAR(200) NOT NULL, 
    league_id INTEGER NOT NULL, 
    kickoff_time TIMESTAMP WITH TIME ZONE NOT NULL, 
    round VARCHAR(128), 
    page_url VARCHAR(512) NOT NULL, 
    home_team VARCHAR(100) NOT NULL, 
    home_id INTEGER NOT NULL, 
    away_team VARCHAR(100) NOT NULL, 
    away_id INTEGER NOT NULL, 
    home_score INTEGER, 
    away_score INTEGER, 
    match_status INTEGER NOT NULL, 
    raw_fetch_date DATE, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (match_id)
);

CREATE INDEX idx_fixtures_away_id ON fotmob.fixtures (away_id);

CREATE INDEX idx_fixtures_created_at ON fotmob.fixtures (created_at);

CREATE INDEX idx_fixtures_home_id ON fotmob.fixtures (home_id);

CREATE INDEX idx_fixtures_kickoff_time ON fotmob.fixtures (kickoff_time);

CREATE INDEX idx_fixtures_league_id_kickoff_time ON fotmob.fixtures (league_id, kickoff_time);

CREATE INDEX idx_fixtures_raw_fetch_date ON fotmob.fixtures (raw_fetch_date);

CREATE INDEX idx_fixtures_updated_at ON fotmob.fixtures (updated_at);

CREATE TABLE fotmob.match_lineups (
    id SERIAL NOT NULL, 
    match_id INTEGER NOT NULL, 
    team_id INTEGER NOT NULL, 
    team_name VARCHAR(100), 
    country_code VARCHAR(3), 
    country_name VARCHAR(100), 
    opta_id VARCHAR(64), 
    member_id INTEGER, 
    member_name VARCHAR(128) NOT NULL, 
    age INTEGER, 
    shirt_number INTEGER, 
    position_id INTEGER, 
    usual_playing_position_id INTEGER, 
    is_starter BOOLEAN, 
    is_sub BOOLEAN, 
    is_captain BOOLEAN, 
    is_coach BOOLEAN, 
    rating FLOAT, 
    horizontal_layout JSONB, 
    vertical_layout JSONB, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_match_lineups_match_team_opta_member UNIQUE (match_id, team_id, opta_id, member_id, member_name)
);

CREATE INDEX idx_match_lineups_created_at ON fotmob.match_lineups (created_at);

CREATE INDEX idx_match_lineups_match_id_team_id ON fotmob.match_lineups (match_id, team_id);

CREATE INDEX idx_match_lineups_match_team_opta_member ON fotmob.match_lineups (match_id, team_id, opta_id, member_id, member_name);

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
    blocked_shots INTEGER, 
    touches INTEGER, 
    touches_opp_box INTEGER, 
    passes_into_final_third INTEGER, 
    passes INTEGER, 
    passes_completed INTEGER, 
    long_passes INTEGER, 
    long_passes_completed INTEGER, 
    dispossessed INTEGER, 
    chances_created INTEGER, 
    goals INTEGER, 
    assists INTEGER, 
    npxg FLOAT, 
    xg FLOAT, 
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
    confirm_count INTEGER, 
    json_body JSONB NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (match_id)
);

CREATE INDEX idx_match_raw_created_at ON fotmob.match_raw (created_at);

CREATE INDEX idx_match_raw_kickoff_time ON fotmob.match_raw (kickoff_time);

CREATE INDEX idx_match_raw_not_fetched ON fotmob.match_raw (match_id) WHERE is_fetched = false;

CREATE INDEX idx_match_raw_not_parsed ON fotmob.match_raw (kickoff_time) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_match_raw_refetch ON fotmob.match_raw (is_parsed, confirm_count, kickoff_time);

CREATE INDEX idx_match_raw_updated_at ON fotmob.match_raw (updated_at);

CREATE TABLE fotmob.match_stats (
    id SERIAL NOT NULL, 
    match_id INTEGER NOT NULL, 
    lineup_type VARCHAR(16), 
    home_formation VARCHAR(16), 
    away_formation VARCHAR(16), 
    home_possession INTEGER, 
    away_possession INTEGER, 
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

CREATE TABLE pinnacle.fixtures (
    id BIGSERIAL NOT NULL, 
    match_id BIGINT NOT NULL, 
    kickoff_time TIMESTAMP WITH TIME ZONE NOT NULL, 
    league_id INTEGER NOT NULL, 
    league_name VARCHAR(200) NOT NULL, 
    home_team VARCHAR(100) NOT NULL, 
    away_team VARCHAR(100) NOT NULL, 
    fixture_id INTEGER, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (fixture_id), 
    UNIQUE (match_id)
);

COMMENT ON COLUMN pinnacle.fixtures.fixture_id IS 'References fotmob_fixtures.match_id';

CREATE INDEX idx_fixtures_away_team ON pinnacle.fixtures (away_team);

CREATE INDEX idx_fixtures_created_at ON pinnacle.fixtures (created_at);

CREATE INDEX idx_fixtures_home_team ON pinnacle.fixtures (home_team);

CREATE INDEX idx_fixtures_kickoff_time ON pinnacle.fixtures (kickoff_time);

CREATE INDEX idx_fixtures_league_id ON pinnacle.fixtures (league_id);

CREATE INDEX idx_fixtures_updated_at ON pinnacle.fixtures (updated_at);

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

CREATE TABLE pinnacle.moneylines (
    id BIGSERIAL NOT NULL, 
    match_id BIGINT NOT NULL, 
    period INTEGER NOT NULL, 
    home_price INTEGER NOT NULL, 
    home_odds NUMERIC(7, 3) NOT NULL, 
    draw_price INTEGER NOT NULL, 
    draw_odds NUMERIC(7, 3) NOT NULL, 
    away_price INTEGER NOT NULL, 
    away_odds NUMERIC(7, 3) NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX idx_moneylines_created_at ON pinnacle.moneylines (created_at);

CREATE INDEX idx_moneylines_match_id ON pinnacle.moneylines (match_id);

CREATE INDEX idx_moneylines_updated_at ON pinnacle.moneylines (updated_at);

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

CREATE TABLE pinnacle.spreads (
    id BIGSERIAL NOT NULL, 
    match_id BIGINT NOT NULL, 
    period INTEGER NOT NULL, 
    handicap NUMERIC(5, 2) NOT NULL, 
    home_price INTEGER NOT NULL, 
    home_odds NUMERIC(7, 3) NOT NULL, 
    away_price INTEGER NOT NULL, 
    away_odds NUMERIC(7, 3) NOT NULL, 
    is_alternate BOOLEAN NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX idx_spreads_created_at ON pinnacle.spreads (created_at);

CREATE INDEX idx_spreads_match_id ON pinnacle.spreads (match_id);

CREATE INDEX idx_spreads_updated_at ON pinnacle.spreads (updated_at);

CREATE TABLE public.leagues (
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

CREATE INDEX idx_leagues_created_at ON public.leagues (created_at);

CREATE INDEX idx_leagues_priority ON public.leagues (priority);

CREATE INDEX idx_leagues_updated_at ON public.leagues (updated_at);

CREATE TABLE public.sites (
    id SERIAL NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    url TEXT NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (name)
);

CREATE INDEX idx_sites_created_at ON public.sites (created_at);

CREATE INDEX idx_sites_updated_at ON public.sites (updated_at);

CREATE INDEX idx_sites_url ON public.sites (url);

CREATE TABLE public.sys_vals (
    key VARCHAR(128) NOT NULL, 
    val_datetime TIMESTAMP WITH TIME ZONE, 
    val_int INTEGER, 
    val_json JSONB, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (key)
);

CREATE INDEX idx_sys_vals_created_at ON public.sys_vals (created_at);

CREATE INDEX idx_sys_vals_updated_at ON public.sys_vals (updated_at);

CREATE TABLE public.training_records (
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

CREATE INDEX idx_training_records_created_at ON public.training_records (created_at);

CREATE INDEX idx_training_records_dataset_name ON public.training_records (dataset_name);

CREATE INDEX idx_training_records_model_type ON public.training_records (model_type);

CREATE INDEX idx_training_records_test_score ON public.training_records (test_score);

CREATE INDEX idx_training_records_train_score ON public.training_records (train_score);

CREATE INDEX idx_training_records_updated_at ON public.training_records (updated_at);

CREATE TABLE public.site_leagues (
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
    FOREIGN KEY(ref_league_id) REFERENCES public.leagues (id), 
    CONSTRAINT uq_site_league_league_id_site UNIQUE (ref_league_id, site_name), 
    CONSTRAINT uq_site_league_site_code UNIQUE (site_name, league_id)
);

CREATE INDEX idx_site_leagues_created_at ON public.site_leagues (created_at);

CREATE INDEX idx_site_leagues_updated_at ON public.site_leagues (updated_at);

INSERT INTO alembic_version (version_num) VALUES ('19d04cf87682') RETURNING alembic_version.version_num;

-- Running upgrade 19d04cf87682 -> 7c900c42d186

ALTER TABLE site_leagues DROP CONSTRAINT site_leagues_ref_league_id_fkey;

ALTER TABLE public.site_leagues ADD FOREIGN KEY(ref_league_id) REFERENCES public.leagues (id);

UPDATE alembic_version SET version_num='7c900c42d186' WHERE alembic_version.version_num = '19d04cf87682';

-- Running upgrade 7c900c42d186 -> 393b08f729d2

ALTER TABLE site_leagues DROP CONSTRAINT site_leagues_ref_league_id_fkey;

ALTER TABLE public.site_leagues ADD CONSTRAINT site_leagues_ref_league_id_fkey FOREIGN KEY(ref_league_id) REFERENCES public.leagues (id);

UPDATE alembic_version SET version_num='393b08f729d2' WHERE alembic_version.version_num = '7c900c42d186';

-- Running upgrade 393b08f729d2 -> 79e11ed98413

ALTER TABLE site_leagues DROP CONSTRAINT site_leagues_ref_league_id_fkey;

ALTER TABLE public.site_leagues ADD CONSTRAINT site_leagues_ref_league_id_fkey FOREIGN KEY(ref_league_id) REFERENCES public.leagues (id);

UPDATE alembic_version SET version_num='79e11ed98413' WHERE alembic_version.version_num = '393b08f729d2';

-- Running upgrade 79e11ed98413 -> fa48827845d9

ALTER TABLE site_leagues DROP CONSTRAINT site_leagues_ref_league_id_fkey;

ALTER TABLE site_leagues ADD CONSTRAINT site_leagues_ref_league_id_fkey FOREIGN KEY(ref_league_id) REFERENCES public.leagues (id);

UPDATE alembic_version SET version_num='fa48827845d9' WHERE alembic_version.version_num = '79e11ed98413';

-- Running upgrade fa48827845d9 -> c14e69af41e7

ALTER TABLE site_leagues DROP CONSTRAINT site_leagues_ref_league_id_fkey;

ALTER TABLE site_leagues ADD CONSTRAINT site_leagues_ref_league_id_fkey FOREIGN KEY(ref_league_id) REFERENCES public.leagues (id);

UPDATE alembic_version SET version_num='c14e69af41e7' WHERE alembic_version.version_num = 'fa48827845d9';

-- Running upgrade c14e69af41e7 -> c8b5d2a14835

CREATE TABLE oddsportal.league_pages (
    id SERIAL NOT NULL, 
    league_id VARCHAR(64) NOT NULL, 
    league_name VARCHAR(200) NOT NULL, 
    page_url VARCHAR(512) NOT NULL, 
    country_name VARCHAR(128) NOT NULL, 
    country_code VARCHAR(8), 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (league_id)
);

CREATE INDEX idx_league_pages_country_name ON oddsportal.league_pages (country_name);

CREATE INDEX idx_league_pages_created_at ON oddsportal.league_pages (created_at);

CREATE INDEX idx_league_pages_updated_at ON oddsportal.league_pages (updated_at);

UPDATE alembic_version SET version_num='c8b5d2a14835' WHERE alembic_version.version_num = 'c14e69af41e7';

-- Running upgrade c8b5d2a14835 -> a0be7a7f6b95

CREATE TABLE oddsportal.fixture_fetch_progress (
    id SERIAL NOT NULL, 
    league_id INTEGER NOT NULL, 
    season INTEGER NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    total_page INTEGER NOT NULL, 
    page_size INTEGER NOT NULL, 
    page INTEGER NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_fixture_fetch_progress_league_season UNIQUE (league_id, season)
);

CREATE INDEX idx_fixture_fetch_progress_created_at ON oddsportal.fixture_fetch_progress (created_at);

CREATE INDEX idx_fixture_fetch_progress_updated_at ON oddsportal.fixture_fetch_progress (updated_at);

CREATE TABLE oddsportal.fixture_raw (
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
    confirm_count INTEGER, 
    json_body JSONB NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_fixture_raw_league_season_page UNIQUE (league_id, season, page)
);

CREATE INDEX idx_fixture_raw_created_at ON oddsportal.fixture_raw (created_at);

CREATE INDEX idx_fixture_raw_not_parsed ON oddsportal.fixture_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_fixture_raw_updated_at ON oddsportal.fixture_raw (updated_at);

DROP INDEX idx_leagues_created_at;

DROP INDEX idx_leagues_priority;

DROP INDEX idx_leagues_updated_at;

CREATE INDEX idx_canonical_leagues_created_at ON canonical_leagues (created_at);

CREATE INDEX idx_canonical_leagues_priority ON canonical_leagues (priority);

CREATE INDEX idx_canonical_leagues_updated_at ON canonical_leagues (updated_at);

ALTER TABLE oddsportal.leagues ALTER COLUMN league_id TYPE INTEGER USING league_id::integer;

ALTER TABLE oddsportal.leagues ALTER COLUMN country_code SET NOT NULL;

DROP INDEX oddsportal.idx_league_pages_country_name;

DROP INDEX oddsportal.idx_league_pages_created_at;

DROP INDEX oddsportal.idx_league_pages_updated_at;

CREATE INDEX idx_leagues_country_name ON oddsportal.leagues (country_name);

CREATE INDEX idx_leagues_created_at ON oddsportal.leagues (created_at);

CREATE INDEX idx_leagues_updated_at ON oddsportal.leagues (updated_at);

UPDATE alembic_version SET version_num='a0be7a7f6b95' WHERE alembic_version.version_num = 'c8b5d2a14835';

-- Running upgrade a0be7a7f6b95 -> a93b49e9cd82

ALTER TABLE oddsportal.fixture_fetch_progress ADD COLUMN total INTEGER NOT NULL;

UPDATE alembic_version SET version_num='a93b49e9cd82' WHERE alembic_version.version_num = 'a0be7a7f6b95';

-- Running upgrade a93b49e9cd82 -> 1cb3d0827e69

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
    confirm_count INTEGER, 
    html_body TEXT NOT NULL, 
    encoding VARCHAR(20), 
    PRIMARY KEY (id), 
    UNIQUE (league_id)
);

CREATE INDEX idx_season_raw_created_at ON oddsportal.season_raw (created_at);

CREATE INDEX idx_season_raw_not_parsed ON oddsportal.season_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_season_raw_updated_at ON oddsportal.season_raw (updated_at);

UPDATE alembic_version SET version_num='1cb3d0827e69' WHERE alembic_version.version_num = 'a93b49e9cd82';

-- Running upgrade 1cb3d0827e69 -> 322e400a3d70

ALTER TABLE oddsportal.leagues ADD COLUMN min_season INTEGER;

ALTER TABLE oddsportal.leagues ADD COLUMN max_season INTEGER;

UPDATE alembic_version SET version_num='322e400a3d70' WHERE alembic_version.version_num = '1cb3d0827e69';

-- Running upgrade 322e400a3d70 -> ddde115d5f4b

CREATE TABLE oddsportal.fixtures (
    id SERIAL NOT NULL, 
    match_id INTEGER NOT NULL, 
    league_id INTEGER NOT NULL, 
    season INTEGER NOT NULL, 
    kickoff_time TIMESTAMP WITH TIME ZONE NOT NULL, 
    home_id INTEGER NOT NULL, 
    away_id INTEGER NOT NULL, 
    home_name VARCHAR(200) NOT NULL, 
    away_name VARCHAR(200) NOT NULL, 
    match_url VARCHAR(512), 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (match_id)
);

CREATE INDEX idx_fixtures_created_at ON oddsportal.fixtures (created_at);

CREATE INDEX idx_fixtures_league_id ON oddsportal.fixtures (league_id);

CREATE INDEX idx_fixtures_season ON oddsportal.fixtures (season);

CREATE INDEX idx_fixtures_updated_at ON oddsportal.fixtures (updated_at);

UPDATE alembic_version SET version_num='ddde115d5f4b' WHERE alembic_version.version_num = '322e400a3d70';

-- Running upgrade ddde115d5f4b -> f0efc0cafe92

CREATE TABLE oddsportal.odds_raw (
    id SERIAL NOT NULL, 
    match_id INTEGER NOT NULL, 
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
    UNIQUE (match_id)
);

CREATE INDEX idx_odds_raw_created_at ON oddsportal.odds_raw (created_at);

CREATE INDEX idx_odds_raw_not_parsed ON oddsportal.odds_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_odds_raw_updated_at ON oddsportal.odds_raw (updated_at);

UPDATE alembic_version SET version_num='f0efc0cafe92' WHERE alembic_version.version_num = 'ddde115d5f4b';

-- Running upgrade f0efc0cafe92 -> fd4691e4ecd4

ALTER TABLE oddsportal.odds_raw ADD COLUMN betting_type_id INTEGER NOT NULL;

ALTER TABLE oddsportal.odds_raw ADD COLUMN scope_id INTEGER NOT NULL;

ALTER TABLE oddsportal.odds_raw DROP CONSTRAINT odds_raw_match_id_key;

ALTER TABLE oddsportal.odds_raw ADD CONSTRAINT uq_odds_raw_match_betting_scope UNIQUE (match_id, betting_type_id, scope_id);

UPDATE alembic_version SET version_num='fd4691e4ecd4' WHERE alembic_version.version_num = 'f0efc0cafe92';

-- Running upgrade fd4691e4ecd4 -> a3b5bc4eee6b

ALTER TABLE oddsportal.fixtures ADD COLUMN home_url VARCHAR(512);

ALTER TABLE oddsportal.fixtures ADD COLUMN away_url VARCHAR(512);

UPDATE alembic_version SET version_num='a3b5bc4eee6b' WHERE alembic_version.version_num = 'fd4691e4ecd4';

-- Running upgrade a3b5bc4eee6b -> 2b2283d755ba

ALTER TABLE oddsportal.fixtures ADD COLUMN match_code VARCHAR(64) NOT NULL;

ALTER TABLE oddsportal.fixtures ADD COLUMN home_code VARCHAR(200) NOT NULL;

ALTER TABLE oddsportal.fixtures ADD COLUMN away_code VARCHAR(200) NOT NULL;

ALTER TABLE oddsportal.fixtures ALTER COLUMN match_url SET NOT NULL;

ALTER TABLE oddsportal.fixtures ALTER COLUMN home_url SET NOT NULL;

ALTER TABLE oddsportal.fixtures ALTER COLUMN away_url SET NOT NULL;

UPDATE alembic_version SET version_num='2b2283d755ba' WHERE alembic_version.version_num = 'a3b5bc4eee6b';

-- Running upgrade 2b2283d755ba -> bcb15653efb6

CREATE TABLE oddsportal.odds_1x2 (
    id SERIAL NOT NULL, 
    match_id INTEGER NOT NULL, 
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
    CONSTRAINT uq_odds_1x2_match_betting_scope_bookmaker_quote_type UNIQUE (match_id, betting_type_id, scope_id, bookmaker_id, quote_type)
);

CREATE INDEX idx_odds_1x2_created_at ON oddsportal.odds_1x2 (created_at);

CREATE INDEX idx_odds_1x2_match_id ON oddsportal.odds_1x2 (match_id);

CREATE INDEX idx_odds_1x2_updated_at ON oddsportal.odds_1x2 (updated_at);

CREATE TABLE oddsportal.odds_ah (
    id SERIAL NOT NULL, 
    match_id INTEGER NOT NULL, 
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
    CONSTRAINT uq_odds_ah_match_betting_scope_bookmaker_quote_type_handicap UNIQUE (match_id, betting_type_id, scope_id, bookmaker_id, quote_type, handicap)
);

CREATE INDEX idx_odds_ah_created_at ON oddsportal.odds_ah (created_at);

CREATE INDEX idx_odds_ah_match_id ON oddsportal.odds_ah (match_id);

CREATE INDEX idx_odds_ah_updated_at ON oddsportal.odds_ah (updated_at);

UPDATE alembic_version SET version_num='bcb15653efb6' WHERE alembic_version.version_num = '2b2283d755ba';

-- Running upgrade bcb15653efb6 -> 4e59913be0f7

DROP INDEX football_data.idx_league_raw_created_at;

DROP INDEX football_data.idx_league_raw_not_parsed;

DROP INDEX football_data.idx_league_raw_updated_at;

DROP TABLE football_data.league_raw;

DROP INDEX football_data.idx_country_raw_created_at;

DROP INDEX football_data.idx_country_raw_not_parsed;

DROP INDEX football_data.idx_country_raw_updated_at;

DROP TABLE football_data.country_raw;

DROP INDEX football_data.idx_odds_created_at;

DROP INDEX football_data.idx_odds_kickoff_time;

DROP INDEX football_data.idx_odds_match_code;

DROP INDEX football_data.idx_odds_match_id;

DROP INDEX football_data.idx_odds_updated_at;

DROP TABLE football_data.odds;

DROP INDEX pinnacle.idx_moneylines_created_at;

DROP INDEX pinnacle.idx_moneylines_match_id;

DROP INDEX pinnacle.idx_moneylines_updated_at;

DROP TABLE pinnacle.moneylines;

DROP INDEX football_data.idx_league_odds_created_at;

DROP INDEX football_data.idx_league_odds_season;

DROP INDEX football_data.idx_league_odds_updated_at;

DROP TABLE football_data.league_odds;

DROP INDEX pinnacle.idx_odds_raw_created_at;

DROP INDEX pinnacle.idx_odds_raw_updated_at;

DROP TABLE pinnacle.odds_raw;

DROP INDEX football_data.idx_countries_created_at;

DROP INDEX football_data.idx_countries_updated_at;

DROP TABLE football_data.countries;

DROP INDEX football_data.idx_odds_raw_created_at;

DROP INDEX football_data.idx_odds_raw_not_parsed;

DROP INDEX football_data.idx_odds_raw_updated_at;

DROP TABLE football_data.odds_raw;

DROP INDEX pinnacle.idx_spreads_created_at;

DROP INDEX pinnacle.idx_spreads_match_id;

DROP INDEX pinnacle.idx_spreads_updated_at;

DROP TABLE pinnacle.spreads;

DROP INDEX pinnacle.idx_fixtures_away_team;

DROP INDEX pinnacle.idx_fixtures_created_at;

DROP INDEX pinnacle.idx_fixtures_home_team;

DROP INDEX pinnacle.idx_fixtures_kickoff_time;

DROP INDEX pinnacle.idx_fixtures_league_id;

DROP INDEX pinnacle.idx_fixtures_updated_at;

DROP TABLE pinnacle.fixtures;

DROP INDEX pinnacle.idx_league_raw_created_at;

DROP INDEX pinnacle.idx_league_raw_updated_at;

DROP TABLE pinnacle.league_raw;

UPDATE alembic_version SET version_num='4e59913be0f7' WHERE alembic_version.version_num = 'bcb15653efb6';

-- Running upgrade 4e59913be0f7 -> 36c173e67e3a

ALTER TABLE oddsportal.fixtures ADD COLUMN ref_match_id INTEGER;

UPDATE alembic_version SET version_num='36c173e67e3a' WHERE alembic_version.version_num = '4e59913be0f7';

-- Running upgrade 36c173e67e3a -> 18d89c810b4a

ALTER TABLE oddsportal.fixtures ADD UNIQUE (ref_match_id);

UPDATE alembic_version SET version_num='18d89c810b4a' WHERE alembic_version.version_num = '36c173e67e3a';

-- Running upgrade 18d89c810b4a -> c213b427422a

CREATE TABLE oddsportal.fixture_mapping_logs (
    id SERIAL NOT NULL, 
    match_id INTEGER NOT NULL, 
    attempts INTEGER NOT NULL, 
    last_attempted_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    next_attempt_at TIMESTAMP WITH TIME ZONE, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (match_id)
);

CREATE INDEX idx_fixture_mapping_logs_created_at ON oddsportal.fixture_mapping_logs (created_at);

CREATE INDEX idx_fixture_mapping_logs_updated_at ON oddsportal.fixture_mapping_logs (updated_at);

ALTER TABLE sys_vals ADD COLUMN module VARCHAR(64);

UPDATE alembic_version SET version_num='c213b427422a' WHERE alembic_version.version_num = '18d89c810b4a';

-- Running upgrade c213b427422a -> 0dabcbab524f

CREATE TABLE oddsportal.fixture_upcoming_raw (
    id SERIAL NOT NULL, 
    league_id INTEGER NOT NULL, 
    league_name VARCHAR(200) NOT NULL, 
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
    confirm_count INTEGER, 
    html_body TEXT NOT NULL, 
    encoding VARCHAR(20), 
    PRIMARY KEY (id), 
    UNIQUE (league_id)
);

CREATE INDEX idx_fixture_upcoming_raw_created_at ON oddsportal.fixture_upcoming_raw (created_at);

CREATE INDEX idx_fixture_upcoming_raw_not_parsed ON oddsportal.fixture_upcoming_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_fixture_upcoming_raw_updated_at ON oddsportal.fixture_upcoming_raw (updated_at);

UPDATE alembic_version SET version_num='0dabcbab524f' WHERE alembic_version.version_num = 'c213b427422a';

-- Running upgrade 0dabcbab524f -> be357a462005

DROP INDEX oddsportal.idx_fixture_history_progress_created_at;

DROP INDEX oddsportal.idx_fixture_history_progress_updated_at;

ALTER TABLE oddsportal.history_fixture_progress DROP CONSTRAINT uq_fixture_history_progress_league_season;

CREATE INDEX idx_history_fixture_progress_created_at ON oddsportal.history_fixture_progress (created_at);

CREATE INDEX idx_history_fixture_progress_updated_at ON oddsportal.history_fixture_progress (updated_at);

ALTER TABLE oddsportal.history_fixture_progress ADD CONSTRAINT uq_history_fixture_progress_league_season UNIQUE (league_id, season);

DROP INDEX oddsportal.idx_fixture_history_raw_created_at;

DROP INDEX oddsportal.idx_fixture_history_raw_not_parsed;

DROP INDEX oddsportal.idx_fixture_history_raw_updated_at;

ALTER TABLE oddsportal.history_fixture_raw DROP CONSTRAINT uq_fixture_history_raw_league_season_page;

CREATE INDEX idx_history_fixture_raw_created_at ON oddsportal.history_fixture_raw (created_at);

CREATE INDEX idx_history_fixture_raw_not_parsed ON oddsportal.history_fixture_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_history_fixture_raw_updated_at ON oddsportal.history_fixture_raw (updated_at);

ALTER TABLE oddsportal.history_fixture_raw ADD CONSTRAINT uq_history_fixture_raw_league_season_page UNIQUE (league_id, season, page);

DROP INDEX oddsportal.idx_fixture_upcoming_raw_created_at;

DROP INDEX oddsportal.idx_fixture_upcoming_raw_not_parsed;

DROP INDEX oddsportal.idx_fixture_upcoming_raw_updated_at;

CREATE INDEX idx_upcoming_fixture_raw_created_at ON oddsportal.upcoming_fixture_raw (created_at);

CREATE INDEX idx_upcoming_fixture_raw_not_parsed ON oddsportal.upcoming_fixture_raw (is_parsed) WHERE is_fetched = true and is_parsed = false;

CREATE INDEX idx_upcoming_fixture_raw_updated_at ON oddsportal.upcoming_fixture_raw (updated_at);

UPDATE alembic_version SET version_num='be357a462005' WHERE alembic_version.version_num = '0dabcbab524f';

-- Running upgrade be357a462005 -> 145a4b081f17

ALTER TABLE oddsportal.fixtures ALTER COLUMN home_id DROP NOT NULL;

ALTER TABLE oddsportal.fixtures ALTER COLUMN away_id DROP NOT NULL;

UPDATE alembic_version SET version_num='145a4b081f17' WHERE alembic_version.version_num = 'be357a462005';

-- Running upgrade 145a4b081f17 -> 29d8f6a3895d

ALTER TABLE oddsportal.fixtures ALTER COLUMN home_url DROP NOT NULL;

ALTER TABLE oddsportal.fixtures ALTER COLUMN home_code DROP NOT NULL;

ALTER TABLE oddsportal.fixtures ALTER COLUMN away_url DROP NOT NULL;

ALTER TABLE oddsportal.fixtures ALTER COLUMN away_code DROP NOT NULL;

UPDATE alembic_version SET version_num='29d8f6a3895d' WHERE alembic_version.version_num = '145a4b081f17';

-- Running upgrade 29d8f6a3895d -> 428189d40382

ALTER TABLE oddsportal.fixtures ALTER COLUMN match_id DROP NOT NULL;

ALTER TABLE oddsportal.fixtures ADD UNIQUE (match_code);

UPDATE alembic_version SET version_num='428189d40382' WHERE alembic_version.version_num = '29d8f6a3895d';

-- Running upgrade 428189d40382 -> 5dee08db94a6

ALTER TABLE oddsportal.fixture_mapping_logs ADD COLUMN match_code VARCHAR(64) NOT NULL;

ALTER TABLE oddsportal.fixture_mapping_logs DROP CONSTRAINT fixture_mapping_logs_match_id_key;

ALTER TABLE oddsportal.fixture_mapping_logs ADD UNIQUE (match_code);

ALTER TABLE oddsportal.fixture_mapping_logs DROP COLUMN match_id;

ALTER TABLE oddsportal.upcoming_fixture_raw ADD COLUMN next_fetch_at TIMESTAMP WITH TIME ZONE;

UPDATE alembic_version SET version_num='5dee08db94a6' WHERE alembic_version.version_num = '428189d40382';

-- Running upgrade 5dee08db94a6 -> fd271e5aa47c

CREATE INDEX idx_fixtures_kickoff_time ON oddsportal.fixtures (kickoff_time);

ALTER TABLE oddsportal.odds_1x2 ADD COLUMN match_code VARCHAR(64) NOT NULL;

DROP INDEX oddsportal.idx_odds_1x2_match_id;

ALTER TABLE oddsportal.odds_1x2 DROP CONSTRAINT uq_odds_1x2_match_betting_scope_bookmaker_quote_type;

ALTER TABLE oddsportal.odds_1x2 ADD CONSTRAINT uq_odds_1x2_match_betting_scope_bookmaker_quote_type UNIQUE (match_code, betting_type_id, scope_id, bookmaker_id, quote_type);

CREATE INDEX idx_odds_1x2_match_code ON oddsportal.odds_1x2 (match_code);

ALTER TABLE oddsportal.odds_1x2 DROP COLUMN match_id;

ALTER TABLE oddsportal.odds_ah ADD COLUMN match_code VARCHAR(64) NOT NULL;

DROP INDEX oddsportal.idx_odds_ah_match_id;

ALTER TABLE oddsportal.odds_ah DROP CONSTRAINT uq_odds_ah_match_betting_scope_bookmaker_quote_type_handicap;

ALTER TABLE oddsportal.odds_ah ADD CONSTRAINT uq_odds_ah_match_betting_scope_bookmaker_quote_type_handicap UNIQUE (match_code, betting_type_id, scope_id, bookmaker_id, quote_type, handicap);

CREATE INDEX idx_odds_ah_match_code ON oddsportal.odds_ah (match_code);

ALTER TABLE oddsportal.odds_ah DROP COLUMN match_id;

ALTER TABLE oddsportal.odds_raw ADD COLUMN match_code VARCHAR(64) NOT NULL;

ALTER TABLE oddsportal.odds_raw DROP CONSTRAINT uq_odds_raw_match_betting_scope;

ALTER TABLE oddsportal.odds_raw ADD CONSTRAINT uq_odds_raw_match_betting_scope UNIQUE (match_code, betting_type_id, scope_id);

ALTER TABLE oddsportal.odds_raw DROP COLUMN match_id;

ALTER TABLE oddsportal.upcoming_fixture_raw DROP COLUMN league_name;

UPDATE alembic_version SET version_num='fd271e5aa47c' WHERE alembic_version.version_num = '5dee08db94a6';

COMMIT;

