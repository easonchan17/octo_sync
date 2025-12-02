import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional, Set, List
from abc import abstractmethod
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask
from core.store.postgres.postgresql_manager import PostgreSQLManager

class BaseAnalyzer(BaseTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]]) -> None:
        super().__init__()
        self.site = site
        self.payload = payload
        self.postgresql_manager = PostgreSQLManager.get_instance()

    def build_output_file(self, comp_code: str, min_season: int, max_season: int, output_format: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.__class__.__name__}_{comp_code}_{min_season}_{max_season}_{timestamp}.{output_format}"

    def check_output_path(self, output_path: str, output_file: str) -> Path:
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / output_file

    def execute(self, *args, **kwargs) -> None:
        comp_code = self.payload["comp_code"]
        min_season = self.payload["min_season"]
        max_season = self.payload["max_season"]
        output_format = self.payload.get("format", "csv")

        output_path = self.config_manager.get_config("features.path")
        output_file = self.build_output_file(
            comp_code,
            min_season,
            max_season,
            output_format
        )
        output_path = self.check_output_path(output_path, output_file)

        try:
            stats = self.query_raw_data(comp_code, min_season, max_season)
            if not stats:
                self.logger.warning(f"No data found for comp_code={comp_code}, seasons={min_season}-{max_season}")
                return

            self.logger.info(f"Data queried for comp_code={comp_code}, seasons={min_season}-{max_season}")
            df = self.do_feature_engineering(stats, self.payload.get("required_features"))
            self.logger.info(f"Data feature engineering completed")
            self.save_output(df, output_path)
            self.logger.info(f"Output saved to: {str(output_path.resolve())}")
        except Exception as e:
            self.logger.error(f"Error saving output: {e}", exc_info=True)

    def save_output(self, df: pd.DataFrame, output_path: Path) -> None:
        # feature_list_path = output_path.parent / f"feature_{output_path.name}"
        # feature_df = pd.DataFrame({"feature_name": df.columns})

        if output_path.suffix == ".csv":
            df.to_csv(output_path, index=False)
            # feature_df.to_csv(feature_list_path, index=False)
        elif output_path.suffix == ".json":
            df.to_json(output_path, orient="records", indent=2)
            # feature_df.to_json(feature_list_path, orient="records", indent=2)
        elif output_path.suffix == ".parquet":
            df.to_parquet(output_path, index=False)
            # feature_df.to_parquet(feature_list_path, index=False)
        else:
            raise ValueError(f"Unsupported output format: {output_path.suffix}")

    @abstractmethod
    def query_raw_data(self, comp_code: str, min_season: int, max_season: int) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def do_feature_engineering(
        self,
        stats: List[Dict[str, Any]],
        required_features: Optional[List[str]] = None
    ) -> Optional[pd.DataFrame]:
        pass