"""Experimento temporal e artefato de uso; teste nunca seleciona modelo."""

import hashlib
import json
import os
import platform
import tempfile

import joblib
import numpy as np
import sklearn
from sklearn.calibration import calibration_curve
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from radar.config import HISTORY_PATH, MODEL_PATH, ROOT
from radar.data import atomic_json, load_snapshot
from radar.features import FEATURE_VERSION, FEATURES, build_features


def candidates():
    return {
        "frequencias": Pipeline([("imputer", SimpleImputer()), ("model", DummyClassifier(strategy="prior"))]),
        "regressao_logistica": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
                ("model", LogisticRegression(C=1.0, max_iter=2000, random_state=42)),
            ]
        ),
        "arvore_decisao": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", DecisionTreeClassifier(max_depth=5, min_samples_leaf=80, random_state=42)),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=300, max_depth=8, min_samples_leaf=30, n_jobs=2, random_state=42
                    ),
                ),
            ]
        ),
    }


def evaluate(model, x, y):
    probabilities = model.predict_proba(x)
    labels = model.classes_.tolist()
    predictions = model.predict(x)
    truth = np.array([[int(target == label) for label in labels] for target in y])
    calibration = {}
    for i, label in enumerate(labels):
        observed, predicted = calibration_curve(
            truth[:, i], probabilities[:, i], n_bins=8, strategy="quantile"
        )
        calibration[label] = {"predicted": predicted.tolist(), "observed": observed.tolist()}
    return {
        "log_loss": float(log_loss(y, probabilities, labels=labels)),
        "accuracy": float(accuracy_score(y, predictions)),
        "f1_macro": float(f1_score(y, predictions, labels=labels, average="macro", zero_division=0)),
        "brier_multiclass": float(np.mean(np.sum((probabilities - truth) ** 2, axis=1))),
        "class_order": labels,
        "confusion_matrix": confusion_matrix(y, predictions, labels=labels).tolist(),
        "calibration": calibration,
    }


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
    # Comparo também com a referência; escolho o padrão pela validação, nunca pelo teste.
    winner = min(validation, key=lambda name: validation[name]["log_loss"])
    test_by_model = {name: evaluate(model, x[test_mask], y[test_mask]) for name, model in models.items()}
    test = test_by_model[winner]
    baseline_test = evaluate(models["frequencias"], x[test_mask], y[test_mask])
    report = {
        "data": metadata,
        "split": {
            "train": int(train_mask.sum()),
            "validation": int(val_mask.sum()),
            "test": int(test_mask.sum()),
        },
        "validation": validation,
        "test_by_model": test_by_model,
        "selected": winner,
        "test": test,
        "baseline_test": baseline_test,
        "test_beats_baseline": test["log_loss"] < baseline_test["log_loss"],
        "protocol": "Treino 2003–2020, validação 2021–2022, teste 2023–2024. Sem ajuste pelo teste.",
        "seed": 42,
        "python": platform.python_version(),
        "sklearn": sklearn.__version__,
    }
    from api.evaluation_schemas import EvaluationReport
    from radar.evaluation import test_predictions

    # Capturo as previsões dos modelos experimentais antes de qualquer ajuste de produção.
    individual_test = test_predictions(models, x[test_mask], features[test_mask], matches, test_by_model)
    production_models = {name: model for name, model in candidates().items() if name != "frequencias"}
    for model in production_models.values():
        model.fit(x, y)
    default_model = min(production_models, key=lambda name: validation[name]["log_loss"])
    production = production_models[default_model]
    version = hashlib.sha256(
        (metadata["raw_sha256"] + repr(candidates()) + str(FEATURE_VERSION) + sklearn.__version__).encode()
    ).hexdigest()[:12]
    evaluation_report = EvaluationReport.model_validate(
        {
            "experiment_id": "historico-" + version,
            "production_version": version,
            "dataset_sha256": metadata["raw_sha256"],
            "periods": {
                "train": "2003–2020",
                "validation": "2021–2022",
                "test": "2023–2024",
                "production": f"{int(matches.season.min())}–{int(matches.season.max())}",
            },
            "selected_model": winner,
            "models": individual_test,
        }
    )
    bundle = {
        "pipeline": production,
        "features": FEATURES,
        "feature_version": FEATURE_VERSION,
        "model_version": version,
        "sklearn": sklearn.__version__,
        "data": metadata,
        "algorithm": default_model,
        "pipelines": production_models,
        "evaluated_test": test,
    }
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=MODEL_PATH.parent, suffix=".joblib")
    os.close(fd)
    try:
        joblib.dump(bundle, temp, compress=3)
        restored = joblib.load(temp)
        np.testing.assert_allclose(
            production.predict_proba(x.tail(10)), restored["pipeline"].predict_proba(x.tail(10))
        )
        for name, model in production_models.items():
            np.testing.assert_allclose(
                model.predict_proba(x.tail(10)), restored["pipelines"][name].predict_proba(x.tail(10))
            )
        os.replace(temp, MODEL_PATH)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    report["production_version"] = version
    report["production_training"] = (
        "Retreinado em todos os dados; métricas acima pertencem ao experimento separado."
    )
    atomic_json(ROOT / "reports" / "metrics.json", report)
    atomic_json(ROOT / "reports" / "evaluation.json", evaluation_report.model_dump(mode="json"))
    atomic_json(
        ROOT / "models" / "metadata.json",
        {k: v for k, v in bundle.items() if k not in {"pipeline", "pipelines"}},
    )
    lines = [
        "# Avaliação do modelo",
        "",
        report["protocol"],
        "",
        "| Modelo | Log loss validação | Acurácia | F1 macro |",
        "|---|---:|---:|---:|",
    ]
    for name, metrics in validation.items():
        lines.append(
            f"| {name} | {metrics['log_loss']:.4f} | {metrics['accuracy']:.2%} | {metrics['f1_macro']:.4f} |"
        )
    lines += ["", "| Modelo | Log loss teste | Acurácia teste |", "|---|---:|---:|"]
    for name, metrics in test_by_model.items():
        lines.append(f"| {name} | {metrics['log_loss']:.4f} | {metrics['accuracy']:.2%} |")
    lines += [
        "",
        f"Selecionado: **{winner}**.",
        "",
        f"Teste: log loss **{test['log_loss']:.4f}**, "
        f"acurácia **{test['accuracy']:.2%}**, F1 macro **{test['f1_macro']:.4f}**.",
        f"Baseline no teste: log loss **{baseline_test['log_loss']:.4f}**.",
        f"Superou o baseline no teste: **{'sim' if report['test_beats_baseline'] else 'não'}**.",
        "",
        "Acurácia não é certeza por partida. Probabilidades são estimativas, não garantias.",
        "A matriz de confusão, Brier e curvas de calibração estão em metrics.json e calibration.html.",
        "Elo usa início 1500, K=20 e vantagem de mando de 65 pontos; parâmetros fixados antes do teste.",
        "Forma e gols usam janelas de 5/10 jogos. Imputação usa somente o treino de cada ajuste.",
        "Históricos avançam durante o teste apenas após a data de cada jogo (avaliação prequential).",
        "",
        report["production_training"],
        f"Base: {metadata['rows']} jogos; {metadata['first_date']} a {metadata['last_date']}.",
        "A temporada 2020 inclui jogos realizados em 2021. As divisões usam temporada, não ano civil.",
    ]
    (ROOT / "reports" / "METRICAS.md").write_text("\n".join(lines), encoding="utf-8")
    import plotly.graph_objects as go

    figure = go.Figure()
    for label, curve in test["calibration"].items():
        figure.add_scatter(x=curve["predicted"], y=curve["observed"], mode="lines+markers", name=label)
    figure.add_scatter(x=[0, 1], y=[0, 1], mode="lines", name="Calibração perfeita")
    figure.update_layout(
        title="Calibração no teste 2023–2024",
        xaxis_title="Probabilidade prevista",
        yaxis_title="Frequência observada",
    )
    figure.write_html(ROOT / "reports" / "calibration.html", include_plotlyjs=True)
    print(json.dumps({"selected": winner, "test": test, "version": version}, indent=2))


if __name__ == "__main__":
    train()
