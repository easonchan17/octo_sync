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

COMMIT;

