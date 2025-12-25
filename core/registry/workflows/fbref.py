from typing import Optional, Dict, Any
from core.registry.registry import Registry
from core.scheduler.tasks.sync.fbref import (
    SyncClub,
    SyncCompetition,
    SyncCountry,
    SyncDefensiveAction,
    SyncMatchResult,
    SyncGoalAndShotCreation,
    SyncGoalKeeping,
    SyncPassing,
    SyncShooting,
    SyncPlayerMatchStats,
    IngestMarketOdds
)
from core.store.postgres.models import (
    Site, Country, Club, Competition, MatchResult,
    MatchStatsSyncState, CountrySyncState, GoalAndShotCreation,
    Passing, DefensiveAction, Shooting, GoalKeeping,
    GlobalState, PlayerMatchStats, PlayerStatsSyncState, MarketOdds
)
from core.scheduler.tasks.base_task import BaseTask, Pipeline
from core.store.postgres.postgresql_manager import PostgreSQLManager

@Registry.register('sync.fbref.countries')
def create_sync_fbref_countries_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [GlobalState, Country],
        site.get_namespace()
    )
    return Pipeline(
        SyncCountry(site)
    )

@Registry.register('sync.fbref.competitions')
def create_sync_fbref_competitions_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [GlobalState, Competition],
        site.get_namespace()
    )
    return Pipeline(
        SyncCompetition(site)
    )

@Registry.register('sync.fbref.clubs')
def create_sync_fbref_clubs_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [GlobalState, Country, Club, CountrySyncState],
        site.get_namespace()
    )
    return Pipeline(
        SyncCountry(site),
        SyncClub(site)
    )

@Registry.register('sync.fbref.match_results')
def create_sync_fbref_match_results_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [GlobalState, Country, Club, CountrySyncState, MatchResult, MatchStatsSyncState],
        site.get_namespace()
    )
    return Pipeline(
        SyncCountry(site),
        SyncClub(site),
        SyncMatchResult(site, payload)
    )

@Registry.register('sync.fbref.gca')
def create_sync_fbref_gca_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [GlobalState, Country, Club, CountrySyncState, GoalAndShotCreation, MatchStatsSyncState],
        site.get_namespace()
    )
    return Pipeline(
        SyncCountry(site),
        SyncClub(site),
        SyncGoalAndShotCreation(site, payload)
    )

@Registry.register('sync.fbref.passing')
def create_sync_fbref_passing_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [GlobalState, Country, Club, CountrySyncState, Passing, MatchStatsSyncState],
        site.get_namespace()
    )
    return Pipeline(
        SyncCountry(site),
        SyncClub(site),
        SyncPassing(site, payload)
    )

@Registry.register('sync.fbref.defensive_actions')
def create_sync_fbref_defensive_actions_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [GlobalState, Country, Club, CountrySyncState, DefensiveAction, MatchStatsSyncState],
        site.get_namespace()
    )
    return Pipeline(
        SyncCountry(site),
        SyncClub(site),
        SyncDefensiveAction(site, payload)
    )

@Registry.register('sync.fbref.shooting')
def create_sync_fbref_shooting_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [GlobalState, Country, Club, CountrySyncState, Shooting, MatchStatsSyncState],
        site.get_namespace()
    )
    return Pipeline(
        SyncCountry(site),
        SyncClub(site),
        SyncShooting(site, payload)
    )

@Registry.register('sync.fbref.goalkeeping')
def create_sync_fbref_goalkeeping_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [GlobalState, Country, Club, CountrySyncState, GoalKeeping, MatchStatsSyncState],
        site.get_namespace()
    )
    return Pipeline(
        SyncCountry(site),
        SyncClub(site),
        SyncGoalKeeping(site, payload)
    )


@Registry.register('sync.fbref.player_match_stats')
def create_sync_fbref_player_match_stats_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [Club, PlayerMatchStats, PlayerStatsSyncState],
        site.get_namespace()
    )
    return Pipeline(
        SyncPlayerMatchStats(site, payload)
    )

@Registry.register('sync.fbref.batch')
def create_sync_fbref_batch_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [GlobalState, Country, Club, CountrySyncState, Competition, MatchStatsSyncState,
         MatchResult, GoalAndShotCreation, Passing,
         DefensiveAction, Shooting, GoalKeeping],
        site.get_namespace()
    )
    return Pipeline(
        SyncCompetition(site),
        SyncCountry(site),
        SyncClub(site),
        SyncMatchResult(site, payload),
        SyncGoalAndShotCreation(site, payload),
        SyncPassing(site, payload),
        SyncDefensiveAction(site, payload),
        SyncShooting(site, payload),
        SyncGoalKeeping(site, payload),
        SyncPlayerMatchStats(site, payload)
    )

@Registry.register('sync.fbref.market_odds')
def create_sync_fbref_market_odds_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [MarketOdds],
        site.get_namespace()
    )
    return Pipeline(
        IngestMarketOdds(site, payload)
    )