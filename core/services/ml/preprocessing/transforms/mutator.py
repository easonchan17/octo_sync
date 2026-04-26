import numpy as np
from typing import Optional
from .base import BaseTransform
from ..constants import DEFAULT_DECIMALS

class FormulaMutator(BaseTransform):
    def mutate(self, col: str, formula: str, decimals: Optional[int] = DEFAULT_DECIMALS) -> 'FormulaMutator':
        self._require_no_col(col)

        new_series = self.df.eval(formula, local_dict={'np': np, 'log': np.log})
        if decimals is not None:
            new_series = new_series.round(decimals)

        self.df[col] = new_series
        self.logger.info(f"Created {col} with formula: {formula}")
        return self
