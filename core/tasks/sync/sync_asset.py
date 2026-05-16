import os
from datetime import timedelta
from core.types.enums import SiteName
from core.tasks.poll_task import PollTask
from core.config.config_manager import ConfigManager
from core.store.postgres.daos.common import AssetDao
from core.scheduler.task_registry import TaskRegistry
from core.tasks.refetch_strategy import AttemptStrategy
from core.browser.intercept_strategy import InterceptStrategy, InterceptType
from core.browser.handlers.receivers import AssetReceiver

class SyncAsset(PollTask):
    INTERCEPT_STRATEGY = {
        "rules": [
            {
                "type": InterceptType.ASSET,
                "receiver": AssetReceiver
            }
        ]
    }

    def __init__(self, site_name: str) -> None:
        super().__init__(site_name=site_name)
        self.base_dir = ConfigManager.get_instance().get_config('resource.asset')
        self.asset_dao = AssetDao()

        self.intercept_strategy = InterceptStrategy.from_rules(self.INTERCEPT_STRATEGY)
        self.retry_strategy = (
            AttemptStrategy()
            .add_segment(min_attempts=1, max_attempts=4, interval=timedelta(minutes=5))
            .add_segment(min_attempts=4, max_attempts=7, interval=timedelta(minutes=15))
            .add_segment(min_attempts=7, max_attempts=10, interval=timedelta(hours=4))
            .add_segment(min_attempts=10, max_attempts=None, interval=timedelta(days=1))
        )


    def make_save_path(self, asset_type: str, entity_type: str, asset_usage: str, file_name: str, file_ext: str) -> str:
        dir_path = os.path.join(self.base_dir, asset_type, entity_type, asset_usage)
        os.makedirs(dir_path, exist_ok=True)

        file_name = f'{file_name}.{file_ext}' if file_ext else file_name
        return os.path.join(dir_path, file_name)

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.asset_dao.get_pending_fetch_items(self.site_name)

                if not items:
                    self.idle_sleep()
                    continue

                for source_url, asset_type, entity_type, asset_usage, file_name, file_ext, fetch_attempts in items:
                    if self.should_stop():
                        return

                    try:
                        future = self.interceptor.submit(
                            url=source_url,
                            strategy=self.intercept_strategy,
                            site_name=self.site_name
                        )

                        result_set = future.result()
                        if result_set is None or result_set.is_empty() or result_set.is_not_modified():
                            self.logger.warning(f"No asset data received: url={source_url}")
                            retry_interval = self.retry_strategy.suggest_interval(fetch_attempts)
                            self.asset_dao.mark_fetch_failed(source_url, retry_interval)
                            continue

                        save_path = self.make_save_path(
                            asset_type, entity_type, asset_usage, file_name, file_ext
                        )
                        with open(save_path, 'wb') as asset_file:
                            asset_file.write(result_set.first())

                        self.asset_dao.mark_as_fetched(source_url)
                        self.logger.info(f"Downloaded asset: url={source_url}")
                    except Exception as e:
                        retry_interval = self.retry_strategy.suggest_interval(fetch_attempts)
                        self.asset_dao.mark_fetch_failed(source_url, retry_interval)
                        self.logger.error(f"Failed to download asset, url={source_url}: {e}")
                        self.idle_sleep()

            except Exception as e:
                self.logger.error(f"SyncAsset error: {e}", exc_info=True)
                self.idle_sleep()


TaskRegistry.poll('sync.fotmob.asset')(
    lambda _: SyncAsset(site_name=SiteName.FOTMOB.value)
)
