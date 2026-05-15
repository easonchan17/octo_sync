import numpy as np
import pandas as pd
import xgboost as xgb
from typing import Optional, Tuple
from sklearn.exceptions import NotFittedError
from sklearn.base import BaseEstimator, ClassifierMixin

class XGBoostClassifier(ClassifierMixin, BaseEstimator):
    _estimator_type = 'classifier'

    def __init__(self, eval_set_size: float = 0.1, **kwargs) -> None:
        self.eval_set_size = eval_set_size
        self.params = kwargs
        self.model = xgb.XGBClassifier(**kwargs)
        self.is_fitted_ = False

    @classmethod
    def load_from_file(
        cls,
        model_path: str,
        eval_set_size: float = 0.1,
        **model_params
    ) -> 'XGBoostClassifier':
        instance = cls(eval_set_size=eval_set_size, **model_params)
        instance.model.load_model(model_path)
        instance.is_fitted_ = True

        return instance

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        sample_weight: pd.Series = None,
        eval_set: Optional[Tuple[pd.DataFrame, pd.Series]] = None,
        **fit_params
    ) -> 'XGBoostClassifier':

        tree_hook = fit_params.pop('_tree_hook', None)

        if eval_set is None and self.eval_set_size > 0:
            split_idx = int(len(X) * (1 - self.eval_set_size))
            X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
            eval_set = [(X_val, y_val)]

            fit_data = (X_train, y_train)
            w_train = sample_weight.iloc[:split_idx] if sample_weight is not None else None
        else:
            fit_data = (X, y)
            w_train = sample_weight

        self.model.fit(
            *fit_data,
            eval_set=eval_set,
            sample_weight=w_train,
            verbose=False,
            **fit_params
        )

        if hasattr(self.model, 'eval_results_'):
            self.eval_results_ = self.model.eval_results_

        if tree_hook is not None and hasattr(self.model, 'best_iteration'):
            tree_hook.append(self.model.best_iteration)

        self.is_fitted_ = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not hasattr(self, 'is_fitted_') or not self.is_fitted_:
            raise NotFittedError("Model not fitted")
        return self.model.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if not hasattr(self, 'is_fitted_') or not self.is_fitted_:
            raise NotFittedError("Model not fitted")
        return self.model.predict_proba(X)

    def get_params(self, deep=True) -> dict:
        params = {
            'eval_set_size': self.eval_set_size,
            **self.params
        }

        if deep and self.model is not None:
            params.update(self.model.get_params())

        return params

    def set_params(self, **params) -> 'XGBoostClassifier':
        if 'eval_set_size' in params:
            self.eval_set_size = params.pop('eval_set_size')

        self.params.update(params)

        if self.model is not None:
            self.model.set_params(**self.params)

        return self

    @property
    def classes_(self) -> np.ndarray:
        if self.model is not None:
            return self.model.classes_

        n_class = self.params.get('num_class', 2)
        return np.arange(n_class)

    @property
    def feature_importances_(self) -> np.ndarray:
        if not hasattr(self, 'is_fitted_') or not self.is_fitted_:
            raise NotFittedError("Model not fitted")

        return self.model.feature_importances_

    @property
    def best_score(self) -> Optional[float]:
        if not hasattr(self, 'is_fitted_') or not self.is_fitted_:
            raise NotFittedError("Model not fitted")

        if not hasattr(self, 'eval_results_') or self.eval_results_ is None:
            return None

        validation_results = None
        for data_name, results in self.eval_results_.items():
            if 'validation' in data_name.lower() or 'eval' in data_name.lower():
                validation_results = results
                break

        if validation_results is None:
            return None

        if 'mlogloss' in validation_results:
            return -min(validation_results['mlogloss'])
        elif 'logloss' in validation_results:
            return -min(validation_results['logloss'])
        elif 'error' in validation_results:
            return -min(validation_results['error'])
        elif 'auc' in validation_results:
            return max(validation_results['auc'])
        elif 'aucpr' in validation_results:
            return max(validation_results['aucpr'])

        return None