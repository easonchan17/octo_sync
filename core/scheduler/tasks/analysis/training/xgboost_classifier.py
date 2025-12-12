import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.base import BaseEstimator, ClassifierMixin

class XGBoostClassifier(BaseEstimator, ClassifierMixin):
    def __init__(self, eval_set_size: float = 0.1, **kwargs) -> None:
        self.eval_set_size = eval_set_size
        self.xgb_params = kwargs
        self.model = None

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        sample_weight: pd.Series = None,
        eval_set=None,
        **fit_params
    ) -> 'XGBoostClassifier':
        if eval_set is None and self.eval_set_size > 0:
            split_idx = int(len(X) * (1 - self.eval_set_size))
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

    def get_params(self, deep=True) -> dict:
        params = {
            'eval_set_size': self.eval_set_size,
            **self.xgb_params
        }
        return params

    def set_params(self, **params) -> 'XGBoostClassifier':
        if 'eval_set_size' in params:
            self.eval_set_size = params.pop('eval_set_size')

        self.xgb_params.update(params)
        return self

    @property
    def feature_importances_(self) -> np.ndarray:
        if self.model is None:
            raise ValueError("Model has not been fitted yet. Call fit() first.")
        return self.model.feature_importances_
