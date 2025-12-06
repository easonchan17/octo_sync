import pandas as pd
from pathlib import Path
from skopt import BayesSearchCV
from skopt.space import Real, Integer
from typing import Optional, Dict, Any
from core.utils.pandas_utils import load_dataframe
from sklearn.model_selection import TimeSeriesSplit
from core.scheduler.tasks.base_task import BaseTask
from .xgboost_classifier import XGBoostClassifier

class BayesianOptimizeTrainer(BaseTask):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.data_file = payload['data_file']
        self.test_size = payload.get('test_size', 0.2)
        self.iter_count = payload.get('iter_count', 300)
        self.num_class = payload.get('num_class', 3)
        self.early_stopping_rounds = payload.get('early_stopping_rounds', 50)
        self.random_state = payload.get('random_state', 1)

    def bayesian_optimization(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        early_stopping_rounds=50,
        test_size=0.2,
        iter_count=300,
        num_class=3,
        random_state=1
    ) -> BayesSearchCV:
        search_spaces = {
            'max_depth': Integer(3, 8),
            'learning_rate': Real(0.005, 0.1, prior='log-uniform'),
            'n_estimators': Integer(300, 2000),
            'subsample': Real(0.6, 0.95),
            'colsample_bytree': Real(0.6, 0.95),
            'reg_alpha': Real(0.1, 10),
            'reg_lambda': Real(1, 10),
            'min_child_weight': Integer(5, 50),
            'gamma': Real(0, 5)
        }

        xgb_model = XGBoostClassifier(
            test_size=test_size,
            early_stopping_rounds=early_stopping_rounds,
            objective='multi:softprob',
            num_class=num_class,
            eval_metric='mlogloss',
            tree_method='hist',
            n_jobs=-1,
            random_state=random_state
        )

        bayes_search = BayesSearchCV(
            estimator=xgb_model,
            search_spaces=search_spaces,
            n_iter=iter_count,
            cv=TimeSeriesSplit(n_splits=5),
            scoring='accuracy',
            # scoring='neg_log_loss',
            random_state=random_state,
            n_jobs=1,
            verbose=0
        )

        def on_step(res):
            if self.should_stop():
                return True

            current_accuracy = -res.func_vals[-1]
            current_params_list = res.x_iters[-1]
            current_params_dict = dict(zip(res.space.dimension_names, current_params_list))

            iteration = len(res.x_iters)
            self.logger.info(f'[Iteration {iteration} finished]')
            self.logger.info(f'    Current CV Accuracy: {current_accuracy:.4f}')
            self.logger.info(f'    Params: {current_params_dict}')
            return False

        bayes_search.fit(X_train, y_train, callback=[on_step])

        if self.should_stop():
            self.logger.warning("Training stopped gracefully by user request")
            return None

        self.logger.info("\n--- Bayesian Optimization Results ---")
        self.logger.info(f"Sample dataset: {self.data_file}")
        self.logger.info(f'Best score: {bayes_search.best_score_}')
        self.logger.info(f'Best params: {bayes_search.best_params_}')
        return bayes_search

    def analyze_predictions_on_test_set(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        bayes_search: BayesSearchCV
    ) -> None:
        best_model = bayes_search.best_estimator_.model
        y_pred = best_model.predict(X_test)
        y_pred_proba = best_model.predict_proba(X_test)

        results_df = X_test.reset_index(drop=True).copy()
        results_df['actual'] = y_test.reset_index(drop=True)
        results_df['predicted'] = y_pred
        results_df['is_correct'] = (results_df['actual'] == results_df['predicted']).astype(int)

        class_labels = sorted(y_test.unique())
        proba_cols = [f'P(Class {c})' for c in class_labels]
        results_df[proba_cols] = pd.DataFrame(y_pred_proba, index=results_df.index, columns=proba_cols)

        self.logger.info("\n--- Independent Test Set Prediction Analysis (Last 20% Data) ---")
        self.logger.info(f"Sample dataset: {self.data_file}")
        self.logger.info(f"Overall Test Set Accuracy: {results_df['is_correct'].mean():.4f}")
        self.logger.info("\n**Prediction Accuracy by Actual Result Category:**")
        class_names = {0: "Home Loss", 1: "Draw", 2: "Home Win"}
        for class_label in class_labels:
            class_mask = results_df['actual'] == class_label
            class_count = class_mask.sum()
            if class_count > 0:
                class_accuracy = results_df.loc[class_mask, 'is_correct'].mean()
                class_name = class_names.get(class_label, f"Class {class_label}")
                self.logger.info(f"  Actual Result={class_name} (Class {class_label}): "
                    f"Accuracy={class_accuracy:.4f} ({class_count} matches)")
            else:
                class_name = class_names.get(class_label, f"Class {class_label}")
                self.logger.info(f"  Actual Result={class_name} (Class {class_label}): No data")

        self.logger.info("\n**Prediction Examples (with probabilities):**")
        self.logger.info(results_df[['actual', 'predicted', 'is_correct']].head(10))

        self.logger.info("\n**Error Analysis Examples:**")
        misclassified = results_df[results_df['is_correct'] == 0]
        self.logger.info(misclassified[['actual', 'predicted', 'is_correct']].head(5))

        results_file = "prediction_analysis_results.csv"
        results_df.to_csv(results_file, index=False)
        self.logger.info(f"Analysis results saved to: {results_file}")

        if hasattr(best_model, 'feature_importances_'):
            imps = pd.DataFrame({
                'feature': X_test.columns,
                'importance': best_model.feature_importances_
            }).sort_values('importance', ascending=False)

            self.logger.info("\n--- Top 20 Feature Importances ---")
            self.logger.info(imps.head(20))

    def execute(self, *args, **kwargs) -> None:
        output_path = self.config_manager.get_config("features.path")
        output_path = Path(output_path)
        df = load_dataframe(output_path/self.data_file)

        y = df['home_point'].copy()
        y = y.replace(3, 2)

        columns_to_drop = [
            'kickoff_time',
            'comp_name',
            'match_code',
            'page_url',
            'match_report',
            'home_team',
            'home_code',
            'away_team',
            'away_code',
            'home_point',
        ]
        existing_columns_to_drop = [col for col in columns_to_drop if col in df.columns]
        if existing_columns_to_drop:
            X = df.drop(columns=existing_columns_to_drop, axis=1)
        else:
            X = df.copy()

        missing_columns = [col for col in columns_to_drop if col not in df.columns]
        if missing_columns:
            self.logger.warning(f"Columns not found in DataFrame (skipped): {missing_columns}")


        # with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.width', None):
        #     self.logger.info("\n%s", X.head())
        self.logger.info(X.head())

        split_idx = int(len(X) * (1 - self.test_size))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

        bayes_search = self.bayesian_optimization(
            pd.DataFrame(X_train, columns=X_train.columns, index=X_train.index),
            y_train,
            early_stopping_rounds=self.early_stopping_rounds,
            test_size=self.test_size,
            iter_count=self.iter_count,
            num_class=self.num_class,
            random_state=self.random_state
        )

        if not bayes_search:
            self.logger.warning("No model found, skipping prediction analysis")
            return

        self.analyze_predictions_on_test_set(
            pd.DataFrame(X_test, columns=X_test.columns, index=X_test.index),
            y_test,
            bayes_search
        )