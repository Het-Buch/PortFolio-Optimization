"""Offline model comparison and Optuna tuning. Never runs in the app."""

import argparse
import json
import time
import warnings
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from sklearn.dummy import DummyRegressor
from sklearn.ensemble import (AdaBoostRegressor, BaggingRegressor,
                              ExtraTreesRegressor, GradientBoostingRegressor,
                              HistGradientBoostingRegressor, RandomForestRegressor)
from sklearn.kernel_ridge import KernelRidge
from sklearn.linear_model import (ARDRegression, BayesianRidge, ElasticNet,
                                  HuberRegressor, Lars, Lasso, LassoLars,
                                  LinearRegression, OrthogonalMatchingPursuit,
                                  PassiveAggressiveRegressor, RANSACRegressor, Ridge,
                                  SGDRegressor, TheilSenRegressor)
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.neighbors import KNeighborsRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR, LinearSVR
from sklearn.tree import DecisionTreeRegressor, ExtraTreeRegressor

SEED = 42
N_SPLITS = 5
ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
MODELS = RESULTS / "models"
PREDS = RESULTS / "predictions"
STUDIES = RESULTS / "optuna"
PARAMS = RESULTS / "best_params"


MLRUNS = ROOT / "mlruns"


def _dirs(target):
    """Every artifact directory for one target run."""
    for d in (RESULTS, MODELS / target, PREDS / target, STUDIES, PARAMS):
        d.mkdir(parents=True, exist_ok=True)


MLFLOW_DB = ROOT / "mlflow.db"


def _mlflow():
    """Local SQLite-backed MLflow. No server; MLflow 3.x rejects the file store."""
    try:
        import mlflow
    except ImportError:
        return None
    MLRUNS.mkdir(exist_ok=True)
    try:
        mlflow.set_tracking_uri(f"sqlite:///{MLFLOW_DB.as_posix()}")
        mlflow.search_experiments(max_results=1)
    except Exception as e:
        print(f"  MLflow disabled ({type(e).__name__}: {e}); continuing without it")
        return None
    return mlflow


class _NoRun:
    """Stand-in so the job still runs with MLflow absent."""
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _start(mf, name, nested=False):
    return mf.start_run(run_name=name, nested=nested) if mf else _NoRun()


def _log_params(mf, params):
    if mf:
        mf.log_params({k: str(v)[:250] for k, v in params.items()})


def _log_metrics(mf, metrics):
    if mf:
        mf.log_metrics({k: float(v) for k, v in metrics.items()
                        if v is not None and np.isfinite(v)})


def _boosters():
    """XGBoost/LightGBM/CatBoost if installed. Absent ones are reported, not fatal."""
    out = {}
    try:
        from xgboost import XGBRegressor
        out["XGBoost"] = XGBRegressor(random_state=SEED, n_jobs=-1, verbosity=0)
    except ImportError:
        pass
    try:
        from lightgbm import LGBMRegressor
        out["LightGBM"] = LGBMRegressor(random_state=SEED, n_jobs=-1, verbose=-1)
    except ImportError:
        pass
    try:
        from catboost import CatBoostRegressor
        out["CatBoost"] = CatBoostRegressor(random_state=SEED, verbose=0, allow_writing_files=False)
    except ImportError:
        pass
    return out


def _models():
    """The 25 regressors named in the report's Table 3.3, plus a mean baseline."""
    def scaled(est):
        return make_pipeline(StandardScaler(), est)

    return {
        "LinearRegression": scaled(LinearRegression()),
        "Ridge": scaled(Ridge(alpha=1.0, random_state=SEED)),
        "Lasso": scaled(Lasso(alpha=0.001, random_state=SEED)),
        "ElasticNet": scaled(ElasticNet(alpha=0.001, random_state=SEED)),
        "BayesianRidge": scaled(BayesianRidge()),
        "ARDRegression": scaled(ARDRegression()),
        "HuberRegressor": scaled(HuberRegressor(max_iter=500)),
        "LassoLars": scaled(LassoLars(alpha=0.001, random_state=SEED)),
        "Lars": scaled(Lars(random_state=SEED)),
        "TheilSen": scaled(TheilSenRegressor(random_state=SEED, max_subpopulation=2000,
                                             n_jobs=-1)),
        "RANSAC": scaled(RANSACRegressor(random_state=SEED)),
        "OrthogonalMatchingPursuit": scaled(OrthogonalMatchingPursuit()),
        "PassiveAggressive": scaled(PassiveAggressiveRegressor(random_state=SEED)),
        "SGDRegressor": scaled(SGDRegressor(random_state=SEED)),
        "KernelRidge": scaled(KernelRidge(alpha=1.0)),
        "SVR_rbf": scaled(SVR(kernel="rbf")),
        "LinearSVR": scaled(LinearSVR(random_state=SEED, max_iter=5000)),
        "KNeighbors": scaled(KNeighborsRegressor(n_neighbors=5)),
        "MLPRegressor": scaled(MLPRegressor(hidden_layer_sizes=(64, 32),
                                            max_iter=300, random_state=SEED)),
        "DecisionTree": DecisionTreeRegressor(random_state=SEED),
        "ExtraTree": ExtraTreeRegressor(random_state=SEED),
        "RandomForest": RandomForestRegressor(n_estimators=100, random_state=SEED, n_jobs=-1),
        "ExtraTrees": ExtraTreesRegressor(n_estimators=100, random_state=SEED, n_jobs=-1),
        "GradientBoosting": GradientBoostingRegressor(random_state=SEED),
        "HistGradientBoosting": HistGradientBoostingRegressor(random_state=SEED),
        "AdaBoost": AdaBoostRegressor(random_state=SEED),
        "Bagging": BaggingRegressor(random_state=SEED, n_jobs=-1),
        **_boosters(),
        "DummyMean": DummyRegressor(strategy="mean"),
    }


# Table 3.3 of the report -> the key used in _models().
REPORT_TABLE_33 = {
    "Linear Regression (LR)": "LinearRegression",
    "Kernel Ridge Regression (KR)": "KernelRidge",
    "Huber Regression (Huber)": "HuberRegressor",
    "Support Vector Regression (SVR)": "SVR_rbf",
    "Ridge Regression (Ridge)": "Ridge",
    "K-Nearest Neighbors (KNN)": "KNeighbors",
    "Elastic Net Regression (EN)": "ElasticNet",
    "Decision Trees (DT)": "DecisionTree",
    "Least Angle Regression (LAR)": "Lars",
    "Random Forest (RF)": "RandomForest",
    "Lasso Least Angle Regression (LLAR)": "LassoLars",
    "Extra Trees Regression (ET)": "ExtraTrees",
    "Orthogonal Matching Pursuit (OMP)": "OrthogonalMatchingPursuit",
    "AdaBoost Regression (Ada)": "AdaBoost",
    "Bayesian Ridge Regression (BR)": "BayesianRidge",
    "Gradient Boosting Regression (GBR)": "GradientBoosting",
    "Automatic Relevance Determination (ARD)": "ARDRegression",
    "Multi-Layer Perceptron (MLP)": "MLPRegressor",
    "Passive Aggressive Regression (PAR)": "PassiveAggressive",
    "Extreme Gradient Boosting (XGBoost)": "XGBoost",
    "Lasso (L1)": "Lasso",
    "Light Gradient Boosting Machine (LightGBM)": "LightGBM",
    "Theil-Sen Estimator (TR)": "TheilSen",
    "Categorical Boosting (CatBoost)": "CatBoost",
    "Random Sample Consensus (RANSAC)": "RANSAC",
}


def coverage():
    """Which of the report's 25 models this run can actually train."""
    have = set(_models())
    return {rep: (key in have) for rep, key in REPORT_TABLE_33.items()}


def build_dataset(tickers, target="price"):
    """Fetch fresh data and engineer features. Pooled across tickers for returns."""
    from ml.train import get_stock_data

    frames = []
    for t in tickers:
        try:
            data = get_stock_data(t)
        except Exception as e:
            print(f"  {t}: fetch failed ({e})")
            continue
        if data is None or len(data) < 300:
            print(f"  {t}: insufficient data")
            continue

        X = data.drop("Close", axis=1).copy()
        if target == "price":
            y = data["Close"]
        else:
            y = data["Close"].pct_change().shift(-1)

        mask = y.notna()
        X, y = X[mask], y[mask]
        X["__ticker"] = t
        frames.append((X, y))
        print(f"  {t}: {len(X)} rows")

    if not frames:
        return None, None

    # Price levels are not comparable across tickers, so never pool them.
    if target == "price":
        X, y = frames[0]
        return X.drop(columns="__ticker"), y

    # Pooled tickers share trading dates, so the index has duplicates. Align
    # positionally and sort by position -- a .loc lookup here raises.
    X = pd.concat([f[0] for f in frames])
    y = pd.concat([f[1] for f in frames])
    order = np.argsort(X.index.values, kind="stable")
    X, y = X.iloc[order], y.iloc[order]
    return X.drop(columns="__ticker"), y


def _naive_baseline(X, y, target):
    """The number every model has to beat. Persistence for price, zero for return."""
    tscv = TimeSeriesSplit(n_splits=N_SPLITS)
    r2s, rmses, dirs = [], [], []
    for _, te in tscv.split(X):
        yte = y.iloc[te]
        pred = X.iloc[te]["Close_lag_1"].values if target == "price" else np.zeros(len(yte))
        r2s.append(r2_score(yte, pred))
        rmses.append(float(np.sqrt(mean_squared_error(yte, pred))))
        dirs.append(float((np.sign(pred) == np.sign(yte)).mean() * 100))
    return {"model": "NAIVE_BASELINE", "r2": np.mean(r2s), "rmse": np.mean(rmses),
            "mae": np.nan, "directional_pct": np.mean(dirs),
            "r2_std": np.std(r2s), "fit_seconds": 0.0}


def evaluate(X, y, target, mf=None):
    """Walk-forward evaluation of every model. Never a random split."""
    tscv = TimeSeriesSplit(n_splits=N_SPLITS)
    base = _naive_baseline(X, y, target)
    rows = [base]

    with _start(mf, f"{target}-NAIVE_BASELINE", nested=True):
        _log_params(mf, {"model": "NAIVE_BASELINE", "target": target,
                         "strategy": "persistence" if target == "price" else "zero"})
        _log_metrics(mf, {k: base[k] for k in
                          ("r2", "rmse", "directional_pct", "r2_std")})

    for name, model in _models().items():
        from sklearn.base import clone
        r2s, rmses, maes, dirs, oof = [], [], [], [], []
        t0 = time.time()
        try:
            for fold, (tr, te) in enumerate(tscv.split(X)):
                Xtr, Xte = X.iloc[tr], X.iloc[te]
                ytr, yte = y.iloc[tr], y.iloc[te]
                m = clone(model).fit(Xtr, ytr)
                p = m.predict(Xte)
                r2s.append(r2_score(yte, p))
                rmses.append(float(np.sqrt(mean_squared_error(yte, p))))
                maes.append(mean_absolute_error(yte, p))
                dirs.append(float((np.sign(p) == np.sign(yte)).mean() * 100))
                oof.append(pd.DataFrame({"fold": fold, "date": Xte.index,
                                         "actual": yte.values, "predicted": p}))
        except Exception as e:
            print(f"  {name}: failed ({type(e).__name__})")
            continue

        # Refit on the full series so the saved artifact is the deployable one.
        final = clone(model).fit(X, y)
        model_path = MODELS / target / f"{name}.joblib"
        pred_path = PREDS / target / f"{name}.csv"
        joblib.dump(final, model_path, compress=3)
        pd.concat(oof).to_csv(pred_path, index=False)

        row = {"model": name, "r2": np.mean(r2s), "rmse": np.mean(rmses),
               "mae": np.mean(maes), "directional_pct": np.mean(dirs),
               "r2_std": np.std(r2s), "fit_seconds": round(time.time() - t0, 2),
               "model_file": f"models/{target}/{name}.joblib",
               "predictions_file": f"predictions/{target}/{name}.csv"}
        rows.append(row)

        with _start(mf, f"{target}-{name}", nested=True):
            _log_params(mf, {"model": name, "target": target, "seed": SEED,
                             "cv": f"TimeSeriesSplit({N_SPLITS})",
                             "rows": len(X), "features": X.shape[1],
                             **{k: v for k, v in
                                getattr(final, "get_params", dict)().items()
                                if isinstance(v, (int, float, str, bool, type(None)))}})
            _log_metrics(mf, {k: row[k] for k in
                              ("r2", "rmse", "mae", "directional_pct",
                               "r2_std", "fit_seconds")})
            # Per-fold metrics give MLflow a real curve instead of one point.
            if mf:
                for i, (r, e) in enumerate(zip(r2s, rmses)):
                    mf.log_metric("fold_r2", float(r), step=i)
                    mf.log_metric("fold_rmse", float(e), step=i)
                mf.log_artifact(str(model_path), "model")
                mf.log_artifact(str(pred_path), "predictions")
        print(f"  {name:26s} R2={np.mean(r2s):+.4f}  RMSE={np.mean(rmses):.4f}  "
              f"dir={np.mean(dirs):.1f}%  {time.time() - t0:.1f}s")

    return pd.DataFrame(rows).sort_values("rmse").reset_index(drop=True)


# Search spaces for the estimators worth tuning. Keyed to the names in _models().
def _suggest(trial, name):
    if name == "Ridge":
        return make_pipeline(StandardScaler(),
                             Ridge(alpha=trial.suggest_float("alpha", 1e-4, 1e4, log=True)))
    if name == "Lasso":
        return make_pipeline(StandardScaler(),
                             Lasso(alpha=trial.suggest_float("alpha", 1e-6, 1e1, log=True)))
    if name == "ElasticNet":
        return make_pipeline(StandardScaler(), ElasticNet(
            alpha=trial.suggest_float("alpha", 1e-6, 1e1, log=True),
            l1_ratio=trial.suggest_float("l1_ratio", 0.0, 1.0)))
    if name == "KernelRidge":
        return make_pipeline(StandardScaler(), KernelRidge(
            alpha=trial.suggest_float("alpha", 1e-4, 1e2, log=True)))
    if name == "KNeighbors":
        return make_pipeline(StandardScaler(), KNeighborsRegressor(
            n_neighbors=trial.suggest_int("n_neighbors", 2, 50),
            weights=trial.suggest_categorical("weights", ["uniform", "distance"])))
    if name == "RandomForest":
        return RandomForestRegressor(
            n_estimators=trial.suggest_int("n_estimators", 50, 400),
            max_depth=trial.suggest_int("max_depth", 2, 20),
            min_samples_leaf=trial.suggest_int("min_samples_leaf", 1, 20),
            random_state=SEED, n_jobs=-1)
    if name == "ExtraTrees":
        return ExtraTreesRegressor(
            n_estimators=trial.suggest_int("n_estimators", 50, 400),
            max_depth=trial.suggest_int("max_depth", 2, 20),
            min_samples_leaf=trial.suggest_int("min_samples_leaf", 1, 20),
            random_state=SEED, n_jobs=-1)
    if name in ("GradientBoosting", "HistGradientBoosting"):
        lr = trial.suggest_float("learning_rate", 1e-3, 0.3, log=True)
        if name == "HistGradientBoosting":
            return HistGradientBoostingRegressor(
                learning_rate=lr,
                max_depth=trial.suggest_int("max_depth", 2, 15),
                max_iter=trial.suggest_int("max_iter", 50, 400), random_state=SEED)
        return GradientBoostingRegressor(
            learning_rate=lr,
            n_estimators=trial.suggest_int("n_estimators", 50, 300),
            max_depth=trial.suggest_int("max_depth", 2, 8), random_state=SEED)
    if name == "SVR_rbf":
        return make_pipeline(StandardScaler(), SVR(
            C=trial.suggest_float("C", 1e-2, 1e3, log=True),
            gamma=trial.suggest_categorical("gamma", ["scale", "auto"])))
    if name == "XGBoost":
        from xgboost import XGBRegressor
        return XGBRegressor(
            n_estimators=trial.suggest_int("n_estimators", 50, 600),
            max_depth=trial.suggest_int("max_depth", 2, 12),
            learning_rate=trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
            subsample=trial.suggest_float("subsample", 0.5, 1.0),
            colsample_bytree=trial.suggest_float("colsample_bytree", 0.5, 1.0),
            reg_lambda=trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
            random_state=SEED, n_jobs=-1, verbosity=0)
    if name == "LightGBM":
        from lightgbm import LGBMRegressor
        return LGBMRegressor(
            n_estimators=trial.suggest_int("n_estimators", 50, 600),
            num_leaves=trial.suggest_int("num_leaves", 8, 128),
            learning_rate=trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
            subsample=trial.suggest_float("subsample", 0.5, 1.0),
            colsample_bytree=trial.suggest_float("colsample_bytree", 0.5, 1.0),
            random_state=SEED, n_jobs=-1, verbose=-1)
    if name == "CatBoost":
        from catboost import CatBoostRegressor
        return CatBoostRegressor(
            iterations=trial.suggest_int("iterations", 50, 600),
            depth=trial.suggest_int("depth", 2, 10),
            learning_rate=trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
            l2_leaf_reg=trial.suggest_float("l2_leaf_reg", 1.0, 10.0),
            random_state=SEED, verbose=0, allow_writing_files=False)
    return None


TUNABLE = {"Ridge", "Lasso", "ElasticNet", "KernelRidge", "KNeighbors", "RandomForest",
           "ExtraTrees", "GradientBoosting", "HistGradientBoosting", "SVR_rbf",
           "XGBoost", "LightGBM", "CatBoost"}


def tune(X, y, names, n_trials, target, mf=None):
    """Optuna over the top models. Studies persist to SQLite so a run can resume."""
    import optuna
    from sklearn.base import clone
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    storage = f"sqlite:///{(STUDIES / f'{target}.db').as_posix()}"
    tscv = TimeSeriesSplit(n_splits=N_SPLITS)
    rows = []
    for name in names:
        if name not in TUNABLE:
            print(f"  {name}: no search space, skipped")
            continue

        def objective(trial):
            model = _suggest(trial, name)
            if model is None:
                raise optuna.TrialPruned()
            errs = []
            for tr, te in tscv.split(X):
                m = clone(model).fit(X.iloc[tr], y.iloc[tr])
                errs.append(np.sqrt(mean_squared_error(y.iloc[te], m.predict(X.iloc[te]))))
            return float(np.mean(errs))

        t0 = time.time()
        study = optuna.create_study(
            direction="minimize", study_name=f"{target}_{name}", storage=storage,
            load_if_exists=True, sampler=optuna.samplers.TPESampler(seed=SEED))
        done = len([t for t in study.trials
                    if t.state == optuna.trial.TrialState.COMPLETE])
        if done < n_trials:
            study.optimize(objective, n_trials=n_trials - done, show_progress_bar=False)

        # Refit on the full series with the winning params -- this is the
        # artifact anything downstream should load.
        best = _suggest(study.best_trial, name)
        best.fit(X, y)
        model_path = MODELS / target / f"{name}_tuned.joblib"
        trials_path = STUDIES / f"{target}_{name}_trials.csv"
        params_path = PARAMS / f"{target}_{name}.json"
        joblib.dump(best, model_path, compress=3)
        study.trials_dataframe().to_csv(trials_path, index=False)

        # Everything needed to rebuild this exact model without re-tuning.
        params_path.write_text(json.dumps({
            "model": name, "target": target, "seed": SEED,
            "cv": f"TimeSeriesSplit({N_SPLITS})",
            "best_params": study.best_params,
            "best_rmse": study.best_value,
            "trials": len(study.trials),
            "sampler": "TPESampler",
            "study_name": f"{target}_{name}",
            "storage": f"optuna/{target}.db",
            "rows": int(len(X)), "features": int(X.shape[1]),
            "generated": datetime.now().isoformat(timespec="seconds"),
        }, indent=2), encoding="utf-8")

        rows.append({"model": name, "tuned_rmse": study.best_value,
                     "best_params": json.dumps(study.best_params),
                     "trials": len(study.trials),
                     "tune_seconds": round(time.time() - t0, 1),
                     "model_file": f"models/{target}/{name}_tuned.joblib",
                     "params_file": f"best_params/{target}_{name}.json",
                     "trials_file": f"optuna/{target}_{name}_trials.csv"})

        with _start(mf, f"{target}-{name}-tuned", nested=True):
            _log_params(mf, {"model": name, "target": target, "tuned": True,
                             "seed": SEED, "sampler": "TPESampler",
                             "trials": len(study.trials), **study.best_params})
            _log_metrics(mf, {"tuned_rmse": study.best_value,
                              "tune_seconds": round(time.time() - t0, 1)})
            if mf:
                for t_ in study.trials:
                    if t_.value is not None and np.isfinite(t_.value):
                        mf.log_metric("trial_rmse", float(t_.value), step=t_.number)
                mf.log_artifact(str(model_path), "model")
                mf.log_artifact(str(params_path), "best_params")
                mf.log_artifact(str(trials_path), "optuna_trials")
        print(f"  {name:26s} tuned RMSE={study.best_value:.5f}  "
              f"({time.time() - t0:.0f}s)  {study.best_params}")

    return pd.DataFrame(rows).sort_values("tuned_rmse").reset_index(drop=True)


def _verdict(best_rmse, base_rmse, tol=0.01):
    """A sub-1% RMSE difference is a tie, not a win."""
    rel = (base_rmse - best_rmse) / base_rmse
    if rel > tol:
        return "beats"
    if rel < -tol:
        return "loses to"
    return "ties"


def _plots(before, after, target):
    """Two figures: ranking against the baseline, and the tuning delta."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    d = before[before.model != "NAIVE_BASELINE"].sort_values("rmse")
    baseline = before[before.model == "NAIVE_BASELINE"]["rmse"].iloc[0]

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(d.model, d.rmse, color="#4C72B0")
    ax.axvline(baseline, color="crimson", ls="--", lw=2,
               label=f"naive baseline ({baseline:.4f})")
    ax.set_xlabel("RMSE (lower is better)")
    ax.set_title(f"Model comparison — {target} target, {N_SPLITS}-fold walk-forward")
    ax.invert_yaxis()
    ax.legend()
    fig.tight_layout()
    fig.savefig(RESULTS / f"model_comparison_{target}.png", dpi=150)
    plt.close(fig)

    if after is not None and not after.empty:
        merged = after.merge(before[["model", "rmse"]], on="model", how="left")
        x = np.arange(len(merged))
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(x - 0.2, merged.rmse, 0.4, label="before tuning", color="#999999")
        ax.bar(x + 0.2, merged.tuned_rmse, 0.4, label="after tuning", color="#55A868")
        ax.axhline(baseline, color="crimson", ls="--", lw=2, label="naive baseline")
        ax.set_xticks(x)
        ax.set_xticklabels(merged.model, rotation=30, ha="right")
        ax.set_ylabel("RMSE")
        ax.set_title(f"Before vs after Optuna tuning — {target} target")
        ax.legend()
        fig.tight_layout()
        fig.savefig(RESULTS / f"tuning_{target}.png", dpi=150)
        plt.close(fig)


def _methodology(tickers, summary):
    """Written next to the numbers so the run can be defended without this file."""
    import sklearn
    lines = [
        "# Methodology",
        "",
        f"Generated {datetime.now().isoformat(timespec='seconds')} by `jobs/model_comparison.py`.",
        "",
        "## Reproducibility",
        f"- Seed: `{SEED}` (numpy, sklearn estimators, Optuna TPE sampler)",
        f"- Cross-validation: `TimeSeriesSplit(n_splits={N_SPLITS})` — walk-forward, never shuffled",
        f"- scikit-learn {sklearn.__version__}, numpy {np.__version__}, pandas {pd.__version__}",
        f"- Tickers: {', '.join(tickers)}",
        "- Data fetched live from yfinance at run time, 15-year window",
        "",
        "## Targets",
        "- `price`: next close as a level. Single ticker only — price levels are not",
        "  comparable across tickers, so they are never pooled.",
        "- `return`: next-day percentage change, pooled across tickers.",
        "",
        "## Baseline",
        "Every model is scored against a naive baseline, and a sub-1% RMSE difference",
        "is reported as a tie rather than a win.",
        "- `price` target: persistence, i.e. tomorrow equals today (`Close_lag_1`)",
        "- `return` target: a constant zero return",
        "",
        "## Features",
        "Lagged SMA/EMA/RSI/MACD/Bollinger/volatility/return, five lagged closes, and",
        "cyclical day/month encodings. All indicators are shifted by one day, so no",
        "feature uses information from the bar it predicts.",
        "",
        "## Tuning",
        "Optuna TPE over the best-ranked tunable models, minimising walk-forward RMSE",
        "on the same folds used for the untuned comparison. Studies persist to SQLite",
        "under `results/optuna/`, so an interrupted run resumes instead of restarting.",
        "",
        "## Results",
    ]
    for t, s in summary.items():
        lines += [
            f"### {t}",
            f"- {s['models_evaluated']} models on {s['rows']} rows x {s['features']} features",
            f"- Baseline RMSE {s['baseline_rmse']:.6f} (R2 {s['baseline_r2']:.4f})",
            f"- Best: **{s['best_model']}** RMSE {s['best_rmse']:.6f} "
            f"(R2 {s['best_r2']:.4f}, directional {s['best_directional_pct']:.2f}%)",
            f"- Verdict: best model **{s['vs_baseline']}** the naive baseline "
            f"({s['improvement_pct']:+.2f}% RMSE)",
            "",
        ]
    lines += [
        "## Artifacts",
        "- `model_comparison_<target>.csv` — every model, RMSE/MAE/R2/directional/fold-std",
        "- `model_comparison_<target>_tuned.csv` — post-Optuna, with best params",
        "- `models/<target>/*.joblib` — each model refit on the full series",
        "- `predictions/<target>/*.csv` — per-fold out-of-sample predictions",
        "- `optuna/<target>.db` — resumable studies; `*_trials.csv` — every trial",
        "- `datasets/<target>.csv` — the exact feature matrix used",
        "- `summary.json` — machine-readable run summary",
        "",
    ]
    (RESULTS / "METHODOLOGY.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", type=int, default=8, help="how many to sample")
    ap.add_argument("--trials", type=int, default=40, help="Optuna trials per model")
    ap.add_argument("--top", type=int, default=5, help="how many models to tune")
    ap.add_argument("--target", choices=["price", "return", "both"], default="both")
    args = ap.parse_args()

    RESULTS.mkdir(exist_ok=True)
    cov = coverage()
    missing = [k for k, v in cov.items() if not v]
    print(f"Report Table 3.3 coverage: {sum(cov.values())}/{len(cov)} models available")
    if missing:
        print("  missing (pip install -r requirements.txt): " + ", ".join(missing))
    pd.DataFrame([{"report_model": k, "available": v} for k, v in cov.items()]).to_csv(
        RESULTS / "table_3_3_coverage.csv", index=False)

    csv = Path(__file__).resolve().parents[1] / "ml" / "top 80 compines with ticker.csv"
    universe = [f"{t}.NS" for t in pd.read_csv(csv)["Ticker"].dropna().unique()]
    tickers = universe[:args.tickers]

    targets = ["price", "return"] if args.target == "both" else [args.target]
    summary = {}

    for target in targets:
        print(f"\n{'=' * 70}\nTARGET: {target}\n{'=' * 70}")
        _dirs(target)
        print("Fetching fresh data from yfinance...")
        X, y = build_dataset(tickers, target=target)
        if X is None:
            print("no data; skipping")
            continue
        print(f"dataset: {X.shape[0]} rows x {X.shape[1]} features\n")
        (RESULTS / "datasets").mkdir(parents=True, exist_ok=True)
        X.assign(__target=y).to_csv(RESULTS / "datasets" / f"{target}.csv")

        mf = _mlflow()
        if mf:
            name = f"portfolio-{target}"
            # Create with an explicit artifact dir the first time; reuse after.
            if mf.get_experiment_by_name(name) is None:
                (MLRUNS / target).mkdir(parents=True, exist_ok=True)
                mf.create_experiment(name,
                                     artifact_location=(MLRUNS / target).as_uri())
            mf.set_experiment(name)
        with _start(mf, f"sweep-{target}"):
            _log_params(mf, {"target": target, "seed": SEED,
                             "cv": f"TimeSeriesSplit({N_SPLITS})",
                             "tickers": ",".join(tickers),
                             "rows": len(X), "features": X.shape[1],
                             "optuna_trials": args.trials, "top_tuned": args.top})

            before = evaluate(X, y, target, mf)
            before.to_csv(RESULTS / f"model_comparison_{target}.csv", index=False)

            ranked = [m for m in before.model
                      if m not in ("NAIVE_BASELINE", "DummyMean")]
            top = [m for m in ranked if m in TUNABLE][:args.top]
            print(f"\nTuning top {len(top)}: {', '.join(top)}")
            after = tune(X, y, top, args.trials, target, mf)
            after.to_csv(RESULTS / f"model_comparison_{target}_tuned.csv", index=False)

            _plots(before, after, target)

            if mf:
                b = before[before.model == "NAIVE_BASELINE"].iloc[0]
                w = before[before.model != "NAIVE_BASELINE"].iloc[0]
                _log_metrics(mf, {"baseline_rmse": b.rmse, "baseline_r2": b.r2,
                                  "best_rmse": w.rmse, "best_r2": w.r2,
                                  "models_evaluated": len(before) - 1})
                mf.set_tag("best_model", str(w.model))
                mf.set_tag("vs_baseline", _verdict(w.rmse, b.rmse))
                for f in (RESULTS / f"model_comparison_{target}.csv",
                          RESULTS / f"model_comparison_{target}_tuned.csv",
                          RESULTS / f"model_comparison_{target}.png",
                          RESULTS / f"tuning_{target}.png",
                          RESULTS / "datasets" / f"{target}.csv"):
                    if f.exists():
                        mf.log_artifact(str(f), "results")

        base = before[before.model == "NAIVE_BASELINE"].iloc[0]
        best = before[before.model != "NAIVE_BASELINE"].iloc[0]
        summary[target] = {
            "rows": int(X.shape[0]), "features": int(X.shape[1]),
            "models_evaluated": int(len(before) - 1),
            "baseline_rmse": float(base.rmse), "baseline_r2": float(base.r2),
            "best_model": str(best.model), "best_rmse": float(best.rmse),
            "best_r2": float(best.r2), "best_directional_pct": float(best.directional_pct),
            "vs_baseline": _verdict(best.rmse, base.rmse),
            "improvement_pct": float((base.rmse - best.rmse) / base.rmse * 100),
            "best_tuned": (str(after.iloc[0].model) if not after.empty else None),
            "best_tuned_rmse": (float(after.iloc[0].tuned_rmse) if not after.empty else None),
        }

    (RESULTS / "summary.json").write_text(json.dumps(
        {"generated": datetime.now().isoformat(timespec="seconds"),
         "seed": SEED, "cv": f"TimeSeriesSplit({N_SPLITS})",
         "tickers": tickers, "results": summary}, indent=2))
    _methodology(tickers, summary)

    print(f"\n{'=' * 70}\nWritten to {RESULTS}")
    for t, s in summary.items():
        print(f"  {t:7s}: best={s['best_model']} ({s['best_rmse']:.5f}) "
              f"{s['vs_baseline'].upper()} naive baseline ({s['baseline_rmse']:.5f}), "
              f"{s['improvement_pct']:+.2f}%")


if __name__ == "__main__":
    main()
