SEASON_COL           = "season"
KICKOFF_TIME_COL     = "kickoff_time"
FIXTURE_CODE_COL     = "match_code"
REST_DAYS_COL        = "rest_days"
IS_HOME_COL          = "is_home"
ORIGINAL_INDEX_COL   = "original_index"

TEAM_CODE_COL        = "team_code"
HOME_TEAM_COL        = "home_team"
HOME_CODE_COL        = "home_code"
AWAY_CODE_COL        = "away_code"
POINT_COL            = "point"
HOME_POINT_COL       = "home_point"
AWAY_POINT_COL       = "away_point"
HOME_GF_COL          = "home_gf"
AWAY_GF_COL          = "away_gf"
HOME_POSSESSION_COL  = "home_possession"
AWAY_POSSESSION_COL  = "away_possession"
PAGE_URL_COL         = "page_url"
MATCH_REPORT_COL     = "match_report"
XG_COL               = "xg"
NOTES_COL            = "notes"

PLAYER_CODE_COL      = "player_code"
IS_STARTER_COL       = "is_starter"
POSITION_COL         = "position"
PRIMARY_POSITION_COL = "primary_position"
MINUTES_PLAYED_COL   = "minutes"
NON_PENALTY_GOALS_COL = "non_penalty_goals"
GOALS_COL            = "goals"
PENALTIES_MADE_COL   = "penalties_made"


HOME_VENUE = "home"
AWAY_VENUE = "away"

EPSILON = 1e-6
IMPUTATION_QUANTILE = 0.05

DEFAULT_DECIMALS = 4

SITE_HOST = "https://fbref.com"
PAGE_URL_TEMPLATE = SITE_HOST + "/en/squads/{club_code}/{season}/matchlogs/all_comps/schedule/{club_name}-Scores-and-Fixtures-All-Competitions"

FINISH_REG_POSITIONS      = ['FW', 'LW', 'RW', 'AM', 'LM', 'RM', 'WB']
CREATIVITY_REG_POSITIONS  = ['AM', 'CM', 'LM', 'RM', 'DM', 'LW', 'RW', 'WB']
PROGRESSION_REG_POSITIONS = ['LW', 'RW', 'WB', 'LM', 'RM', 'AM', 'LB', 'RB']
DEFENSE_REG_POSITIONS     = ['CB', 'LB', 'RB', 'WB', 'DM']
AERIAL_MAX_POSITIONS      = ['CB', 'DM', 'FW', 'WB']
AERIAL_AVG_POSITIONS      = ['CB', 'DM', 'WB']

OUTFIELD_POSITIONS  = ['CB', 'DF', 'LB', 'RB', 'DM', 'WB', 'CM', 'AM', 'LM', 'RM', 'LW', 'RW', 'FW']
ATTACK_POSITIONS    = ["FW", "LW", "RW"]
PLAYMAKER_POSITIONS = ["AM", "CM", "LM", "RM", "DM", "WB"]
DEFENSE_POSITIONS   = ["DF", "CB", "LB", "RB", "DM", "WB"]
AERIAL_POSITIONS    = ["DF", "CB", "LB", "RB", "DM", "WB", "FW"]
GK_POSITIONS        = ["GK"]

OUTFIELD_FEATURE_POSITION_MAPPING = {
    "npxg_per_90_ema_20": ATTACK_POSITIONS,
    "shots_on_target_per_90_ema_20": ATTACK_POSITIONS,
    "non_penalty_goals_per_90_ema_20": ATTACK_POSITIONS,
    "shots_per_90_ema_20-shots_on_target_per_90_ema_20": ATTACK_POSITIONS,
    "xg_assist_per_90_ema_20": PLAYMAKER_POSITIONS,
    "shot_creating_actions_per_90_ema_20": PLAYMAKER_POSITIONS,
    "progressive_passes_per_90_ema_20": PLAYMAKER_POSITIONS,
    "key_passes_per_90_ema_20": PLAYMAKER_POSITIONS,
    "progressive_carries_per_90_ema_20": PLAYMAKER_POSITIONS,
    "take_ons_won_per_90_ema_20": PLAYMAKER_POSITIONS,
    "fouls_drawn_per_90_ema_20": PLAYMAKER_POSITIONS,
    "dispossessed_per_90_ema_20+miscontrols_per_90_ema_20": PLAYMAKER_POSITIONS,
    "tackles_won_per_90_adj_ema_20": DEFENSE_POSITIONS,
    "interceptions_per_90_adj_ema_20": DEFENSE_POSITIONS,
    "ball_recoveries_per_90_adj_ema_20": DEFENSE_POSITIONS,
    "blocks_per_90_adj_ema_20": DEFENSE_POSITIONS,
    "challenges_lost_per_90_adj_ema_20": DEFENSE_POSITIONS,
    "aerials_won_per_90_ema_20": AERIAL_POSITIONS,
    "aerials_lost_per_90_ema_20/(aerials_won_per_90_ema_20+aerials_lost_per_90_ema_20)": AERIAL_POSITIONS
}

OUTFIELD_EMPIRICAL_BENCHMARKS = {
    "npxg_per_90_ema_20": 0.8,
    "shots_on_target_per_90_ema_20": 1.5,
    "non_penalty_goals_per_90_ema_20": 0.8,
    "shots_per_90_ema_20-shots_on_target_per_90_ema_20": 2.5,
    "xg_assist_per_90_ema_20": 0.5,
    "shot_creating_actions_per_90_ema_20": 6.0,
    "progressive_passes_per_90_ema_20": 10.0,
    "key_passes_per_90_ema_20": 3.0,
    "progressive_carries_per_90_ema_20": 10.0,
    "take_ons_won_per_90_ema_20": 4.0,
    "fouls_drawn_per_90_ema_20": 3.0,
    "dispossessed_per_90_ema_20+miscontrols_per_90_ema_20": 6.0,
    "tackles_won_per_90_adj_ema_20": 3.0,
    "interceptions_per_90_adj_ema_20": 2.5,
    "ball_recoveries_per_90_adj_ema_20": 12.0,
    "blocks_per_90_adj_ema_20": 2.5,
    "challenges_lost_per_90_adj_ema_20": 2.0,
    "aerials_won_per_90_ema_20": 6.0,
    "aerials_lost_per_90_ema_20/(aerials_won_per_90_ema_20+aerials_lost_per_90_ema_20)": 1.0
}

GK_FEATURE_POSITION_MAPPING = {
    "gk_psxg_per_90_ema_20-gk_goals_against_per_90_ema_20": GK_POSITIONS,
    "gk_crosses_stopped_per_90_ema_20/gk_crosses_per_90_ema_20": GK_POSITIONS,
    "gk_def_actions_outside_pen_area_per_90_ema_20": GK_POSITIONS
}

GK_EMPIRICAL_BENCHMARKS = {
    "gk_psxg_per_90_ema_20-gk_goals_against_per_90_ema_20": 1.0,
    "gk_crosses_stopped_per_90_ema_20/gk_crosses_per_90_ema_20": 0.15,
    "gk_def_actions_outside_pen_area_per_90_ema_20": 2.0
}
