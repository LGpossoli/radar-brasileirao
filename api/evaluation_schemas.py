"""Valido o relatório histórico antes de colocá-lo à disposição na API."""

from datetime import date
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sklearn.metrics import f1_score, log_loss

Result = Literal["A", "D", "H"]


class EvaluationContract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class EvaluationMatch(EvaluationContract):
    id: int
    season: Literal[2023, 2024]
    date: date
    home: str
    away: str
    home_goals: int = Field(ge=0)
    away_goals: int = Field(ge=0)
    probabilities: dict[Result, float]
    predicted: Result
    actual: Result
    correct: bool

    @model_validator(mode="after")
    def consistent_result(self):
        p = self.probabilities
        if set(p) != {"A", "D", "H"} or any(not 0 <= value <= 1 for value in p.values()):
            raise ValueError("Probabilidades inválidas.")
        if abs(sum(p.values()) - 1) > 1e-8:
            raise ValueError("As probabilidades devem somar um.")
        # Sigo a ordem de classes do scikit-learn, inclusive no desempate exato.
        predicted = max(("A", "D", "H"), key=p.get)
        actual = (
            "H" if self.home_goals > self.away_goals else "A" if self.home_goals < self.away_goals else "D"
        )
        if self.predicted != predicted or self.actual != actual or self.correct != (predicted == actual):
            raise ValueError("Resultado ou indicador de acerto inconsistente.")
        return self


class EvaluationMetrics(EvaluationContract):
    total: int = Field(gt=0)
    hits: int = Field(ge=0)
    errors: int = Field(ge=0)
    accuracy: float = Field(ge=0, le=1)
    f1_macro: float = Field(ge=0, le=1)
    log_loss: float = Field(ge=0)


class ModelEvaluation(EvaluationContract):
    metrics: EvaluationMetrics
    matches: list[EvaluationMatch]

    @model_validator(mode="after")
    def consistent_metrics(self):
        rows, m = self.matches, self.metrics
        if len({row.id for row in rows}) != len(rows) or len(rows) != m.total:
            raise ValueError("Quantidade de partidas inconsistente.")
        hits = sum(row.correct for row in rows)
        if m.hits != hits or m.errors != len(rows) - hits:
            raise ValueError("Contagem de acertos inconsistente.")
        actual, predicted = [row.actual for row in rows], [row.predicted for row in rows]
        probabilities = [[row.probabilities[label] for label in ("A", "D", "H")] for row in rows]
        expected = [
            hits / len(rows),
            f1_score(actual, predicted, labels=["A", "D", "H"], average="macro", zero_division=0),
            log_loss(actual, probabilities, labels=["A", "D", "H"]),
        ]
        if not np.allclose([m.accuracy, m.f1_macro, m.log_loss], expected, atol=1e-10, rtol=0):
            raise ValueError("Métricas não correspondem às previsões.")
        return self


class EvaluationReport(EvaluationContract):
    schema_version: Literal[1] = 1
    experiment_id: str
    production_version: str
    dataset_sha256: str
    periods: dict[str, str]
    selected_model: str
    retrospective: Literal[True] = True
    models: dict[str, ModelEvaluation]

    @model_validator(mode="after")
    def same_matches(self):
        required = {"regressao_logistica", "arvore_decisao", "random_forest", "frequencias"}
        if set(self.models) != required or self.selected_model not in required:
            raise ValueError("Catálogo de avaliação incompatível.")
        expected = None
        for model in self.models.values():
            games = [
                (row.id, row.season, row.date, row.home, row.away, row.home_goals, row.away_goals)
                for row in model.matches
            ]
            if expected is not None and games != expected:
                raise ValueError("Os modelos devem avaliar as mesmas partidas.")
            expected = games
        if (
            set(self.periods) != {"train", "validation", "test", "production"}
            or not self.periods.get("production")
            or self.periods.get("train") != "2003–2020"
            or self.periods.get("validation") != "2021–2022"
            or self.periods.get("test") != "2023–2024"
        ):
            raise ValueError("Divisão temporal incompatível.")
        return self


class EvaluationResponse(EvaluationContract):
    experiment_id: str
    periods: dict[str, str]
    retrospective: bool
    selected_model: str
    model_id: str
    model_name: str
    metrics: EvaluationMetrics
    comparison: dict[str, EvaluationMetrics]
    matches: list[EvaluationMatch]
