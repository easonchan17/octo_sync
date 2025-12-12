import pandas as pd
from pathlib import Path
from datetime import datetime
from skopt import BayesSearchCV
from typing import Any, List, Optional, Tuple
from core.logger.logger_manager import LoggerManager
from core.store.postgres.models import TrainingRecord
from core.store.postgres.postgresql_manager import PostgreSQLManager
from sklearn.metrics import classification_report, confusion_matrix, log_loss
from core.scheduler.tasks.analysis.models.xgboost_classifier import XGBoostClassifier

class ExperimentTracker:
    def __init__(self, config: Any) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.postgresql_manager = PostgreSQLManager.get_instance()
        self.config = config

    def _log_feature_importance(
        self,
        feature_importances: Any,
        feature_names: Any,
        top_n_features: int
    ) -> None:
        self.logger.info("\n" + "-" * 50)
        self.logger.info(f"TOP {top_n_features} FEATURE IMPORTANCE")
        self.logger.info("-" * 50)
        feat_imp_df = pd.DataFrame({
            'Feature': feature_names,
            'Importance': feature_importances
        }).sort_values(by='Importance', ascending=False)

        feat_imp_df['Cumul(%)'] = feat_imp_df['Importance'].cumsum() * 100

        top_features_str = feat_imp_df.head(top_n_features).to_string(
            index=False,
            formatters={
                'Importance': '{:.4f}'.format,
                'Cumul(%)': '{:.1f}%'.format
            }
        )
        self.logger.info(f"\n{top_features_str}")

        total_feats = len(feature_names)
        if total_feats > top_n_features:
            self.logger.info(f"\n... (Showing top {top_n_features} of {total_feats} features)")

    def log_optimization_step(self, res: Any) -> bool:
        current_score = -res.func_vals[-1]
        current_params_list = res.x_iters[-1]
        current_params_dict = dict(zip(res.space.dimension_names, current_params_list))

        iteration = len(res.x_iters)
        self.logger.info(f'[Iteration {iteration} finished]')
        self.logger.info(f'    Current CV Score: {current_score:.4f}')
        self.logger.info(f'    Params: {current_params_dict}')
        return False

    def track_analysis(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        bayes_search: BayesSearchCV,
        top_n_features: Optional[int] = 20
    ) -> float:
        best_estimator = bayes_search.best_estimator_

        y_pred_train = best_estimator.predict(X_train)
        y_prob_train = best_estimator.predict_proba(X_train)
        y_pred_test = best_estimator.predict(X_test)
        y_prob_test = best_estimator.predict_proba(X_test)

        train_log_loss = -bayes_search.best_score_
        test_log_loss = log_loss(y_test, y_prob_test, labels=best_estimator.classes_)

        train_accuracy = best_estimator.score(X_train, y_train)
        test_accuracy = best_estimator.score(X_test, y_test)
        target_names = self.config.target_names

        self.logger.info("\n" + "="*50)
        self.logger.info("MODEL OPTIMIZATION REPORT")
        self.logger.info("="*50)

        self.logger.info(f"Dataset  : {self.config.dataset_name}")
        self.logger.info(f"Best CV Loss: {train_log_loss: .4f} (Lower is better)")
        self.logger.info(f"Test Set Loss : {test_log_loss:.4f} (Lower is better)")
        self.logger.info(f"Train Set Acc: {train_accuracy:.4f} (Higher is better)")
        self.logger.info(f"Test Set Acc: {test_accuracy:.4f} (Higher is better)")

        gap = test_log_loss - train_log_loss
        if gap > 0.05:
            self.logger.warning(f"Potential Overfitting detected! (Log Loss Gap: {gap:.4f})")

        self.logger.info("\n" + "-" * 50)
        self.logger.info("📈 DETAILED CLASSIFICATION REPORT")
        self.logger.info("-" * 50)

        report_dict = classification_report(
            y_test, y_pred_test, target_names=target_names, output_dict=True, zero_division=0.0
        )
        report_df = pd.DataFrame(report_dict).transpose()
        self.logger.info(f"\n{report_df.round(4).to_string()}")

        self.logger.info("\n" + "-" * 50)
        self.logger.info("🔲 CONFUSION MATRIX (Actual vs Predicted)")
        self.logger.info("-" * 50)

        cm = confusion_matrix(y_test, y_pred_test)
        cm_df = pd.DataFrame(
            cm,
            index=[f"True {name}" for name in target_names],
            columns=[f"Pred {name}" for name in target_names]
        )
        self.logger.info(f"\n{cm_df.to_string()}")

        self._log_feature_importance(
            best_estimator.feature_importances_,
            X_test.columns.tolist(),
            top_n_features
        )

        self.logger.info("="*50 + "\n")
        return float(test_accuracy)

    def save_model(self, estimator: XGBoostClassifier) -> Tuple[str, str]:
        base_dir = self.config.model_dir / self.config.model_family
        base_dir.mkdir(parents=True, exist_ok=True)

        inst_version = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_version = f"{self.config.model_version}_{inst_version}"

        file_name = f"{model_version}.json"
        model_path = base_dir / file_name

        booster = estimator.model.get_booster()
        booster.save_model(str(model_path))

        model_path = str(model_path)
        self.logger.info(f"Model artifact saved to: {model_path}")

        return model_path, model_version

    def save_metadata(
        self,
        bayes_search: BayesSearchCV,
        model_path: str,
        model_version: str,
        test_accuracy: float,
        feature_names: List[str]
    ) -> int:
        try:
            record = TrainingRecord(
                training_config=self.config.model_params,
                search_spaces=self.config.hyperparameter_space_config,
                model_path=model_path,
                model_version=model_version,
                model_type=self.config.model_type,
                feature_names=feature_names,
                dataset_name=self.config.dataset_name,
                best_params=dict(bayes_search.best_params_),
                best_score=float(bayes_search.best_score_),
                test_accuracy=float(test_accuracy)
            )

            with self.postgresql_manager.get_session() as session:
                session.add(record)
                session.flush()
                return record.id
        except Exception as e:
            self.logger.error(f"Failed to save training record: {e}", exc_info=True)
            raise
