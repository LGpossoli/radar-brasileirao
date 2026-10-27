import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.evaluation_schemas import EvaluationReport
from api.main import create_app
from api.services import PredictionService
from radar.config import ROOT
from ui.evaluation import filtered_matches


@pytest.fixture(scope="module")
def evaluation_report():
    return EvaluationReport.model_validate_json(
        (ROOT / "reports/evaluation.json").read_text(encoding="utf-8")
    )


def test_metrics_and_match_alignment(evaluation_report):
    historical = json.loads((ROOT / "reports/metrics.json").read_text(encoding="utf-8"))
    for key, model in evaluation_report.models.items():
        assert model.metrics.hits + model.metrics.errors == model.metrics.total == 760
        assert model.metrics.accuracy == pytest.approx(model.metrics.hits / 760)
        for field in ("accuracy", "f1_macro", "log_loss"):
            assert getattr(model.metrics, field) == pytest.approx(historical["test_by_model"][key][field])
        assert {row.season for row in model.matches} == {2023, 2024}


@pytest.mark.parametrize("damage", ["hits", "probabilities", "actual", "period", "version_schema"])
def test_invalid_report_rejected(evaluation_report, damage):
    data = evaluation_report.model_dump(mode="json")
    model = data["models"]["regressao_logistica"]
    if damage == "hits":
        model["metrics"]["hits"] += 1
    elif damage == "probabilities":
        model["matches"][0]["probabilities"]["H"] = 1.5
    elif damage == "actual":
        row = model["matches"][0]
        row["actual"] = "A" if row["actual"] != "A" else "H"
    elif damage == "period":
        data["periods"]["train"] = "2003–2025"
    else:
        data["schema_version"] = 9
    with pytest.raises(ValidationError):
        EvaluationReport.model_validate(data)


def test_evaluation_loaded_once_and_no_request_io(monkeypatch):
    original = Path.read_text
    reads = []

    def read(path, *args, **kwargs):
        if path.name == "evaluation.json":
            reads.append(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)
    with TestClient(create_app()) as client:
        assert len(reads) == 1
        monkeypatch.setattr(Path, "read_text", lambda *args, **kwargs: pytest.fail("Leitura em consulta"))
        for key in ("regressao_logistica", "arvore_decisao", "random_forest"):
            result = client.get("/v1/evaluation", params={"model_id": key})
            assert result.status_code == 200
            assert result.json()["model_id"] == key
            assert result.json()["metrics"]["total"] == 760
        assert client.get("/v1/evaluation?model_id=inexistente").status_code == 400


@pytest.mark.parametrize("contents", [None, "{}", "mismatch"])
def test_unavailable_report_does_not_break_analysis(tmp_path, evaluation_report, contents):
    path = tmp_path / "evaluation.json"
    if contents == "mismatch":
        data = evaluation_report.model_dump(mode="json")
        data["production_version"] = "incompativel"
        path.write_text(json.dumps(data), encoding="utf-8")
    elif contents is not None:
        path.write_text(contents, encoding="utf-8")
    with TestClient(create_app(lambda: PredictionService(evaluation_path=path))) as client:
        assert client.get("/v1/evaluation").status_code == 503
        assert client.get("/health").status_code == 200
        assert (
            client.post(
                "/v1/predict", json={"home_team_id": "flamengo", "away_team_id": "palmeiras"}
            ).status_code
            == 200
        )


def test_filters_do_not_change_overall_metrics(evaluation_report):
    model = evaluation_report.models["regressao_logistica"].model_dump(mode="json")
    before = dict(model["metrics"])
    rows = filtered_matches(model["matches"], 2023, "Flamengo", "Erros")
    assert rows
    assert all(
        row["season"] == 2023 and "Flamengo" in (row["home"], row["away"]) and not row["correct"]
        for row in rows
    )
    assert model["metrics"] == before
    assert not filtered_matches(model["matches"], "Todas", "inexistente", "Todos")


def test_simulation_year_optional_and_only_a_label(service):
    with TestClient(create_app(lambda: service)) as client:
        result = client.post("/v1/simulate", json={"seed": 42})
        assert result.status_code == 200
        assert result.json()["year"] is None
        assert result.json()["rounds"] == service.simulate(2027, 42)["rounds"]
