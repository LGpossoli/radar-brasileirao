import io

import joblib
import numpy as np
import pandas as pd
import pytest
import sklearn

from api.services import PredictionService
from radar.data import import_bytes, load_snapshot
from radar.features import FEATURE_VERSION, FEATURES, build_features
from radar.train import candidates


@pytest.fixture
def raw_csv():
    rows = [
        [1, 1, "01/08/2020", "Flamengo", "Palmeiras", 2, 1, "Flamengo"],
        [2, 2, "02/08/2020", "Palmeiras", "Santos", 0, 0, "-"],
        [3, 3, "01/02/2021", "Santos", "Flamengo", 0, 1, "Flamengo"],
        [4, 1, "01/06/2021", "Flamengo", "Santos", 1, 0, "Flamengo"],
    ]
    frame = pd.DataFrame(
        rows,
        columns=[
            "ID",
            "rodata",
            "data",
            "mandante",
            "visitante",
            "mandante_Placar",
            "visitante_Placar",
            "vencedor",
        ],
    )
    return frame.to_csv(index=False).encode()


@pytest.fixture
def clean(raw_csv):
    from radar.data import normalize

    return normalize(raw_csv)[0]


def csv_edit(raw, **changes):
    frame = pd.read_csv(io.BytesIO(raw))
    for column, value in changes.items():
        frame.loc[0, column] = value
    return frame.to_csv(index=False).encode()


@pytest.fixture
def service(tmp_path, raw_csv):
    metadata = import_bytes(raw_csv, tmp_path)
    _, matches = load_snapshot(tmp_path / "current.json")
    features, _ = build_features(matches)
    pipeline = candidates()["frequencias"]
    pipeline.fit(features[FEATURES], features.result)
    bundle = {
        "pipeline": pipeline,
        "feature_version": FEATURE_VERSION,
        "features": FEATURES,
        "sklearn": sklearn.__version__,
        "data": metadata,
        "model_version": "test",
    }
    model = tmp_path / "model.joblib"
    joblib.dump(bundle, model)
    restored = joblib.load(model)
    np.testing.assert_allclose(
        pipeline.predict_proba(features[FEATURES]), restored["pipeline"].predict_proba(features[FEATURES])
    )
    return PredictionService(model, tmp_path / "current.json")
