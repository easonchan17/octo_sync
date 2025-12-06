import numpy as np
from typing import List, Any
from ..processor import FeatureProcessor

class ConditionalDeriver(FeatureProcessor):
    def process(self, feature: str, conditions: List[str], choices: List[Any]) -> None:
        self.ensure_column_does_not_exist(feature)

        if not conditions:
            raise ValueError("Conditions cannot be empty")

        if not choices:
            raise ValueError("Choices cannot be empty")

        if len(conditions) != len(choices):
            raise ValueError("Conditions and choices must have the same length")

        np_conditions = [self.df.eval(cond) for cond in conditions]
        self.df[feature] = np.select(np_conditions, choices)

        self.logger.info(f"Created conditional feature {feature} with {len(choices)} choices")
