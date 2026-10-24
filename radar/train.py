"""Experimento temporal e artefato de uso; teste nunca seleciona modelo."""
import hashlib
import json
import os
import platform
import tempfile

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.calibration import calibration_curve
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from radar.config import HISTORY_PATH, MODEL_PATH, ROOT
from radar.data import atomic_json, load_snapshot
from radar.features import FEATURES, FEATURE_VERSION, build_features


def candidates():
    return {
        "frequencias": Pipeline([("imputer", SimpleImputer()),
                                  ("model", DummyClassifier(strategy="prior"))]),
        "regressao_logistica": Pipeline([("imputer", SimpleImputer(strategy="median")),
                                         ("scale", StandardScaler()),
                                         ("model", LogisticRegression(C=1.0, max_iter=2000, random_state=42))]),
        "gradient_boosting": Pipeline([("imputer", SimpleImputer(strategy="median")),
                                       ("model", HistGradientBoostingClassifier(
                                           max_iter=120, max_leaf_nodes=7, l2_regularization=5,
                                           learning_rate=.05, early_stopping=False, random_state=42))]),
    }


def evaluate(model, x, y):
    probabilities = model.predict_proba(x)
    labels = model.classes_.tolist()
    predictions = model.predict(x)
    truth = np.array([[int(target == label) for label in labels] for target in y])
    calibration = {}
    for i, label in enumerate(labels):
        observed, predicted = calibration_curve(truth[:, i], probabilities[:, i], n_bins=8, strategy="quantile")
        calibration[label] = {"predicted": predicted.tolist(), "observed": observed.tolist()}
    return {"log_loss": float(log_loss(y, probabilities, labels=labels)),
            "accuracy": float(accuracy_score(y, predictions)),
            "f1_macro": float(f1_score(y, predictions, labels=labels, average="macro", zero_division=0)),
            "brier_multiclass": float(np.mean(np.sum((probabilities - truth) ** 2, axis=1))),
            "class_order": labels, "confusion_matrix": confusion_matrix(y, predictions, labels=labels).tolist(),
            "calibration": calibration}


def train():
    metadata, matches = load_snapshot(HISTORY_PATH)
    features, _ = build_features(matches)
    train_mask = features.season.between(2003, 2020)
    val_mask = features.season.between(2021, 2022)
    test_mask = features.season.between(2023, 2024)
    for name, mask in [("treino", train_mask), ("validação", val_mask), ("teste", test_mask)]:
        if features.loc[mask, "result"].nunique() != 3:
            raise ValueError(f"Partição {name} insuficiente para avaliar as três classes.")
    x, y = features[FEATURES], features.result
    models = candidates()
    validation = {}
    for name, model in models.items():
        model.fit(x[train_mask], y[train_mask])
        validation[name] = evaluate(model, x[val_mask], y[val_mask])
    # O baseline também pode vencer: não escondemos desempenho inferior ao acaso informado.
    winner = min(validation, key=lambda name: validation[name]["log_loss"])
    test = evaluate(models[winner], x[test_mask], y[test_mask])
    baseline_test = evaluate(models["frequencias"], x[test_mask], y[test_mask])
    report = {"data": metadata, "split": {"train": int(train_mask.sum()),
              "validation": int(val_mask.sum()), "test": int(test_mask.sum())},
              "validation": validation, "selected": winner, "test": test, "baseline_test": baseline_test,
              "test_beats_baseline": test["log_loss"] < baseline_test["log_loss"],
              "protocol": "Treino 2003–2020, validação 2021–2022, teste 2023–2024. Sem ajuste pelo teste.",
              "seed": 42, "python": platform.python_version(), "sklearn": sklearn.__version__}
    production = candidates()[winner]
    production.fit(x, y)
    version = hashlib.sha256((metadata["raw_sha256"] + winner + str(FEATURE_VERSION)
                              + sklearn.__version__).encode()).hexdigest()[:12]
    bundle = {"pipeline": production, "features": FEATURES, "feature_version": FEATURE_VERSION,
              "model_version": version, "sklearn": sklearn.__version__, "data": metadata,
              "algorithm": winner, "evaluated_test": test}
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=MODEL_PATH.parent, suffix=".joblib")
    os.close(fd)
    try:
        joblib.dump(bundle, temp, compress=3)
        restored = joblib.load(temp)
        np.testing.assert_allclose(production.predict_proba(x.tail(10)),
                                   restored["pipeline"].predict_proba(x.tail(10)))
        os.replace(temp, MODEL_PATH)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    report["production_version"] = version
    report["production_training"] = "Retreinado em todos os dados; métricas acima pertencem ao experimento separado."
    atomic_json(ROOT / "reports" / "metrics.json", report)
    atomic_json(ROOT / "models" / "metadata.json", {k: v for k, v in bundle.items() if k != "pipeline"})
    lines = ["# Avaliação do modelo", "", report["protocol"], "",
             "| Modelo | Log loss validação | Acurácia | F1 macro |", "|---|---:|---:|---:|"]
    for name, metrics in validation.items():
        lines.append(f"| {name} | {metrics['log_loss']:.4f} | {metrics['accuracy']:.2%} | {metrics['f1_macro']:.4f} |")
    lines += ["", f"Selecionado: **{winner}**.", "", f"Teste: log loss **{test['log_loss']:.4f}**, "
              f"acurácia **{test['accuracy']:.2%}**, F1 macro **{test['f1_macro']:.4f}**.",
              f"Baseline no teste: log loss **{baseline_test['log_loss']:.4f}**.",
              f"Superou o baseline no teste: **{'sim' if report['test_beats_baseline'] else 'não'}**.", "",
              "Acurácia não é certeza por partida. Probabilidades são estimativas, não garantias.",
              "A matriz de confusão, Brier e curvas de calibração estão em metrics.json e calibration.html.",
              "Elo usa início 1500, K=20 e vantagem de mando de 65 pontos; parâmetros fixados antes do teste.",
              "Forma e gols usam janelas de 5/10 jogos. Imputação usa somente o treino de cada ajuste.",
              "Históricos avançam durante o teste apenas após a data de cada jogo (avaliação prequential).", "",
              report["production_training"],
              f"Base: {metadata['rows']} jogos; {metadata['first_date']} a {metadata['last_date']}.",
              "A temporada 2020 inclui jogos realizados em 2021. As divisões usam temporada, não ano civil."]
    (ROOT / "reports" / "METRICAS.md").write_text("\n".join(lines), encoding="utf-8")
    import plotly.graph_objects as go
    figure = go.Figure()
    for label, curve in test["calibration"].items():
        figure.add_scatter(x=curve["predicted"], y=curve["observed"], mode="lines+markers", name=label)
    figure.add_scatter(x=[0, 1], y=[0, 1], mode="lines", name="Calibração perfeita")
    figure.update_layout(title="Calibração no teste 2023–2024", xaxis_title="Probabilidade prevista",
                         yaxis_title="Frequência observada")
    figure.write_html(ROOT / "reports" / "calibration.html", include_plotlyjs=True)
    print(json.dumps({"selected": winner, "test": test, "version": version}, indent=2))


if __name__ == "__main__":
    train()
