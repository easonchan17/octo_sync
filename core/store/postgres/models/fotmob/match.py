from sqlalchemy import Column, Integer, SmallInteger, DateTime, Index, text, Float, String, Boolean, UniqueConstraint, BigInteger
from ..base_model import Base, CrawlStatusMixin, RawJsonMixin
from core.types.enums import SiteName


class MatchRaw(Base, CrawlStatusMixin, RawJsonMixin):
    __tablename__ = 'match_raw'
    __table_args__ = (
        Index('idx_match_raw_created_at', 'created_at'),
        Index('idx_match_raw_updated_at', 'updated_at'),
        Index('idx_match_raw_next_fetch_at', 'next_fetch_at'),
        Index('idx_match_raw_kickoff_time', 'kickoff_time'),
        Index(
            'idx_match_raw_not_parsed',
            'kickoff_time',
            postgresql_where=text("is_fetched = true and is_parsed = false")
        ),
        Index(
            'idx_match_raw_not_fetched',
            'match_id',
            postgresql_where=text("is_fetched = false")
        ),
        {'schema': SiteName.FOTMOB.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    match_id = Column(Integer, nullable=False, unique=True)
    kickoff_time = Column(DateTime(timezone=True), nullable=False)

    match_status = Column(Integer, nullable=True)


class MatchStat(Base):
    __tablename__ = 'match_stats'
    __table_args__ = (
        Index('idx_match_stats_created_at', 'created_at'),
        Index('idx_match_stats_updated_at', 'updated_at'),
        Index('idx_match_stats_match_id', 'match_id'),
        {'schema': SiteName.FOTMOB.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, nullable=False, unique=True)

    lineup_type = Column(String(16), nullable=True)
    home_formation = Column(String(16), nullable=True)
    away_formation = Column(String(16), nullable=True)

    home_possession = Column(Integer, nullable=True)
    away_possession = Column(Integer, nullable=True)

    home_goals_penalty = Column(Integer, nullable=True)
    away_goals_penalty = Column(Integer, nullable=True)

    home_shots = Column(Integer, nullable=True)
    away_shots = Column(Integer, nullable=True)
    home_shots_on_target = Column(Integer, nullable=True)
    away_shots_on_target = Column(Integer, nullable=True)
    home_shots_off_target = Column(Integer, nullable=True)
    away_shots_off_target = Column(Integer, nullable=True)
    home_hit_woodwork = Column(Integer, nullable=True)
    away_hit_woodwork = Column(Integer, nullable=True)
    home_shots_inside_box = Column(Integer, nullable=True)
    away_shots_inside_box = Column(Integer, nullable=True)
    home_shots_outside_box = Column(Integer, nullable=True)
    away_shots_outside_box = Column(Integer, nullable=True)
    home_big_chances = Column(Integer, nullable=True)
    away_big_chances = Column(Integer, nullable=True)
    home_big_chances_missed = Column(Integer, nullable=True)
    away_big_chances_missed = Column(Integer, nullable=True)

    home_xg = Column(Float, nullable=True)
    away_xg = Column(Float, nullable=True)
    home_xg_open_play = Column(Float, nullable=True)
    away_xg_open_play = Column(Float, nullable=True)
    home_xg_set_play = Column(Float, nullable=True)
    away_xg_set_play = Column(Float, nullable=True)
    home_npxg = Column(Float, nullable=True)
    away_npxg = Column(Float, nullable=True)
    home_xg_on_target = Column(Float, nullable=True)
    away_xg_on_target = Column(Float, nullable=True)

    home_passes = Column(Integer, nullable=True)
    away_passes = Column(Integer, nullable=True)
    home_passes_completed = Column(Integer, nullable=True)
    away_passes_completed = Column(Integer, nullable=True)
    home_own_half_passes = Column(Integer, nullable=True)
    away_own_half_passes = Column(Integer, nullable=True)
    home_opp_half_passes = Column(Integer, nullable=True)
    away_opp_half_passes = Column(Integer, nullable=True)
    home_long_passes = Column(Integer, nullable=True)
    away_long_passes = Column(Integer, nullable=True)
    home_long_passes_completed = Column(Integer, nullable=True)
    away_long_passes_completed = Column(Integer, nullable=True)
    home_crosses = Column(Integer, nullable=True)
    away_crosses = Column(Integer, nullable=True)
    home_crosses_completed = Column(Integer, nullable=True)
    away_crosses_completed = Column(Integer, nullable=True)
    home_throws = Column(Integer, nullable=True)
    away_throws = Column(Integer, nullable=True)
    home_corners = Column(Integer, nullable=True)
    away_corners = Column(Integer, nullable=True)

    home_tackles = Column(Integer, nullable=True)
    away_tackles = Column(Integer, nullable=True)
    home_interceptions = Column(Integer, nullable=True)
    away_interceptions = Column(Integer, nullable=True)
    home_shot_blocks = Column(Integer, nullable=True)
    away_shot_blocks = Column(Integer, nullable=True)
    home_clearances = Column(Integer, nullable=True)
    away_clearances = Column(Integer, nullable=True)
    home_keeper_saves = Column(Integer, nullable=True)
    away_keeper_saves = Column(Integer, nullable=True)

    home_duels_won = Column(Integer, nullable=True)
    away_duels_won = Column(Integer, nullable=True)
    home_ground_duels = Column(Integer, nullable=True)
    away_ground_duels = Column(Integer, nullable=True)
    home_ground_duels_won = Column(Integer, nullable=True)
    away_ground_duels_won = Column(Integer, nullable=True)
    home_aerials = Column(Integer, nullable=True)
    away_aerials = Column(Integer, nullable=True)
    home_aerials_won = Column(Integer, nullable=True)
    away_aerials_won = Column(Integer, nullable=True)
    home_dribbles = Column(Integer, nullable=True)
    away_dribbles = Column(Integer, nullable=True)
    home_dribbles_completed = Column(Integer, nullable=True)
    away_dribbles_completed = Column(Integer, nullable=True)

    home_offsides = Column(Integer, nullable=True)
    away_offsides = Column(Integer, nullable=True)
    home_fouls_committed = Column(Integer, nullable=True)
    away_fouls_committed = Column(Integer, nullable=True)
    home_yellow_cards = Column(Integer, nullable=True)
    away_yellow_cards = Column(Integer, nullable=True)
    home_red_cards = Column(Integer, nullable=True)
    away_red_cards = Column(Integer, nullable=True)


class MatchPlayerStat(Base):
    __tablename__ = 'match_player_stats'
    __table_args__ = (
        Index('idx_match_player_stats_created_at', 'created_at'),
        Index('idx_match_player_stats_updated_at', 'updated_at'),
        Index('idx_match_player_stats_match_id_opta_id_player_id_player_name', 'match_id', 'opta_id', 'player_id', 'player_name'),
        UniqueConstraint('match_id', 'opta_id', 'player_id', 'player_name', name='uq_match_player_stats_match_id_opta_id_player_id_player_name'),
        {'schema': SiteName.FOTMOB.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, nullable=False)
    opta_id = Column(String(64), nullable=False)
    player_id = Column(Integer, nullable=False)
    player_name = Column(String(128), nullable=False)

    rating = Column(Float, nullable=True)
    fantasy_points = Column(Integer, nullable=True)
    minutes_played = Column(Integer, nullable=True)

    shots = Column(Integer, nullable=True)
    shots_on_target = Column(Integer, nullable=True)
    shots_blocked = Column(Integer, nullable=True)
    shots_inside_box = Column(Integer, nullable=True)
    shots_freekick = Column(Integer, nullable=True)
    shots_fastbreak = Column(Integer, nullable=True)
    shots_setpiece = Column(Integer, nullable=True)
    shots_corner = Column(Integer, nullable=True)
    shots_header = Column(Integer, nullable=True)
    shots_penalty = Column(Integer, nullable=True)
    shots_individual_play = Column(Integer, nullable=True)
    shots_throw_in_set_piece = Column(Integer, nullable=True)

    goals = Column(Integer, nullable=True)
    goals_inside_box = Column(Integer, nullable=True)
    goals_freekick = Column(Integer, nullable=True)
    goals_fastbreak = Column(Integer, nullable=True)
    goals_setpiece = Column(Integer, nullable=True)
    goals_corner = Column(Integer, nullable=True)
    goals_header = Column(Integer, nullable=True)
    goals_penalty = Column(Integer, nullable=True)
    goals_individual_play = Column(Integer, nullable=True)
    goals_throw_in_set_piece = Column(Integer, nullable=True)

    xg_inside_box = Column(Float, nullable=True)
    xg_freekick = Column(Float, nullable=True)
    xg_fastbreak = Column(Float, nullable=True)
    xg_setpiece = Column(Float, nullable=True)
    xg_corner = Column(Float, nullable=True)
    xg_header = Column(Float, nullable=True)
    xg_individual_play = Column(Float, nullable=True)
    xg_throw_in_set_piece = Column(Float, nullable=True)

    xgot_inside_box = Column(Float, nullable=True)
    xgot_freekick = Column(Float, nullable=True)
    xgot_fastbreak = Column(Float, nullable=True)
    xgot_setpiece = Column(Float, nullable=True)
    xgot_corner = Column(Float, nullable=True)
    xgot_header = Column(Float, nullable=True)
    xgot_individual_play = Column(Float, nullable=True)
    xgot_throw_in_set_piece = Column(Float, nullable=True)

    touches = Column(Integer, nullable=True)
    touches_opp_box = Column(Integer, nullable=True)
    passes_into_final_third = Column(Integer, nullable=True)
    passes = Column(Integer, nullable=True)
    passes_completed = Column(Integer, nullable=True)
    long_passes = Column(Integer, nullable=True)
    long_passes_completed = Column(Integer, nullable=True)
    dispossessed = Column(Integer, nullable=True)
    chances_created = Column(Integer, nullable=True)
    assists = Column(Integer, nullable=True)
    xg = Column(Float, nullable=True)
    npxg = Column(Float, nullable=True)
    xgot = Column(Float, nullable=True)
    xa = Column(Float, nullable=True)

    tackles = Column(Integer, nullable=True)
    blocks = Column(Integer, nullable=True)
    clearances = Column(Integer, nullable=True)
    headed_clearance = Column(Integer, nullable=True)
    interceptions = Column(Integer, nullable=True)
    recoveries = Column(Integer, nullable=True)
    dribbled_past = Column(Integer, nullable=True)

    duels_won = Column(Integer, nullable=True)
    duels_lost = Column(Integer, nullable=True)
    ground_duels = Column(Integer, nullable=True)
    ground_duels_won = Column(Integer, nullable=True)
    aerials = Column(Integer, nullable=True)
    aerials_won = Column(Integer, nullable=True)
    fouls_suffered = Column(Integer, nullable=True)
    fouls_committed = Column(Integer, nullable=True)

    saves = Column(Integer, nullable=True)
    goals_conceded = Column(Integer, nullable=True)
    xgot_faced = Column(Float, nullable=True)
    goals_prevented = Column(Float, nullable=True)
    keeper_sweeper = Column(Integer, nullable=True)
    keeper_high_claim = Column(Integer, nullable=True)
    keeper_diving_save = Column(Integer, nullable=True)
    saves_inside_box = Column(Integer, nullable=True)
    punches = Column(Integer, nullable=True)
    throws = Column(Integer, nullable=True)

    team_id = Column(Integer, nullable=True)
    position_id = Column(Integer, nullable=True)
    usual_position = Column(Integer, nullable=True)
    is_goalkeeper = Column(Boolean, nullable=True)

class ShotStat(Base):
    __tablename__ = 'match_shot_stats'
    __table_args__ = (
        Index('idx_match_shot_stats_created_at', 'created_at'),
        Index('idx_match_shot_stats_updated_at', 'updated_at'),
        Index('idx_match_shot_stats_match_team_player', 'match_id', 'team_id', 'player_id'),
        UniqueConstraint('match_id', 'event_id', name='uq_match_shot_stats_match_id_event_id'),
        {'schema': SiteName.FOTMOB.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, nullable=False)
    event_id = Column(BigInteger, nullable=False)

    period = Column(String(16), nullable=True)
    min = Column(Integer, nullable=True)
    min_added = Column(Integer, nullable=True)
    x = Column(Float, nullable=True)
    y = Column(Float, nullable=True)

    team_id = Column(Integer, nullable=True)
    keeper_id = Column(Integer, nullable=True)
    player_id = Column(Integer, nullable=True)

    shot_type = Column(String(32), nullable=True)
    event_type = Column(String(32), nullable=True)
    situation = Column(String(32), nullable=True)

    is_blocked = Column(Boolean, nullable=True)
    is_own_goal = Column(Boolean, nullable=True)
    is_on_target = Column(Boolean, nullable=True)
    is_saved_off_line = Column(Boolean, nullable=True)
    is_inside_box = Column(Boolean, nullable=True)

    xg = Column(Float, nullable=True)
    xgot = Column(Float, nullable=True)

class MatchLineup(Base):
    __tablename__ = 'match_lineups'
    __table_args__ = (
        Index('idx_match_lineups_created_at', 'created_at'),
        Index('idx_match_lineups_updated_at', 'updated_at'),
        UniqueConstraint('match_id', 'team_id', 'member_id', name='uq_match_lineups_match_team_member_id'),
        {'schema': SiteName.FOTMOB.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, nullable=False)

    team_id = Column(Integer, nullable=False)
    team_name = Column(String(100), nullable=True)

    member_id = Column(Integer, nullable=False)
    member_name = Column(String(128), nullable=False)
    opta_id = Column(String(64), nullable=True)
    age = Column(Integer, nullable=True)

    country_code = Column(String(3), nullable=True)
    country_name = Column(String(100), nullable=True)

    shirt_number = Column(Integer, nullable=True)
    position_id = Column(Integer, nullable=True)
    position = Column(String(3), nullable=True)
    usual_playing_position_id = Column(Integer, nullable=True)

    role = Column(SmallInteger, nullable=True)
    is_captain = Column(Boolean, default=False)

    rating = Column(Float, nullable=True)
    market_value = Column(BigInteger, nullable=True)


class FormCacheBuildLog(Base):
    __tablename__ = 'form_cache_build_logs'
    __table_args__ = (
        Index('idx_form_cache_build_logs_built_at', 'built_at'),
        Index('idx_form_cache_build_logs_created_at', 'created_at'),
        Index('idx_form_cache_build_logs_updated_at', 'updated_at'),
        {'schema': SiteName.FOTMOB.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    built_at = Column(DateTime(timezone=True), nullable=False)
    checkpoint = Column(DateTime(timezone=True), nullable=False)
    match_count = Column(Integer, nullable=False)
