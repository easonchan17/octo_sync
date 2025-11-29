from core.browser.interceptor import TaskType
from core.store.postgres.models import Site, Country
from core.scheduler.tasks.base_task import BaseTask
from core.scheduler.synchronizers.fbref.club_synchronizer import ClubSynchronizer

class SyncClub(BaseTask):
    def __init__(self, site: Site) -> None:
        super().__init__()
        self.site = site
        self.synchronizer = ClubSynchronizer()

    def execute(self, *args, **kwargs) -> None:
        countries = self.synchronizer.get_unsynced_countries(self.site)
        if not countries:
            self.logger.info(f"No countries to sync from {self.site.name}")
            return

        config_prefix = f"interceptor.{self.site.name}.clubs"
        page_url_template = self.config_manager.get_config(f"{config_prefix}.url_template")
        default_timeout = self.config_manager.get_config("browser.timeout")
        html_handler = self.config_manager.get_config(f"{config_prefix}.html_handler")

        for country_name, country_code in countries:
            try:
                page_url = page_url_template.format(country_code=country_code, country_name=country_name)
                future = self.interceptor.submit_task(
                    TaskType.OPEN_PAGE,
                    url=page_url,
                    html_handler=html_handler
                )

                responses, _ = future.result(timeout=default_timeout*2)
                if not responses:
                    self.logger.error(f"No response for {page_url}")
                    return

                clubs = responses[0]
                if not clubs:
                    self.logger.warning(f"No clubs for {page_url}")
                    continue

                for club in clubs:
                    club.country_name = country_name
                    club.country_code = country_code

                self.logger.debug(f"Intercepted {country_name} clubs from {self.site.name}: {clubs}")
                self.synchronizer.sync(
                    self.site,
                    Country(name=country_name, code=country_code),
                    clubs
                )

            except Exception as e:
                self.logger.error(f"Failed to sync {country_name} clubs from {self.site.name}: {e}")
