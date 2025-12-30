from typing import Optional, Dict, Any
from core.registry import Registry
from core.scheduler.tasks.sync.fbref import (
    SyncCompTeam,
    SyncDefensiveAction,
    SyncMatchResult,
    SyncGoalAndShotCreation,
    SyncGoalKeeping,
    SyncPassing,
    SyncShooting,
    SyncPlayerMatchStats,
    SyncMarketOdds
)
from core.store.postgres.models import (
    Site, MatchResult,
    MatchStatsSyncState, GoalAndShotCreation,
    Passing, DefensiveAction, Shooting, GoalKeeping,
    GlobalState, PlayerMatchStats, PlayerStatsSyncState, MarketOdds,
    CompTeam, CompSyncState
)
from core.scheduler.tasks.base_task import BaseTask, Pipeline
from core.store.postgres.postgresql_manager import PostgreSQLManager

@Registry.factory('sync.fbref.comp_teams')
def create_sync_fbref_comp_teams_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [GlobalState, CompTeam, CompSyncState],
        site.get_namespace()
    )
    return Pipeline(
        SyncCompTeam(site, payload)
    )

@Registry.factory('sync.fbref.match_results')
def create_sync_fbref_match_results_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [GlobalState, CompTeam, CompSyncState, MatchResult, MatchStatsSyncState],
        site.get_namespace()
    )
    return Pipeline(
        SyncMatchResult(site, payload)
    )

@Registry.factory('sync.fbref.gca')
def create_sync_fbref_gca_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [GlobalState, CompTeam, CompSyncState, GoalAndShotCreation, MatchStatsSyncState],
        site.get_namespace()
    )
    return Pipeline(
        SyncGoalAndShotCreation(site, payload)
    )

@Registry.factory('sync.fbref.passing')
def create_sync_fbref_passing_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [GlobalState, CompTeam, CompSyncState, Passing, MatchStatsSyncState],
        site.get_namespace()
    )
    return Pipeline(
        SyncPassing(site, payload)
    )

@Registry.factory('sync.fbref.defensive_actions')
def create_sync_fbref_defensive_actions_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [GlobalState, CompTeam, CompSyncState, DefensiveAction, MatchStatsSyncState],
        site.get_namespace()
    )
    return Pipeline(
        SyncDefensiveAction(site, payload)
    )

@Registry.factory('sync.fbref.shooting')
def create_sync_fbref_shooting_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [GlobalState, CompTeam, CompSyncState, Shooting, MatchStatsSyncState],
        site.get_namespace()
    )
    return Pipeline(
        SyncShooting(site, payload)
    )

@Registry.factory('sync.fbref.goalkeeping')
def create_sync_fbref_goalkeeping_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [GlobalState, CompTeam, CompSyncState, GoalKeeping, MatchStatsSyncState],
        site.get_namespace()
    )
    return Pipeline(
        SyncGoalKeeping(site, payload)
    )

@Registry.factory('sync.fbref.player_match_stats')
def create_sync_fbref_player_match_stats_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [MatchResult, PlayerMatchStats, PlayerStatsSyncState],
        site.get_namespace()
    )
    return Pipeline(
        SyncPlayerMatchStats(site, payload)
    )

@Registry.factory('sync.fbref.market_odds')
def create_sync_fbref_market_odds_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [CompSyncState, MarketOdds],
        site.get_namespace()
    )
    return Pipeline(
        SyncMarketOdds(site, payload)
    )

@Registry.factory('sync.fbref.batch')
def create_sync_fbref_batch_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [GlobalState, CompTeam, CompSyncState, MatchStatsSyncState,
         MatchResult, GoalAndShotCreation, Passing,
         DefensiveAction, Shooting, GoalKeeping, PlayerMatchStats, PlayerStatsSyncState],
        site.get_namespace()
    )
    return Pipeline(
        SyncCompTeam(site, payload),
        SyncMatchResult(site, payload),
        SyncGoalAndShotCreation(site, payload),
        SyncPassing(site, payload),
        SyncDefensiveAction(site, payload),
        SyncShooting(site, payload),
        SyncGoalKeeping(site, payload),
        SyncPlayerMatchStats(site, payload),
        SyncMarketOdds(site, payload)
    )
