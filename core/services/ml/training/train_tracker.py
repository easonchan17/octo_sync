import shap
import numpy as np
import pandas as pd
from typing import Tuple
from datetime import datetime
from core.logger.logger_manager import LoggerManager
from core.store.postgres.models import TrainingRecord
from core.store.postgres.postgresql_manager import PostgreSQLManager
from sklearn.metrics import classification_report, confusion_matrix, log_loss
from .train_config import BaseTrainConfig

class TrainTracker:
    def __init__(self, config: BaseTrainConfig) -> None:
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
        self.shap_imp_df = None
        self.high_corr_pairs = None

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

        explainer = shap.TreeExplainer(best_estimator.model)
        shap_values = explainer.shap_values(X_test)
        if isinstance(shap_values, list):
            mean_abs_shap = pd.Series(
                sum(abs(sv).mean(axis=0) for sv in shap_values) / len(shap_values),
                index=feature_names
            )
        elif shap_values.ndim == 3:
            mean_abs_shap = pd.Series(abs(shap_values).mean(axis=(0, 2)), index=feature_names)
        else:
            mean_abs_shap = pd.Series(abs(shap_values).mean(axis=0), index=feature_names)

        shap_imp_df = pd.DataFrame({
            'Feature': feature_names,
            'SHAP': mean_abs_shap.values
        }).sort_values(by='SHAP', ascending=False).reset_index(drop=True)
        shap_imp_df['Rank'] = shap_imp_df.index + 1
        shap_imp_df['CumulSHAP(%)'] = shap_imp_df['SHAP'].cumsum() / shap_imp_df['SHAP'].sum() * 100

        corr_matrix = X_test.corr().abs()
        upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
        high_corr_pairs = (
            upper.stack()
            .reset_index()
            .rename(columns={'level_0': 'Feature_A', 'level_1': 'Feature_B', 0: 'Corr'})
            .query('Corr > 0.85')
            .sort_values('Corr', ascending=False)
            .reset_index(drop=True)
        )

        self.train_score = train_score
        self.test_score = test_score
        self.score_gap = score_gap
        self.test_report_df = report_df
        self.test_cm_df = cm_df
        self.feature_names = feature_names
        self.feat_imp_df = feat_imp_df
        self.shap_imp_df = shap_imp_df
        self.high_corr_pairs = high_corr_pairs


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
        self.logger.info("FEATURE IMPORTANCE (Gain)")
        self.logger.info("-" * 50)
        self.feat_imp_df['Cumul(%)'] = self.feat_imp_df['Importance'].cumsum() * 100
        self.logger.info(f"\n{self.feat_imp_df.to_string(index=False, formatters={'Importance': '{:.4f}'.format, 'Cumul(%)': '{:.1f}%'.format})}")

        self.logger.info("\n" + "-" * 50)
        self.logger.info("FEATURE IMPORTANCE (SHAP mean |value|)")
        self.logger.info("-" * 50)
        self.logger.info(f"\n{self.shap_imp_df.to_string(index=False, formatters={'SHAP': '{:.4f}'.format, 'CumulSHAP(%)': '{:.1f}%'.format})}")

        cutoff = int(len(self.shap_imp_df) * 0.7)
        bottom_30 = self.shap_imp_df.iloc[cutoff:]
        self.logger.info(f"\n[SHAP Bottom 30% — candidates for removal ({len(bottom_30)} features)]")
        self.logger.info(f"\n{bottom_30[['Rank', 'Feature', 'SHAP']].to_string(index=False, formatters={'SHAP': '{:.4f}'.format})}")

        self.logger.info("\n" + "-" * 50)
        self.logger.info("HIGH CORRELATION PAIRS (|corr| > 0.85)")
        self.logger.info("-" * 50)
        if self.high_corr_pairs.empty:
            self.logger.info("No high correlation pairs found.")
        else:
            self.logger.info(f"\n{self.high_corr_pairs.to_string(index=False, formatters={'Corr': '{:.3f}'.format})}")
