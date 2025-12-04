import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.base import BaseEstimator

class XGBoostClassifier(BaseEstimator):
    def __init__(self, test_size=0.2, **kwargs) -> None:
        self.xgb_params = kwargs
        self.test_size = test_size
        self.model = None

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        sample_weight: pd.Series = None,
        eval_set=None,
        **fit_params
    ) -> 'XGBoostClassifier':
        if eval_set is None:
            split_idx = int(len(X) * (1 - self.test_size))
            X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

            w_train = None
            if sample_weight is not None:
                w_train = sample_weight.iloc[:split_idx]
            eval_set = [(X_val, y_val)]
            fit_data = (X_train, y_train)
        else:
            fit_data = (X, y)
            w_train = sample_weight

        self.model = xgb.XGBClassifier(**self.xgb_params)
        self.model.fit(
            *fit_data,
            eval_set=eval_set,
            sample_weight=w_train,
            verbose=False,
            **fit_params
        )
        return self

    def predict(self, X) -> np.ndarray:
        return self.model.predict(X)

    def predict_proba(self, X) -> np.ndarray:
        return self.model.predict_proba(X)

    def score(self, X, y) -> float:
        return self.model.score(X, y)

    def get_params(self, deep=True) -> dict:
        return {**self.xgb_params}

    def set_params(self, **params) -> 'XGBoostClassifier':
        self.xgb_params.update(params)
        return self
