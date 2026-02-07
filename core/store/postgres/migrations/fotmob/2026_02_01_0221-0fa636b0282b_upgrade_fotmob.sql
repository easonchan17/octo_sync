BEGIN;

CREATE TABLE public.alembic_version_fotmob (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_fotmob_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 86e0505f9aa6

INSERT INTO public.alembic_version_fotmob (version_num) VALUES ('86e0505f9aa6') RETURNING public.alembic_version_fotmob.version_num;

-- Running upgrade 86e0505f9aa6 -> 360f5d531f86

CREATE TABLE fotmob.daily_sync_state (
    id SERIAL NOT NULL, 
    event_date DATE NOT NULL, 
    sync_flags BIGINT NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE, 
    updated_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    UNIQUE (event_date)
);

CREATE INDEX idx_daily_sync_state_created_at ON fotmob.daily_sync_state (created_at);

CREATE INDEX idx_daily_sync_state_updated_at ON fotmob.daily_sync_state (updated_at);

UPDATE public.alembic_version_fotmob SET version_num='360f5d531f86' WHERE public.alembic_version_fotmob.version_num = '86e0505f9aa6';

-- Running upgrade 360f5d531f86 -> 7eed4ff41092

ALTER TABLE fotmob.daily_sync_state ADD COLUMN details JSONB;

UPDATE public.alembic_version_fotmob SET version_num='7eed4ff41092' WHERE public.alembic_version_fotmob.version_num = '360f5d531f86';

-- Running upgrade 7eed4ff41092 -> e19065840349

CREATE TABLE fotmob.match_stats (
    id SERIAL NOT NULL, 
    match_id INTEGER NOT NULL, 
    home_possession FLOAT, 
    away_possession FLOAT, 
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
    created_at TIMESTAMP WITH TIME ZONE, 
    updated_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    UNIQUE (match_id)
);

CREATE INDEX idx_match_stats_created_at ON fotmob.match_stats (created_at);

CREATE INDEX idx_match_stats_match_id ON fotmob.match_stats (match_id);

CREATE INDEX idx_match_stats_updated_at ON fotmob.match_stats (updated_at);

CREATE TABLE fotmob.match_sync_state (
    id SERIAL NOT NULL, 
    match_id INTEGER NOT NULL, 
    sync_flags BIGINT NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE, 
    updated_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    UNIQUE (match_id)
);

CREATE INDEX idx_match_sync_state_created_at ON fotmob.match_sync_state (created_at);

CREATE INDEX idx_match_sync_state_match_id ON fotmob.match_sync_state (match_id);

CREATE INDEX idx_match_sync_state_updated_at ON fotmob.match_sync_state (updated_at);

CREATE TABLE fotmob.player_stats (
    id SERIAL NOT NULL, 
    match_id INTEGER NOT NULL, 
    team_id INTEGER NOT NULL, 
    player_id INTEGER NOT NULL, 
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
    created_at TIMESTAMP WITH TIME ZONE, 
    updated_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id)
);

CREATE INDEX idx_player_stats_match_id ON fotmob.player_stats (match_id);

CREATE INDEX idx_player_stats_player_id ON fotmob.player_stats (player_id);

CREATE INDEX idx_player_stats_team_id ON fotmob.player_stats (team_id);

UPDATE public.alembic_version_fotmob SET version_num='e19065840349' WHERE public.alembic_version_fotmob.version_num = '7eed4ff41092';

-- Running upgrade e19065840349 -> 37d049f8d7af

ALTER TABLE fotmob.match_stats ALTER COLUMN home_possession TYPE INTEGER;

ALTER TABLE fotmob.match_stats ALTER COLUMN away_possession TYPE INTEGER;

ALTER TABLE fotmob.player_stats ADD COLUMN team_name VARCHAR(100) NOT NULL;

ALTER TABLE fotmob.player_stats ADD COLUMN player_name VARCHAR(128) NOT NULL;

UPDATE public.alembic_version_fotmob SET version_num='37d049f8d7af' WHERE public.alembic_version_fotmob.version_num = 'e19065840349';

-- Running upgrade 37d049f8d7af -> 79d8f90e7542

DROP INDEX fotmob.idx_player_stats_match_id;

DROP INDEX fotmob.idx_player_stats_player_id;

CREATE UNIQUE INDEX idx_player_stats_match_id_player_id ON fotmob.player_stats (match_id, player_id);

UPDATE public.alembic_version_fotmob SET version_num='79d8f90e7542' WHERE public.alembic_version_fotmob.version_num = '37d049f8d7af';

-- Running upgrade 79d8f90e7542 -> 40a90eadde8e

ALTER TABLE fotmob.lineups ADD COLUMN team_id INTEGER NOT NULL;

ALTER TABLE fotmob.lineups ADD COLUMN team_name VARCHAR(100);

ALTER TABLE fotmob.lineups ADD COLUMN player_id INTEGER NOT NULL;

ALTER TABLE fotmob.lineups ADD COLUMN player_name VARCHAR(128) NOT NULL;

ALTER TABLE fotmob.lineups ADD COLUMN shirt_number INTEGER;

ALTER TABLE fotmob.lineups ADD COLUMN position_id INTEGER;

ALTER TABLE fotmob.lineups ADD COLUMN usual_playing_position_id INTEGER;

ALTER TABLE fotmob.lineups ADD COLUMN is_starter BOOLEAN;

ALTER TABLE fotmob.lineups ADD COLUMN is_sub BOOLEAN;

ALTER TABLE fotmob.lineups ADD COLUMN is_captain BOOLEAN;

ALTER TABLE fotmob.lineups ADD COLUMN is_coach BOOLEAN;

ALTER TABLE fotmob.lineups ADD COLUMN rating FLOAT;

ALTER TABLE fotmob.lineups ADD COLUMN horizontal_layout JSONB;

ALTER TABLE fotmob.lineups ADD COLUMN vertical_layout JSONB;

ALTER TABLE fotmob.lineups DROP CONSTRAINT lineups_match_id_key;

CREATE UNIQUE INDEX idx_lineups_match_id_player_id ON fotmob.lineups (match_id, player_id);

CREATE INDEX idx_lineups_match_team ON fotmob.lineups (match_id, team_id);

ALTER TABLE fotmob.lineups DROP COLUMN home_team;

ALTER TABLE fotmob.lineups DROP COLUMN away_team;

ALTER TABLE fotmob.lineups DROP COLUMN kind;

UPDATE public.alembic_version_fotmob SET version_num='40a90eadde8e' WHERE public.alembic_version_fotmob.version_num = '79d8f90e7542';

-- Running upgrade 40a90eadde8e -> 2222a12d7b2c

ALTER TABLE fotmob.lineups ADD COLUMN member_id INTEGER NOT NULL;

ALTER TABLE fotmob.lineups ADD COLUMN member_name VARCHAR(128) NOT NULL;

DROP INDEX fotmob.idx_lineups_match_id_player_id;

DROP INDEX fotmob.idx_lineups_match_team;

CREATE UNIQUE INDEX idx_lineups_match_id_member_id ON fotmob.lineups (match_id, member_id);

CREATE INDEX idx_lineups_match_id_team_id ON fotmob.lineups (match_id, team_id);

ALTER TABLE fotmob.lineups DROP COLUMN player_id;

ALTER TABLE fotmob.lineups DROP COLUMN player_name;

UPDATE public.alembic_version_fotmob SET version_num='2222a12d7b2c' WHERE public.alembic_version_fotmob.version_num = '40a90eadde8e';

-- Running upgrade 2222a12d7b2c -> 8e26af26b182

ALTER TABLE fotmob.lineups ADD COLUMN country_code VARCHAR(3);

ALTER TABLE fotmob.lineups ADD COLUMN country_name VARCHAR(100);

ALTER TABLE fotmob.lineups ADD COLUMN age INTEGER;

UPDATE public.alembic_version_fotmob SET version_num='8e26af26b182' WHERE public.alembic_version_fotmob.version_num = '2222a12d7b2c';

-- Running upgrade 8e26af26b182 -> 82d093d09fc7

ALTER TABLE fotmob.lineups ADD COLUMN opta_id INTEGER;

UPDATE public.alembic_version_fotmob SET version_num='82d093d09fc7' WHERE public.alembic_version_fotmob.version_num = '8e26af26b182';

-- Running upgrade 82d093d09fc7 -> c5a2d01539aa

DROP INDEX fotmob.idx_lineups_match_id_member_id;

CREATE INDEX idx_lineups_match_id_member_id ON fotmob.lineups (match_id, member_id);

CREATE UNIQUE INDEX idx_lineups_match_id_opta_id ON fotmob.lineups (match_id, opta_id);

UPDATE public.alembic_version_fotmob SET version_num='c5a2d01539aa' WHERE public.alembic_version_fotmob.version_num = '82d093d09fc7';

-- Running upgrade c5a2d01539aa -> 65b02601a610

DROP INDEX fotmob.idx_lineups_match_id_member_id;

DROP INDEX fotmob.idx_lineups_match_id_opta_id;

CREATE UNIQUE INDEX idx_lineups_match_id_opta_id_member_id ON fotmob.lineups (match_id, opta_id, member_id);

UPDATE public.alembic_version_fotmob SET version_num='65b02601a610' WHERE public.alembic_version_fotmob.version_num = 'c5a2d01539aa';

-- Running upgrade 65b02601a610 -> 587de2915821

ALTER TABLE fotmob.match_stats ADD COLUMN lineup_type VARCHAR(16);

ALTER TABLE fotmob.match_stats ADD COLUMN home_formation VARCHAR(16);

ALTER TABLE fotmob.match_stats ADD COLUMN away_formation VARCHAR(16);

UPDATE public.alembic_version_fotmob SET version_num='587de2915821' WHERE public.alembic_version_fotmob.version_num = '65b02601a610';

-- Running upgrade 587de2915821 -> d2a383ec597f

ALTER TABLE fotmob.player_stats ADD COLUMN opta_id INTEGER NOT NULL;

DROP INDEX fotmob.idx_player_stats_match_id_player_id;

DROP INDEX fotmob.idx_player_stats_team_id;

CREATE INDEX idx_player_stats_created_at ON fotmob.player_stats (created_at);

CREATE UNIQUE INDEX idx_player_stats_match_id_opta_id_player_id ON fotmob.player_stats (match_id, opta_id, player_id);

CREATE INDEX idx_player_stats_updated_at ON fotmob.player_stats (updated_at);

ALTER TABLE fotmob.player_stats DROP COLUMN team_name;

ALTER TABLE fotmob.player_stats DROP COLUMN team_id;

UPDATE public.alembic_version_fotmob SET version_num='d2a383ec597f' WHERE public.alembic_version_fotmob.version_num = '587de2915821';

-- Running upgrade d2a383ec597f -> 07fe6617efeb

CREATE TABLE fotmob.raw_match_details (
    id SERIAL NOT NULL, 
    match_id INTEGER NOT NULL, 
    kickoff_time TIMESTAMP WITH TIME ZONE NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE, 
    updated_at TIMESTAMP WITH TIME ZONE, 
    source_url VARCHAR(512), 
    is_parsed BOOLEAN, 
    parse_attempts INTEGER, 
    last_error TEXT, 
    json_body JSONB NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (match_id)
);

CREATE INDEX idx_raw_match_details_created_at ON fotmob.raw_match_details (created_at);

CREATE INDEX idx_raw_match_details_match_id ON fotmob.raw_match_details (match_id);

CREATE INDEX idx_raw_match_details_updated_at ON fotmob.raw_match_details (updated_at);

CREATE INDEX ix_fotmob_raw_match_details_is_parsed ON fotmob.raw_match_details (is_parsed);

UPDATE public.alembic_version_fotmob SET version_num='07fe6617efeb' WHERE public.alembic_version_fotmob.version_num = 'd2a383ec597f';

-- Running upgrade 07fe6617efeb -> 21d83d2a07a8

ALTER TABLE fotmob.fotmob_fixtures DROP COLUMN home_xg;

ALTER TABLE fotmob.fotmob_fixtures DROP COLUMN away_xg;

UPDATE public.alembic_version_fotmob SET version_num='21d83d2a07a8' WHERE public.alembic_version_fotmob.version_num = '07fe6617efeb';

-- Running upgrade 21d83d2a07a8 -> 0fa636b0282b

DROP INDEX fotmob.idx_lineups_match_id_opta_id_member_id;

CREATE UNIQUE INDEX idx_lineups_match_id_team_id_opta_id_member_id_member_name ON fotmob.lineups (match_id, team_id, opta_id, member_id, member_name);

DROP INDEX fotmob.idx_player_stats_match_id_opta_id_player_id;

CREATE UNIQUE INDEX idx_player_stats_match_id_opta_id_player_id_player_name ON fotmob.player_stats (match_id, opta_id, player_id, player_name);

DROP INDEX fotmob.idx_raw_match_details_match_id;

CREATE INDEX idx_raw_match_details_kickoff_time ON fotmob.raw_match_details (kickoff_time);

CREATE INDEX idx_raw_match_details_not_parsed ON fotmob.raw_match_details (id) WHERE is_parsed = false;

UPDATE public.alembic_version_fotmob SET version_num='0fa636b0282b' WHERE public.alembic_version_fotmob.version_num = '21d83d2a07a8';

COMMIT;

