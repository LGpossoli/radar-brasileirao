from datetime import datetime
from zoneinfo import ZoneInfo

import joblib
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from api.main import create_app
from api.services import PredictionService
from radar.config import MODEL_PATH
from radar.features import FEATURES


def test_three_serialized_models_are_used_without_changing_shared_default():
    service = PredictionService()
    assert set(service.pipelines) == {"regressao_logistica", "arvore_decisao", "random_forest"}
    restored = joblib.load(MODEL_PATH)
    original = service.default_model
    vectors = pd.DataFrame(np.zeros((2, len(FEATURES))), columns=FEATURES)
    for key, pipeline in service.pipelines.items():
        np.testing.assert_allclose(
            pipeline.predict_proba(vectors), restored["pipelines"][key].predict_proba(vectors)
        )
    with TestClient(create_app(lambda: service)) as client:
        outputs = []
        for key in service.pipelines:
            result = client.post(
                "/v1/predict", json={"home_team_id": "flamengo", "away_team_id": "palmeiras", "model_id": key}
            )
            assert result.status_code == 200
            assert result.json()["model_id"] == key
            outputs.append(result.json()["probabilities"])
            season = client.post(
                "/v1/simulate",
                json={
                    "year": datetime.now(ZoneInfo("America/Sao_Paulo")).year + 1,
                    "seed": 100,
                    "model_id": key,
                },
            )
            assert season.status_code == 200
            assert season.json()["model_id"] == key
            assert len(season.json()["rounds"]) == 38
        assert outputs[0] != outputs[1] != outputs[2]
        assert service.default_model == original
