from typing import Optional, Dict, Any
from core.registry import Registry
from core.scheduler.tasks.sync.fbref import (
    SyncCompTeam,
    SyncDefensiveAction,
    SyncScoresAndFixtures,
    SyncGoalAndShotCreation,
    SyncGoalKeeping,
    SyncPassing,
    SyncShooting,
    SyncPlayerMatchStats,
    SyncMarketOdds,
    SyncEloRating
)
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask, Pipeline

@Registry.factory('sync.fbref.comp_teams')
def create_sync_fbref_comp_teams_task(
    site: Site,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(SyncCompTeam(site, payload))

@Registry.factory('sync.fbref.scores_and_fixtures')
def create_sync_fbref_scores_and_fixtures_task(
    site: Site,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(SyncScoresAndFixtures(site, payload))

@Registry.factory('sync.fbref.gca')
def create_sync_fbref_gca_task(
    site: Site,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(SyncGoalAndShotCreation(site, payload))

@Registry.factory('sync.fbref.passing')
def create_sync_fbref_passing_task(
    site: Site,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(SyncPassing(site, payload))

@Registry.factory('sync.fbref.defensive_actions')
def create_sync_fbref_defensive_actions_task(
    site: Site,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(SyncDefensiveAction(site, payload))

@Registry.factory('sync.fbref.shooting')
def create_sync_fbref_shooting_task(
    site: Site,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(SyncShooting(site, payload))

@Registry.factory('sync.fbref.goalkeeping')
def create_sync_fbref_goalkeeping_task(
    site: Site,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(SyncGoalKeeping(site, payload))

@Registry.factory('sync.fbref.player_match_stats')
def create_sync_fbref_player_match_stats_task(
    site: Site,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(SyncPlayerMatchStats(site, payload))

@Registry.factory('sync.fbref.market_odds')
def create_sync_fbref_market_odds_task(
    site: Site,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(SyncMarketOdds(site, payload))

@Registry.factory('sync.fbref.elo_rating')
def create_sync_fbref_elo_rating_task(
    site: Site,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(SyncEloRating(site, payload))

@Registry.factory('sync.fbref.batch')
def create_sync_fbref_batch_task(
    site: Site,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(
        SyncCompTeam(site, payload),
        SyncScoresAndFixtures(site, payload),
        SyncEloRating(site, payload),
        SyncGoalAndShotCreation(site, payload),
        SyncPassing(site, payload),
        SyncDefensiveAction(site, payload),
        SyncShooting(site, payload),
        SyncGoalKeeping(site, payload),
        SyncPlayerMatchStats(site, payload),
        SyncMarketOdds(site, payload)
    )
