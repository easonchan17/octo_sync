import numpy as np
from typing import Optional, List, Any
from .base import BaseTransform
from ..constants import DEFAULT_DECIMALS

class FormulaMutator(BaseTransform):
    def mutate(self, col: str, formula: str, decimals: Optional[int] = DEFAULT_DECIMALS) -> None:
        self._require_no_col(col)

        new_series = self.df.eval(formula, local_dict={'np': np, 'log': np.log})
        if decimals is not None:
            new_series = new_series.round(decimals)

        self.df[col] = new_series
        self.logger.info(f"Created {col} with formula: {formula}")

    def mutate_batch(self, cols: List[Any]) -> None:
        for col, formula in cols:
            self.mutate(col, formula)

class EntropyMutator(BaseTransform):
    def build(self, col: str, probability_cols: List[str], decimals: Optional[int] = DEFAULT_DECIMALS) -> None:
        for prob_col in probability_cols:
            self._require_col(prob_col)

        p = self.df[probability_cols]
        term = p * np.log(p.replace(0, 1.0))

        entropy = -term.sum(axis=1, skipna=False)

        if decimals is not None:
            entropy = entropy.round(decimals)

        self.df[col] = entropy
        self.logger.info(f"Created {col} from probability columns: {probability_cols}")
