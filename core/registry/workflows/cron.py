from core.domain import LeagueID
from core.config.env_manager import env_manager
from core.registry import Registry, RegistryKind
from core.store.cache.global_store import GlobalStore

def init_cron_jobs() -> None:
    from core.scheduler.cron import Cron
    cron = Cron.get_instance()

    current_env = env_manager.value
    jobs = Registry.filter(RegistryKind.CRON)

    for name, target, metadata in jobs:
        allowed_envs = metadata.get("envs")

        if allowed_envs is not None:
            if not isinstance(allowed_envs, list):
                raise TypeError(f"Task config error: 'envs' must be a list (e.g. ['prod']), got {type(allowed_envs)}: {allowed_envs}")

            if current_env not in [env.lower() for env in allowed_envs]:
                continue

        trigger = metadata.get("trigger")
        cron.add_job(target, name, **trigger)

@Registry.cron('cron.sync_fotmob_fixtures', minute="*/5", envs=['dev', 'prod'])
def sync_fotmob_fixtures() -> None:
    from core.server.services.site_service import SiteService

    league_id = LeagueID.EPL.value
    SiteService.get_instance().start_sync(
        'fotmob',
        'fixtures',
        {
            'league_id': str(league_id)
        }
    )

@Registry.cron('cron.sync_fotmob_lineups', minute="*/10", envs=['dev', 'prod'])
def sync_fotmob_lineups() -> None:
    from core.server.services.site_service import SiteService

    SiteService.get_instance().start_sync(
        'fotmob',
        'lineups',
        {}
    )

@Registry.cron('cron.sync_pinnacle_odds', minute="*/15", envs=['dev', 'prod'])
def sync_pinnacle_odds() -> None:
    from core.server.services.site_service import SiteService
    SiteService.get_instance().start_sync(
        'pinnacle',
        'odds',
        {
            'country_name': 'england',
            'league_name': 'premier-league'
        }
    )

@Registry.cron('cron.sync_fbref_batch', hour=10, minute=0, envs=['dev', 'prod'])
def sync_fbref_batch() -> None:
    from core.server.services.site_service import SiteService

    league_id = LeagueID.EPL.value
    latest_season = GlobalStore.get_instance().get(f'seasons.{league_id}')
    if latest_season is None:
        raise ValueError(f"Latest season for league {league_id} not found")

    SiteService.get_instance().start_sync(
        'fbref',
        'batch',
        payload={
            'league_id': str(league_id),
            'min_season': latest_season,
            'max_season': latest_season
        },
        is_force=True
    )