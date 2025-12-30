from core.registry import Registry, RegistryKind

def init_cron_jobs() -> None:
    from core.scheduler.cron import Cron
    cron = Cron.get_instance()

    for func, metadata in Registry.filter(RegistryKind.CRON):
        cron.add_job(func, **metadata["trigger"])

@Registry.cron('cron.sync_fotmob_fixtures', minute="*/1")
def sync_fotmob_fixtures() -> None:
    from core.server.services.site_service import SiteService
    SiteService.get_instance().start_sync(
        'fotmob',
        'fixtures',
        {'league_id': '47', 'league_name': 'premier-league'}
    )

@Registry.cron('cron.sync_pinnacle_odds', minute="*/15")
def sync_pinnacle_odds() -> None:
    from core.server.services.site_service import SiteService
    SiteService.get_instance().start_sync(
        'pinnacle',
        'odds',
        {'country_name': 'england', 'league_name': 'premier-league'}
    )
