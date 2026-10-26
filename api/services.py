import joblib
import pandas as pd
import sklearn

from radar.config import HISTORY_PATH, MODEL_PATH
from radar.data import load_snapshot
from radar.features import FEATURE_VERSION, FEATURES, build_features, summarize


class PredictionService:
    def __init__(self, model_path=MODEL_PATH, history_path=HISTORY_PATH):
        try:
            self.bundle = joblib.load(model_path)  # somente artefato local confiável
            self.metadata, matches = load_snapshot(history_path)
        except (OSError, KeyError, ValueError) as exc:
            raise RuntimeError(
                "Não foi possível carregar os artefatos. Execute radar.data e radar.train."
            ) from exc
        if (
            self.bundle["feature_version"] != FEATURE_VERSION
            or self.bundle["features"] != FEATURES
            or self.bundle["sklearn"] != sklearn.__version__
        ):
            raise RuntimeError("Modelo incompatível. Reinstale requirements.txt e retreine.")
        if self.metadata["last_date"] < self.bundle["data"]["last_date"]:
            raise RuntimeError("Histórico anterior ao treinamento do modelo. Atualize os dados.")
        _, self.history = build_features(matches)
        self.season = int(matches.season.max())
        last = matches[matches.season.eq(self.season)]
        self.clubs = sorted(set(last.home) | set(last.away))
        self.pipeline = self.bundle["pipeline"]
        self.default_model = self.bundle.get("algorithm", "frequencias")
        self.pipelines = self.bundle.get("pipelines", {self.default_model: self.pipeline})
        if any(set(model.classes_) != {"H", "D", "A"} for model in self.pipelines.values()):
            raise RuntimeError("Modelo não contém as três classes esperadas.")

    def model_name(self, model_id=None):
        algorithm = model_id or self.default_model
        return {
            "regressao_logistica": "Regressão Logística",
            "frequencias": "Frequências históricas",
            "arvore_decisao": "Árvore de Decisão",
            "random_forest": "Random Forest",
        }.get(algorithm, algorithm)

    def select_model(self, model_id):
        selected = model_id or self.default_model
        if selected not in self.pipelines:
            raise ValueError("Modelo desconhecido ou indisponível.")
        return selected, self.pipelines[selected]

    def simulate(self, year, seed, model_id=None):
        from radar.simulation import schedule, simulate

        selected, pipeline = self.select_model(model_id)
        fixtures = [pair for round_ in schedule(self.clubs) for pair in round_]
        vectors = pd.DataFrame([self.history.vector(*pair) for pair in fixtures], columns=FEATURES)
        estimates = pipeline.predict_proba(vectors)
        order = [list(pipeline.classes_).index(label) for label in ("H", "D", "A")]
        probabilities = {pair: row[order] for pair, row in zip(fixtures, estimates)}
        return {
            "year": year,
            "seed": seed,
            "rounds": simulate(self.clubs, probabilities, seed),
            "model_name": self.model_name(selected),
            "model_id": selected,
            "model_version": self.bundle["model_version"] + ":" + selected,
            "data_through": self.metadata["last_date"],
        }

    def health(self):
        return {
            "status": "ok",
            "model_loaded": True,
            "model_version": self.bundle["model_version"],
            "data_through": self.metadata["last_date"],
            "trained_through": self.bundle["data"]["last_date"],
        }

    def teams(self):
        return {
            "season": self.season,
            "models": {key: self.model_name(key) for key in self.pipelines},
            "default_model_id": self.default_model,
            "model_name": self.model_name(),
            "data_through": self.metadata["last_date"],
            "teams": [{"id": club, "name": self.history.names[club]} for club in self.clubs],
        }

    def predict(self, home, away, model_id=None):
        selected, pipeline = self.select_model(model_id)
        if home == away:
            raise ValueError("Escolha dois clubes diferentes.")
        if home not in self.clubs or away not in self.clubs:
            raise ValueError("Clube desconhecido ou ausente da temporada disponível.")
        features = pd.DataFrame([self.history.vector(home, away)], columns=FEATURES)
        values = dict(zip(pipeline.classes_, pipeline.predict_proba(features)[0]))
        warnings = [
            f"Confronto hipotético com dados até {self.metadata['last_date']}; "
            "não incorpora acontecimentos posteriores, escalações ou lesões."
        ]
        if len(self.history.games[home]) < 10 or len(self.history.games[away]) < 10:
            warnings.append("Histórico limitado: menos de dez partidas para pelo menos um clube.")
        if self.metadata["raw_sha256"] != self.bundle["data"]["raw_sha256"]:
            warnings.append("Históricos atualizados após o treinamento; o modelo não foi retreinado.")
        h2h = [m for m in self.history.matches if {m["home"], m["away"]} == {home, away}][-5:][::-1]
        return {
            "probabilities": {
                "home_win": float(values["H"]),
                "draw": float(values["D"]),
                "away_win": float(values["A"]),
            },
            "home": summarize(self.history, home, "H"),
            "away": summarize(self.history, away, "A"),
            "head_to_head": [
                {
                    "date": m["date"],
                    "home": self.history.names[m["home"]],
                    "away": self.history.names[m["away"]],
                    "home_goals": m["hg"],
                    "away_goals": m["ag"],
                }
                for m in h2h
            ],
            "model_version": self.bundle["model_version"] + ":" + selected,
            "data_through": self.metadata["last_date"],
            "trained_through": self.bundle["data"]["last_date"],
            "warnings": warnings,
            "model_id": selected,
            "model_name": self.model_name(selected),
        }
