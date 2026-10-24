from unittest.mock import Mock

import requests
from streamlit.testing.v1 import AppTest

from radar.config import ROOT


def test_ui_calls_api_and_displays_probabilities(service, monkeypatch):
    catalog = Mock()
    catalog.json.return_value = service.teams()
    prediction = Mock()
    prediction.json.return_value = service.predict("flamengo", "santos")
    monkeypatch.setattr(requests, "get", Mock(return_value=catalog))
    post = Mock(return_value=prediction)
    monkeypatch.setattr(requests, "post", post)
    app = AppTest.from_file(str(ROOT / "ui" / "app.py")).run()
    app.selectbox[0].select("flamengo")
    app.selectbox[1].select("santos")
    app.button[0].click().run()
    assert not app.exception
    assert len(app.metric) == 3
    assert post.call_args.kwargs["json"] == {"home_team_id": "flamengo", "away_team_id": "santos"}


def test_ui_unavailable_api(monkeypatch):
    monkeypatch.setattr(requests, "get", Mock(side_effect=requests.ConnectionError))
    app = AppTest.from_file(str(ROOT / "ui" / "app.py")).run()
    assert not app.exception
    assert "indisponível" in app.error[0].value
