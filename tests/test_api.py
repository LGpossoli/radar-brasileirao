import joblib
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.services import PredictionService


def test_lifespan_loads_once_and_predicts_without_io(service, monkeypatch):
    calls = []

    def factory():
        calls.append(1)
        return service

    with TestClient(create_app(factory)) as client:
        monkeypatch.setattr(joblib, "load", lambda *a, **k: pytest.fail("Leitura em inferência"))
        assert client.get("/health").json()["model_loaded"] is True
        assert len(client.get("/v1/teams").json()["teams"]) == 2
        for _ in range(3):
            response = client.post("/v1/predict", json={"home_team_id": "flamengo", "away_team_id": "santos"})
            assert response.status_code == 200
            probabilities = response.json()["probabilities"]
            assert sum(probabilities.values()) == pytest.approx(1)
            assert all(0 <= p <= 1 for p in probabilities.values())
            assert response.json()["home"]["limited_history"] is True
    assert len(calls) == 1


@pytest.mark.parametrize(
    "payload,code",
    [
        ({"home_team_id": "flamengo", "away_team_id": "flamengo"}, 400),
        ({"home_team_id": "desconhecido", "away_team_id": "santos"}, 400),
        ({"home_team_id": 123, "away_team_id": "santos"}, 422),
        ({"home_team_id": "flamengo"}, 422),
        ({"home_team_id": "flamengo", "away_team_id": "santos", "extra": True}, 422),
    ],
)
def test_invalid_requests(service, payload, code):
    with TestClient(create_app(lambda: service)) as client:
        assert client.post("/v1/predict", json=payload).status_code == code


def test_internal_error_controlled_and_health_survives(service, monkeypatch):
    def fail(*args):
        raise RuntimeError("detalhe privado")

    monkeypatch.setattr(service, "predict", fail)
    with TestClient(create_app(lambda: service), raise_server_exceptions=False) as client:
        response = client.post("/v1/predict", json={"home_team_id": "flamengo", "away_team_id": "santos"})
        assert response.status_code == 500
        assert "detalhe privado" not in response.text
        assert client.get("/health").status_code == 200


def test_missing_artifact_prevents_startup(tmp_path):
    with pytest.raises(RuntimeError, match="artefatos"):
        PredictionService(tmp_path / "missing", tmp_path / "current.json")


def test_unknown_models_are_rejected(service):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    with TestClient(create_app(lambda: service)) as client:
        assert (
            client.post(
                "/v1/predict",
                json={"home_team_id": "flamengo", "away_team_id": "santos", "model_id": "inexistente"},
            ).status_code
            == 400
        )
        assert (
            client.post(
                "/v1/predict", json={"home_team_id": "flamengo", "away_team_id": "santos", "model_id": 42}
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/v1/simulate",
                json={
                    "year": datetime.now(ZoneInfo("America/Sao_Paulo")).year + 1,
                    "seed": 1,
                    "model_id": "inexistente",
                },
            ).status_code
            == 400
        )
