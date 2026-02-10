from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, Integer, DateTime, Index, text, Float, String, Boolean
from ..base_model import Base, StatusMixin, DictMixin, CrawlStatusMixin, RawJsonMixin, IntrospectionMixin, Status
from core.types.enums import SiteName


class MatchRawData(Base, StatusMixin, DictMixin, CrawlStatusMixin, RawJsonMixin):
    __tablename__ = 'match_raw_data'
    __table_args__ = (
        Index('idx_match_raw_data_created_at', 'created_at'),
        Index('idx_match_raw_data_updated_at', 'updated_at'),
        Index('idx_match_raw_data_kickoff_time', 'kickoff_time'),
        Index(
            'idx_match_raw_data_not_parsed',
            'kickoff_time',
            postgresql_where=text("is_fetched = true and is_parsed = false")
        ),
        Index(
            'idx_match_raw_data_not_fetched',
            'match_id',
            postgresql_where=text("is_fetched = false")
        ),
        Index('idx_match_raw_data_refetch', 'is_parsed', 'confirm_count', 'kickoff_time'),
        {'schema': '{schema}', 'info': {'sites': [SiteName.FOTMOB.value]}}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    match_id = Column(Integer, nullable=False, unique=True)
    kickoff_time = Column(DateTime(timezone=True), nullable=False)

    match_status = Column(Integer, nullable=True)

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class MatchStat(Base, StatusMixin, DictMixin, IntrospectionMixin):
    __tablename__ = 'match_stats'
    __table_args__ = (
        Index('idx_match_stats_created_at', 'created_at'),
        Index('idx_match_stats_updated_at', 'updated_at'),
        Index('idx_match_stats_match_id', 'match_id'),
        {'schema': '{schema}', 'info': {'sites': [SiteName.FOTMOB.value]}}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, nullable=False, unique=True)

    lineup_type = Column(String(16), nullable=True)
    home_formation = Column(String(16), nullable=True)
    away_formation = Column(String(16), nullable=True)

    home_possession = Column(Integer, nullable=True)
    away_possession = Column(Integer, nullable=True)

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

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class MatchPlayerStat(Base, StatusMixin, DictMixin, IntrospectionMixin):
    __tablename__ = 'match_player_stats'
    __table_args__ = (
        Index('idx_match_player_stats_created_at', 'created_at'),
        Index('idx_match_player_stats_updated_at', 'updated_at'),
        Index('idx_match_player_stats_match_id_opta_id_player_id_player_name', 'match_id', 'opta_id', 'player_id', 'player_name', unique=True),
        {'schema': '{schema}', 'info': {'sites': [SiteName.FOTMOB.value]}}
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
    blocked_shots = Column(Integer, nullable=True)
    touches = Column(Integer, nullable=True)
    touches_opp_box = Column(Integer, nullable=True)
    passes_into_final_third = Column(Integer, nullable=True)
    passes = Column(Integer, nullable=True)
    passes_completed = Column(Integer, nullable=True)
    long_passes = Column(Integer, nullable=True)
    long_passes_completed = Column(Integer, nullable=True)
    dispossessed = Column(Integer, nullable=True)
    chances_created = Column(Integer, nullable=True)
    goals = Column(Integer, nullable=True)
    assists = Column(Integer, nullable=True)
    npxg = Column(Float, nullable=True)
    xg = Column(Float, nullable=True)
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

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class MatchLineup(Base, StatusMixin, DictMixin, IntrospectionMixin):
    __tablename__ = 'match_lineups'
    __table_args__ = (
        Index('idx_match_lineups_created_at', 'created_at'),
        Index('idx_match_lineups_updated_at', 'updated_at'),
        Index('idx_match_lineups_match_id_team_id', 'match_id', 'team_id'),
        Index('idx_match_lineups_match_team_opta_member', 'match_id', 'team_id', 'opta_id', 'member_id', 'member_name', unique=True),
        {'schema': '{schema}', 'info': {'sites': [SiteName.FOTMOB.value]}}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, nullable=False)
    team_id = Column(Integer, nullable=False)
    team_name = Column(String(100), nullable=True)

    country_code = Column(String(3), nullable=True)
    country_name = Column(String(100), nullable=True)
    opta_id = Column(String(64), nullable=True)

    member_id = Column(Integer, nullable=False)
    member_name = Column(String(128), nullable=False)

    age = Column(Integer, nullable=True)

    shirt_number = Column(Integer, nullable=True)
    position_id = Column(Integer, nullable=True)
    usual_playing_position_id = Column(Integer, nullable=True)

    is_starter = Column(Boolean, default=False)
    is_sub = Column(Boolean, default=False)
    is_captain = Column(Boolean, default=False)
    is_coach = Column(Boolean, default=False)

    rating = Column(Float, nullable=True)

    horizontal_layout = Column(JSONB(none_as_null=True), nullable=True)
    vertical_layout = Column(JSONB(none_as_null=True), nullable=True)

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
