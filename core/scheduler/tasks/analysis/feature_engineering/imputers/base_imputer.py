import pandas as pd
from abc import abstractmethod
from ..context import FeatureContext

class BaseImputer(FeatureContext):
    def get_null_mask(self, feature: str) -> pd.Series:
        self.ensure_column_exists(feature)
        return self.df[feature].isna()

    @abstractmethod
    def impute(self, *args, **kwargs) -> None:
        pass
