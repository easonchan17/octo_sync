import pandas as pd
from typing import Tuple
from datetime import datetime
from core.logger.logger_manager import LoggerManager
from core.store.postgres.models import TrainingRecord
from core.store.postgres.postgresql_manager import PostgreSQLManager
from sklearn.metrics import classification_report, confusion_matrix, log_loss
from core.services.ml.training.base_trainer_config import BaseTrainerConfig

class BaseTracker:
    def __init__(self, config: BaseTrainerConfig) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.db = PostgreSQLManager.get_instance()
        self.config = config
        self.optimizer = None
        self.train_score = None
        self.test_score = None
        self.score_gap = None
        self.test_report_df = None
        self.test_cm_df = None
        self.feature_names = None
        self.feat_imp_df = None

    def analysis(self, X_test: pd.DataFrame, y_test: pd.Series) -> None:
        if self.optimizer is None:
            raise ValueError("Optimizer is not set")

        best_estimator = self.optimizer.best_estimator_
        best_score = self.optimizer.best_score_

        y_prob_test = best_estimator.predict_proba(X_test)
        scoring = self.config.scoring

        if scoring == 'neg_log_loss':
            train_score = -best_score
            test_score = log_loss(y_test, y_prob_test, labels=best_estimator.classes_)
            score_gap = test_score - train_score
        elif scoring == 'accuracy':
            train_score = best_score
            test_score = best_estimator.score(X_test, y_test)
            score_gap = train_score - test_score
        else:
            raise ValueError(f"Invalid scoring method: {scoring}")

        target_names = self.config.target_names
        y_pred_test = best_estimator.predict(X_test)
        report_dict = classification_report(
            y_test, y_pred_test,
            target_names=target_names,
            output_dict=True,
            zero_division=0.0
        )
        report_df = pd.DataFrame(report_dict).transpose()

        cm = confusion_matrix(y_test, y_pred_test)
        cm_df = pd.DataFrame(
            cm,
            index=[f"True {name}" for name in target_names],
            columns=[f"Pred {name}" for name in target_names]
        )

        feature_names = X_test.columns.tolist()
        feat_imp_df = pd.DataFrame({
            'Feature': feature_names,
            'Importance': best_estimator.feature_importances_
        }).sort_values(by='Importance', ascending=False)

        self.train_score = train_score
        self.test_score = test_score
        self.score_gap = score_gap
        self.test_report_df = report_df
        self.test_cm_df = cm_df
        self.feature_names = feature_names
        self.feat_imp_df = feat_imp_df


    def save_model(self) -> Tuple[str, str]:
        base_dir = self.config.model_dir / self.config.model_family
        base_dir.mkdir(parents=True, exist_ok=True)

        inst_version = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_version = f"{self.config.model_version}_{inst_version}"

        file_name = f"{model_version}.json"
        model_path = base_dir / file_name

        booster = self.optimizer.best_estimator_.model.get_booster()
        booster.save_model(str(model_path))

        model_path = str(model_path)
        self.logger.info(f"Model artifact saved to: {model_path}")

        return model_path, model_version

    def save_metadata(self,model_path: str, model_version: str) -> None:
        try:
            record = TrainingRecord(
                model_version=model_version,
                model_type=self.config.model_type,
                model_path=model_path,
                dataset_name=self.config.dataset_name,
                feature_names=self.feature_names,
                training_params=self.config.training_params,
                best_params=dict(self.optimizer.best_params_),
                train_score=float(self.train_score),
                test_score=float(self.test_score)
            )

            with self.db.get_session() as session:
                session.add(record)
                session.flush()
                self.logger.info(f"Training record saved to database: {record.id}")
        except Exception as e:
            self.logger.error(f"Failed to save training record: {e}", exc_info=True)


    def report(self) -> None:
        self.logger.info("\n" + "="*50)
        self.logger.info("MODEL OPTIMIZATION REPORT")
        self.logger.info("="*50)
        self.logger.info(f"Dataset  : {self.config.dataset_name}")
        self.logger.info(f"Best CV Score: {self.train_score: .4f}")
        self.logger.info(f"Test Set Score : {self.test_score:.4f}")
        if self.score_gap > 0.05:
            self.logger.warning(f"Potential Overfitting detected! (Gap: {self.score_gap:.4f})")

        self.logger.info("\n" + "-" * 50)
        self.logger.info("DETAILED CLASSIFICATION REPORT")
        self.logger.info("-" * 50)
        self.logger.info(f"\n{self.test_report_df.round(4).to_string()}")

        self.logger.info("\n" + "-" * 50)
        self.logger.info("CONFUSION MATRIX (Actual vs Predicted)")
        self.logger.info("-" * 50)
        self.logger.info(f"\n{self.test_cm_df.to_string()}")

        self.logger.info("\n" + "-" * 50)
        self.logger.info(f"FEATURE IMPORTANCE")
        self.logger.info("-" * 50)
        self.feat_imp_df['Cumul(%)'] = self.feat_imp_df['Importance'].cumsum() * 100
        all_features_str = self.feat_imp_df.to_string(
            index=False,
            formatters={
                'Importance': '{:.4f}'.format,
                'Cumul(%)': '{:.1f}%'.format
            }
        )
        self.logger.info(f"\n{all_features_str}")
