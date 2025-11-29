from core.browser.interceptor import TaskType
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask
from core.scheduler.synchronizers.fbref.country_synchronizer import CountrySynchronizer

class SyncCountry(BaseTask):
    def __init__(self, site: Site) -> None:
        super().__init__()
        self.site = site
        self.synchronizer = CountrySynchronizer()

    def execute(self, *args, **kwargs) -> None:
        if self.synchronizer.is_synced(self.site):
            self.logger.warning(f"Countries already synced from {self.site.name}")
            return

        try:
            config_prefix = f"interceptor.{self.site.name}.countries"
            page_url = self.config_manager.get_config(f"{config_prefix}.url")
            default_timeout = self.config_manager.get_config("browser.timeout")

            html_handler = self.config_manager.get_config(f"{config_prefix}.html_handler")

            future = self.interceptor.submit_task(
                TaskType.OPEN_PAGE,
                url=page_url,
                html_handler=html_handler
            )

            responses, _ = future.result(timeout=default_timeout*2)
            if not responses:
                self.logger.error(f"No response for {page_url}")
                return

            countries = responses[0]
            self.logger.debug(f"Intercepted countries from {self.site.name}: {countries}")
            self.synchronizer.sync(self.site, countries)

        except Exception as e:
            self.logger.error(f"Failed to sync countries from {self.site.name}: {e}")
