import json
import shap
import numpy as np
import pandas as pd
from typing import Optional, Tuple
from datetime import datetime
from sklearn.frozen import FrozenEstimator
from sklearn.calibration import CalibratedClassifierCV
from core.logger.logger_manager import get_logger_manager
from core.store.postgres.models import TrainingRecord
from core.store.postgres.postgresql_manager import get_postgresql_manager
from sklearn.metrics import classification_report, confusion_matrix, log_loss
from .train_config import BaseTrainConfig

class TrainTracker:
    MARKET_BASELINE_COLS = ['market_median_away_real', 'market_median_draw_real', 'market_median_home_real']
    MARKET_VIG_COL = 'market_median_vig_close'
    DRAW_CLASS = 'Draw'
    DRAW_COL = 'T_draw'

    @classmethod
    def validate_dataset(cls, df: pd.DataFrame) -> None:
        required = cls.MARKET_BASELINE_COLS + [cls.MARKET_VIG_COL]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Dataset is missing required columns {missing}; rebuild the dataset")

    def __init__(self, config: BaseTrainConfig) -> None:
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)
        self.db = get_postgresql_manager()
        self.config = config
        self.draw_class_idx = list(self.config.target_names).index(self.DRAW_CLASS)
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
        self.calibrator = None
        self.calibrator_path = None
        self.calib_draw_threshold_report = None
        self.market_baseline_score = None
        self.calibrated_test_score = None
        self.blend_weight = None
        self.blended_test_score = None
        self.draw_fair_mean = None
        self.draw_fair_mean_true = None
        self.market_vig_mean = None

    def _fit_blend_weight(self, market_probs: np.ndarray, model_probs: np.ndarray, y_true: pd.Series, labels: np.ndarray) -> float:
        candidate_weights = np.linspace(0.0, 1.0, 101)
        best_weight, best_score = 0.0, float('inf')
        for weight in candidate_weights:
            blended_probs = weight * market_probs + (1 - weight) * model_probs
            score = log_loss(y_true, blended_probs, labels=labels)
            if score < best_score:
                best_score, best_weight = score, weight
        return best_weight

    def analysis(
        self,
        X_test: pd.DataFrame, y_test: pd.Series,
        market_probs_test: np.ndarray, market_vig_test: np.ndarray, market_probs_calib: Optional[np.ndarray] = None,
        X_calib: Optional[pd.DataFrame] = None, y_calib: Optional[pd.Series] = None,
    ) -> None:
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
            market_baseline_score = log_loss(y_test, market_probs_test, labels=best_estimator.classes_)
        elif scoring == 'accuracy':
            train_score = best_score
            test_score = best_estimator.score(X_test, y_test)
            score_gap = train_score - test_score
            market_pred = np.argmax(market_probs_test, axis=1)
            market_baseline_score = (market_pred == y_test.values).mean()
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
        self.market_baseline_score = market_baseline_score
        self.test_report_df = report_df
        self.test_cm_df = cm_df
        self.feature_names = feature_names
        self.feat_imp_df = feat_imp_df
        self.shap_imp_df = shap_imp_df
        self.high_corr_pairs = high_corr_pairs
        self.draw_fair_mean = market_probs_test[:, self.draw_class_idx].mean()
        self.market_vig_mean = market_vig_test.mean()
        draw_baseline = self.draw_fair_mean * self.market_vig_mean
        self.draw_fair_mean_true = market_probs_test[y_test.values == self.draw_class_idx, self.draw_class_idx].mean()
        self.draw_threshold_report = self._build_draw_threshold_report(y_prob_test, y_test)
        self.draw_threshold = self._optimize_draw_threshold(self.draw_threshold_report, draw_baseline)
        self.draw_class = self.draw_class_idx

        if X_calib is not None and y_calib is not None:
            calibrator = CalibratedClassifierCV(FrozenEstimator(best_estimator), method='sigmoid')
            calibrator.fit(X_calib, y_calib)
            y_prob_calib = calibrator.predict_proba(X_test)
            self.calibrator = calibrator
            self.calib_draw_threshold_report = self._build_draw_threshold_report(y_prob_calib, y_test)
            self.draw_threshold = self._optimize_draw_threshold(self.calib_draw_threshold_report, draw_baseline)
            self.calibrated_test_score = log_loss(y_test, y_prob_calib, labels=best_estimator.classes_)

            model_probs_calib = best_estimator.predict_proba(X_calib)
            self.blend_weight = self._fit_blend_weight(market_probs_calib, model_probs_calib, y_calib, best_estimator.classes_)
            blended_probs_test = self.blend_weight * market_probs_test + (1 - self.blend_weight) * y_prob_test
            self.blended_test_score = log_loss(y_test, blended_probs_test, labels=best_estimator.classes_)

        profit_score_col = ((self.draw_threshold_report['Draw Precision'] - draw_baseline).clip(lower=0.0) * self.draw_threshold_report['Draw Recall']).round(5)
        self.draw_threshold_report['Profit Score'] = profit_score_col
        if self.calib_draw_threshold_report is not None:
            calib_profit_score_col = ((self.calib_draw_threshold_report['Draw Precision'] - draw_baseline).clip(lower=0.0) * self.calib_draw_threshold_report['Draw Recall']).round(5)
            self.calib_draw_threshold_report['Profit Score'] = calib_profit_score_col


    def _build_draw_threshold_report(self, y_prob: np.ndarray, y_true: pd.Series, t_min: float = 0.24, t_max: float = 0.40, steps: int = 17) -> pd.DataFrame:
        home_indices = [i for i in range(y_prob.shape[1]) if i != self.draw_class_idx]

        rows = []
        for t in np.linspace(t_min, t_max, steps):
            t = round(t, 2)
            non_draw = np.take(home_indices, np.argmax(y_prob[:, home_indices], axis=1))
            y_pred = np.where(y_prob[:, self.draw_class_idx] >= t, self.draw_class_idx, non_draw)
            report = classification_report(y_true, y_pred, target_names=self.config.target_names, output_dict=True, zero_division=0.0)
            rows.append({
                self.DRAW_COL:    t,
                "Draw Precision": round(report[self.DRAW_CLASS]["precision"], 4),
                "Draw Recall":    round(report[self.DRAW_CLASS]["recall"],    4),
                "Draw F1":        round(report[self.DRAW_CLASS]["f1-score"],  4),
                "Macro F1":       round(report["macro avg"]["f1-score"], 4),
            })
        return pd.DataFrame(rows)

    def _optimize_draw_threshold(self, scan_df: pd.DataFrame, draw_baseline: float) -> float:
        df = scan_df.copy()
        precision_premium = (df['Draw Precision'] - draw_baseline).clip(lower=0.0)
        df['profit_volume_score'] = precision_premium * df['Draw Recall']
        if df['profit_volume_score'].max() == 0:
            self.logger.warning("No positive EV threshold found, falling back to Macro F1")
            return float(df.loc[df['Macro F1'].idxmax(), self.DRAW_COL])
        return float(df.loc[df['profit_volume_score'].idxmax(), self.DRAW_COL])

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

        if self.calibrator is not None:
            calib_path = base_dir / f"{model_version}_calibrator.json"
            calibrated_clf = self.calibrator.calibrated_classifiers_[0]
            calib_params = [{'a': float(cal.a_), 'b': float(cal.b_)} for cal in calibrated_clf.calibrators]
            calib_path.write_text(json.dumps(calib_params), encoding='utf-8')
            self.calibrator_path = str(calib_path)
            self.logger.info(f"Calibrator saved to: {calib_path.resolve()}")

        return model_path, model_version

    def save_metadata(self,model_path: str, model_version: str) -> None:
        try:
            record = TrainingRecord(
                model_version=model_version,
                model_family=self.config.model_family,
                model_type=self.config.model_type,
                model_path=model_path,
                dataset_name=self.config.dataset_name,
                feature_names=self.feature_names,
                training_params={
                    **self.config.training_params,
                    'draw_threshold': self.draw_threshold,
                    'draw_class': self.draw_class,
                    'calibrator_path': self.calibrator_path,
                },
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


    def report(self, model_version: str) -> None:
        lines = []
        lines.append("=" * 50)
        lines.append("MODEL OPTIMIZATION REPORT")
        lines.append("=" * 50)
        lines.append(f"Model Version         : {model_version}")
        lines.append(f"Dataset               : {self.config.dataset_name}")
        lines.append(f"Balanced              : {self.config.balanced}")
        lines.append(f"Feature Count         : {len(self.feature_names)}")
        lines.append(f"Eval Set Size         : {self.config.eval_set_size}")
        lines.append(f"Calibration Set Size  : {self.config.calibration_set_size}")
        lines.append(f"Test Set Size         : {self.config.test_set_size}")
        lines.append(f"Scoring               : {self.config.scoring}")
        lines.append(f"N Iter                : {self.config.optimizer_params.get('n_iter')}")
        lines.append(f"Early Stopping Rounds : {self.config.model_params.get('early_stopping_rounds')}")
        lines.append(f"Best CV Score         : {self.train_score:.4f}")
        lines.append(f"Test Set Score        : {self.test_score:.4f}")
        lines.append(f"Market Baseline Score : {self.market_baseline_score:.4f}")
        if self.calibrated_test_score is not None:
            lines.append(f"Calibrated Test Score : {self.calibrated_test_score:.4f}")
        if self.blended_test_score is not None:
            lines.append(f"Blended Test Score    : {self.blended_test_score:.4f}")
            lines.append(f"Blend Weight (market) : {self.blend_weight:.2f}")
        lines.append(f"Draw Threshold        : {self.draw_threshold:.2f}")
        lines.append(f"Draw Fair Mean (All)  : {self.draw_fair_mean:.4f}")
        lines.append(f"Draw Fair Mean (True) : {self.draw_fair_mean_true:.4f}")
        lines.append(f"Market Vig Mean       : {self.market_vig_mean:.4f}")
        if self.score_gap > 0.05:
            lines.append(f"WARNING: Potential Overfitting detected! (Gap: {self.score_gap:.4f})")

        lines.append("\n" + "-" * 50)
        lines.append("BEST PARAMS")
        lines.append("-" * 50)
        for k, v in sorted(self.optimizer.best_params_.items()):
            lines.append(f"  {k:<25}: {v}")

        lines.append("\n" + "-" * 50)
        lines.append("DETAILED CLASSIFICATION REPORT")
        lines.append("-" * 50)
        lines.append(f"\n{self.test_report_df.round(4).to_string()}")

        lines.append("\n" + "-" * 50)
        lines.append("CONFUSION MATRIX (Actual vs Predicted)")
        lines.append("-" * 50)
        lines.append(f"\n{self.test_cm_df.to_string()}")

        lines.append("\n" + "-" * 50)
        lines.append("FEATURE IMPORTANCE (Gain)")
        lines.append("-" * 50)
        self.feat_imp_df['Cumul(%)'] = self.feat_imp_df['Importance'].cumsum() * 100
        lines.append(f"\n{self.feat_imp_df.to_string(index=False, formatters={'Importance': '{:.4f}'.format, 'Cumul(%)': '{:.1f}%'.format})}")

        lines.append("\n" + "-" * 50)
        lines.append("FEATURE IMPORTANCE (SHAP mean |value|)")
        lines.append("-" * 50)
        lines.append(f"\n{self.shap_imp_df.to_string(index=False, formatters={'SHAP': '{:.4f}'.format, 'CumulSHAP(%)': '{:.1f}%'.format})}")

        cutoff = int(len(self.shap_imp_df) * 0.7)
        bottom_30 = self.shap_imp_df.iloc[cutoff:]
        lines.append(f"\n[SHAP Bottom 30% — candidates for removal ({len(bottom_30)} features)]")
        lines.append(f"\n{bottom_30[['Rank', 'Feature', 'SHAP']].to_string(index=False, formatters={'SHAP': '{:.4f}'.format})}")

        lines.append("\n" + "-" * 50)
        lines.append("HIGH CORRELATION PAIRS (|corr| > 0.85)")
        lines.append("-" * 50)
        if self.high_corr_pairs.empty:
            lines.append("No high correlation pairs found.")
        else:
            lines.append(f"\n{self.high_corr_pairs.to_string(index=False, formatters={'Corr': '{:.3f}'.format})}")

        lines.append("\n" + "-" * 50)
        lines.append("DRAW THRESHOLD SCAN")
        lines.append("-" * 50)
        lines.append(f"\n{self.draw_threshold_report.to_string(index=False)}")

        if self.calib_draw_threshold_report is not None:
            lines.append("\n" + "-" * 50)
            lines.append("DRAW THRESHOLD SCAN (Calibrated)")
            lines.append("-" * 50)
            calib_report = self.calib_draw_threshold_report.copy()
            calib_report['Selected'] = calib_report[self.DRAW_COL].apply(lambda t: '*' if round(t, 2) == round(self.draw_threshold, 2) else '')
            lines.append(f"\n{calib_report.to_string(index=False)}")

        content = "\n".join(lines)
        for line in lines:
            if line.startswith("WARNING"):
                self.logger.warning(line)
            else:
                self.logger.info(line)

        report_dir = self.config.report_dir / self.config.model_family
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{model_version}.txt"
        report_path.write_text(content, encoding="utf-8")
        self.logger.info(f"Evaluation report saved to: {report_path.resolve()}")
