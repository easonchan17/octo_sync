import numpy as np
from typing import List, Optional
from .base_deriver import BaseDeriver
from ..constants import DEFAULT_DECIMALS

class EntropyDeriver(BaseDeriver):
    def derive(self, feature: str, probability_cols: List[str], decimals: Optional[int] = DEFAULT_DECIMALS) -> None:
        self.ensure_column_does_not_exist(feature)

        for col in probability_cols:
            self.ensure_column_exists(col)

        p = self.df[probability_cols]
        term = p * np.log(p.replace(0, 1.0))

        entropy = -term.sum(axis=1, skipna=False)

        if decimals is not None:
            entropy = entropy.round(decimals)

        self.df[feature] = entropy
        self.logger.info(f"Created {feature} from probability columns: {probability_cols}")