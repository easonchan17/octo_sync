from typing import Optional, Dict, Any

from numpy import size
from core.scheduler.tasks.sync.zcy import (
    SyncBrand,
    SyncCategory,
    SyncProduct,
    SyncSubCategory
)
from core.scheduler.tasks.sync.fbref import (
    SyncClub,
    SyncCompetition,
    SyncCountry,
    SyncDefensiveAction,
    SyncFixture,
    SyncGoalAndShotCreation,
    SyncGoalKeeping,
    SyncPassing,
    SyncShooting,
    SyncPlayerMatchStats
)
from core.scheduler.tasks.analysis.analyzers import (
    MatchStatsAnalyzer,
    OutfieldPlayerStatsAnalyzer,
    GoalkeeperStatsAnalyzer,
    MatchStatsAggregator
)
from core.scheduler.tasks.analysis.training.bayesian_optimize_trainer import BayesianOptimizeTrainer
from core.scheduler.tasks.base_task import BaseTask, Pipeline
from core.store.postgres.postgresql_manager import PostgreSQLManager
from core.store.postgres.models import (
    Site, Category, SubCategory, Brand, SubCategoryBrand, Product,
    Country, Club, Competition, Fixture, ClubSyncState, GoalAndShotCreation, Passing,
    DefensiveAction, Shooting, GoalKeeping,GlobalState, PlayerMatchStats, MatchSyncState
)

class Registry:
    _registry = {}

    @classmethod
    def register(cls, name):
        def decorator(func):
            cls._registry[name] = func
            return func
        return decorator

    @classmethod
    def get(
        cls,
        name: str,
        site: Site,
        db: PostgreSQLManager,
        payload: Optional[Dict[str, Any]]
    ) -> Any:
        if name not in cls._registry:
            raise ValueError(f"Name {name} not found in registry")
        return cls._registry[name](site, db, payload)


#****************** fbref ****************#
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
        [GlobalState, Country, Club],
        site.get_namespace()
    )
    return Pipeline(
        SyncCountry(site),
        SyncClub(site)
    )

@Registry.register('sync.fbref.fixtures')
def create_sync_fbref_fixtures_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [GlobalState, Country, Club, Fixture, ClubSyncState],
        site.get_namespace()
    )
    return Pipeline(
        SyncCountry(site),
        SyncClub(site),
        SyncFixture(site, payload)
    )

@Registry.register('sync.fbref.gca')
def create_sync_fbref_gca_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [GlobalState, Country, Club, GoalAndShotCreation, ClubSyncState],
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
        [GlobalState, Country, Club, Passing, ClubSyncState],
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
        [GlobalState, Country, Club, DefensiveAction, ClubSyncState],
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
        [GlobalState, Country, Club, Shooting, ClubSyncState],
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
        [GlobalState, Country, Club, GoalKeeping, ClubSyncState],
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
        [Club, PlayerMatchStats, MatchSyncState],
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
        [GlobalState, Country, Club, Competition, ClubSyncState,
         Fixture, GoalAndShotCreation, Passing,
         DefensiveAction, Shooting, GoalKeeping],
        site.get_namespace()
    )
    return Pipeline(
        SyncCountry(site),
        SyncClub(site),
        SyncCompetition(site),
        SyncFixture(site, payload),
        SyncGoalAndShotCreation(site, payload),
        SyncPassing(site, payload),
        SyncDefensiveAction(site, payload),
        SyncShooting(site, payload),
        SyncGoalKeeping(site, payload),
        SyncPlayerMatchStats(site, payload)
    )
#******************** zcy ******************#
@Registry.register('sync.zcy.category')
def create_sync_zcy_category_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [Category],
        site.get_namespace()
    )

    return Pipeline(
        SyncCategory(site)
    )

@Registry.register('sync.zcy.sub_category')
def create_sync_zcy_sub_category_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [Category, SubCategory],
        site.get_namespace()
    )

    return Pipeline(
        SyncSubCategory(site)
    )

@Registry.register('sync.zcy.brand')
def create_sync_zcy_brand_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [Category, SubCategory, Brand, SubCategoryBrand],
        site.get_namespace()
    )

    return Pipeline(
        SyncBrand(site)
    )

@Registry.register('sync.zcy.product')
def create_sync_zcy_product_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [SubCategory, Brand, SubCategoryBrand, Product],
        site.get_namespace()
    )

    return Pipeline(
        SyncProduct(site)
    )

#******************** model training *******************#
@Registry.register('analysis.fbref.match_stats')
def create_analysis_fbref_match_stats_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(
        MatchStatsAggregator(site, payload)
    )

@Registry.register('training.winball')
def create_training_bayesian_optimization_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(
        BayesianOptimizeTrainer(payload)
    )