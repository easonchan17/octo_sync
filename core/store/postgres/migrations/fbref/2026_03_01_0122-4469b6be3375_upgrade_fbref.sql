BEGIN;

CREATE TABLE public.alembic_version_fbref (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_fbref_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 802e1d974d92

ALTER TABLE fbref.match_results ALTER COLUMN home_gf SET NOT NULL;

ALTER TABLE fbref.match_results ALTER COLUMN away_gf SET NOT NULL;

INSERT INTO public.alembic_version_fbref (version_num) VALUES ('802e1d974d92') RETURNING public.alembic_version_fbref.version_num;

-- Running upgrade 802e1d974d92 -> 27a21462ead4

ALTER TABLE fbref.elo_ratings ADD COLUMN game_count INTEGER NOT NULL;

UPDATE public.alembic_version_fbref SET version_num='27a21462ead4' WHERE public.alembic_version_fbref.version_num = '802e1d974d92';

-- Running upgrade 27a21462ead4 -> c1479d1b40ce

ALTER TABLE fbref.fbref_fixtures ADD COLUMN fixture_id INTEGER;

COMMENT ON COLUMN fbref.fbref_fixtures.fixture_id IS 'References fotmob_fixtures.match_id';

ALTER TABLE fbref.fbref_fixtures ADD UNIQUE (fixture_id);

UPDATE public.alembic_version_fbref SET version_num='c1479d1b40ce' WHERE public.alembic_version_fbref.version_num = '27a21462ead4';

-- Running upgrade c1479d1b40ce -> e8747c4304df

UPDATE public.alembic_version_fbref SET version_num='e8747c4304df' WHERE public.alembic_version_fbref.version_num = 'c1479d1b40ce';

-- Running upgrade e8747c4304df -> df4922965ede

ALTER TABLE fbref.comp_sync_state ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE fbref.comp_sync_state ALTER COLUMN updated_at SET NOT NULL;

DROP INDEX fbref.idx_comp_sync_state_season_comp_code;

CREATE INDEX idx_comp_sync_state_season_comp_code ON fbref.comp_sync_state (season, comp_code);

ALTER TABLE fbref.comp_sync_state ADD CONSTRAINT uq_comp_sync_state_season_comp_code UNIQUE (season, comp_code);

ALTER TABLE fbref.comp_teams ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE fbref.comp_teams ALTER COLUMN updated_at SET NOT NULL;

DROP INDEX fbref.idx_comp_teams_season_comp_code_team_code;

CREATE INDEX idx_comp_teams_season_comp_code_team_code ON fbref.comp_teams (season, comp_code, team_code);

ALTER TABLE fbref.comp_teams ADD CONSTRAINT uq_comp_teams_season_comp_code_team_code UNIQUE (season, comp_code, team_code);

ALTER TABLE fbref.defensive_actions ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE fbref.defensive_actions ALTER COLUMN updated_at SET NOT NULL;

DROP INDEX fbref.idx_defensive_actions_match_team;

CREATE INDEX idx_defensive_actions_match_team ON fbref.defensive_actions (match_code, team_code);

ALTER TABLE fbref.defensive_actions ADD CONSTRAINT uq_defensive_actions_match_team UNIQUE (match_code, team_code);

ALTER TABLE fbref.elo_ratings ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE fbref.elo_ratings ALTER COLUMN updated_at SET NOT NULL;

DROP INDEX fbref.idx_elo_ratings_team_match;

CREATE INDEX idx_elo_ratings_team_match ON fbref.elo_ratings (team_code, match_code);

ALTER TABLE fbref.elo_ratings ADD CONSTRAINT uq_elo_ratings_team_match UNIQUE (team_code, match_code);

ALTER TABLE fbref.fbref_fixtures ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE fbref.fbref_fixtures ALTER COLUMN updated_at SET NOT NULL;

DROP INDEX fbref.idx_fbref_fixtures_time_home_away;

CREATE INDEX idx_fbref_fixtures_time_home_away ON fbref.fbref_fixtures (kickoff_time, home_code, away_code);

ALTER TABLE fbref.fbref_fixtures ADD CONSTRAINT uq_fbref_fixtures_time_home_away UNIQUE (kickoff_time, home_code, away_code);

ALTER TABLE fbref.gca ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE fbref.gca ALTER COLUMN updated_at SET NOT NULL;

DROP INDEX fbref.idx_gca_match_team;

CREATE INDEX idx_gca_match_team ON fbref.gca (match_code, team_code);

ALTER TABLE fbref.gca ADD CONSTRAINT uq_gca_match_team UNIQUE (match_code, team_code);

ALTER TABLE fbref.goal_keeping ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE fbref.goal_keeping ALTER COLUMN updated_at SET NOT NULL;

DROP INDEX fbref.idx_goal_keeping_match_team;

CREATE INDEX idx_goal_keeping_match_team ON fbref.goal_keeping (match_code, team_code);

ALTER TABLE fbref.goal_keeping ADD CONSTRAINT uq_goal_keeping_match_team UNIQUE (match_code, team_code);

ALTER TABLE fbref.market_odds ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE fbref.market_odds ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE fbref.match_results ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE fbref.match_results ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE fbref.match_stats_sync_state ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE fbref.match_stats_sync_state ALTER COLUMN updated_at SET NOT NULL;

DROP INDEX fbref.idx_match_stats_sync_state_team_code_season;

CREATE INDEX idx_match_stats_sync_state_team_code_season ON fbref.match_stats_sync_state (team_code, season);

ALTER TABLE fbref.match_stats_sync_state ADD CONSTRAINT uq_match_stats_sync_state_team_code_season UNIQUE (team_code, season);

ALTER TABLE fbref.passing ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE fbref.passing ALTER COLUMN updated_at SET NOT NULL;

DROP INDEX fbref.idx_passing_match_team;

CREATE INDEX idx_passing_match_team ON fbref.passing (match_code, team_code);

ALTER TABLE fbref.passing ADD CONSTRAINT uq_passing_match_team UNIQUE (match_code, team_code);

ALTER TABLE fbref.player_match_stats ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE fbref.player_match_stats ALTER COLUMN updated_at SET NOT NULL;

DROP INDEX fbref.idx_player_match_stats_match_player;

CREATE INDEX idx_player_match_stats_match_player ON fbref.player_match_stats (match_code, player_code);

ALTER TABLE fbref.player_match_stats ADD CONSTRAINT uq_player_match_stats_match_player UNIQUE (match_code, player_code);

ALTER TABLE fbref.player_stats_sync_state ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE fbref.player_stats_sync_state ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE fbref.shooting ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE fbref.shooting ALTER COLUMN updated_at SET NOT NULL;

DROP INDEX fbref.idx_shooting_match_team;

CREATE INDEX idx_shooting_match_team ON fbref.shooting (match_code, team_code);

ALTER TABLE fbref.shooting ADD CONSTRAINT uq_shooting_match_team UNIQUE (match_code, team_code);

UPDATE public.alembic_version_fbref SET version_num='df4922965ede' WHERE public.alembic_version_fbref.version_num = 'e8747c4304df';

-- Running upgrade df4922965ede -> 4469b6be3375

UPDATE public.alembic_version_fbref SET version_num='4469b6be3375' WHERE public.alembic_version_fbref.version_num = 'df4922965ede';

COMMIT;

