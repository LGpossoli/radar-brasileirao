from unittest.mock import Mock

import requests
from streamlit.testing.v1 import AppTest

from radar.config import ROOT
from ui.presentation import PALETTES, dashboard, luminance, team_colors, text_color


def fake_api(service, monkeypatch):
    catalog = Mock()
    catalog.json.return_value = service.teams()
    monkeypatch.setattr(requests, "get", Mock(return_value=catalog))

    def predict(*args, **kwargs):
        response = Mock()
        data = kwargs["json"]
        if args[0].endswith("/v1/simulate"):
            response.json.return_value = service.simulate(data["year"], data["seed"], data.get("model_id"))
        else:
            response.json.return_value = service.predict(
                data["home_team_id"], data["away_team_id"], data.get("model_id")
            )
        return response

    post = Mock(side_effect=predict)
    monkeypatch.setattr(requests, "post", post)
    return post


def button(app, label):
    return next(item for item in app.button if item.label == label)


def test_ui_calls_api_and_displays_probabilities(service, monkeypatch):
    post = fake_api(service, monkeypatch)
    app = AppTest.from_file(str(ROOT / "ui" / "app.py")).run()
    assert not app.exception
    assert post.call_args.kwargs["json"] == {
        "home_team_id": "flamengo",
        "away_team_id": "santos",
        "model_id": "frequencias",
    }
    assert any('class="prob-chart"' in item.value for item in app.markdown)
    assert any("Dados até 01/06/2021" in item.value for item in app.markdown)


def test_swap_updates_selectors_and_recalculates(service, monkeypatch):
    post = fake_api(service, monkeypatch)
    app = AppTest.from_file(str(ROOT / "ui" / "app.py")).run()
    button(app, "⇄ Inverter").click().run()
    assert not app.exception
    assert [item.value for item in app.selectbox][1:3] == ["santos", "flamengo"]
    assert post.call_args.kwargs["json"] == {
        "home_team_id": "santos",
        "away_team_id": "flamengo",
        "model_id": "frequencias",
    }
    assert app.session_state["analysis"]["home"]["team_id"] == "santos"


def test_same_team_clears_previous_analysis(service, monkeypatch):
    fake_api(service, monkeypatch)
    app = AppTest.from_file(str(ROOT / "ui" / "app.py")).run()
    app.selectbox[2].select("flamengo").run()
    assert not app.exception
    assert app.warning[0].value == "Escolha dois clubes diferentes."
    assert not any('class="prob-chart"' in item.value for item in app.markdown)


def test_readme_opens_in_project_menu(service, monkeypatch):
    fake_api(service, monkeypatch)
    app = AppTest.from_file(str(ROOT / "ui" / "app.py")).run()
    button(app, "Ler README").click().run()
    assert not app.exception
    assert any("## Instalação" in item.value for item in app.markdown)


def test_ui_unavailable_api(monkeypatch):
    monkeypatch.setattr(requests, "get", Mock(side_effect=requests.ConnectionError))
    app = AppTest.from_file(str(ROOT / "ui" / "app.py")).run()
    assert not app.exception
    assert "indisponível" in app.error[0].value


def test_identical_palettes_have_distinct_colors():
    for home, away in [("santos", "corinthians"), ("flamengo", "vitoria"), ("palmeiras", "juventude")]:
        first, second = team_colors(home, away)
        assert first in PALETTES[home] and second in PALETTES[away]
        assert first != second


def test_percentage_text_meets_contrast_ratio():
    for palette in list(PALETTES.values()) + [["#89979f"]]:
        for color in palette:
            levels = sorted([luminance(color), luminance(text_color(color))])
            assert (levels[1] + 0.05) / (levels[0] + 0.05) >= 4.5


def test_percentages_use_brazilian_decimal_separator(service):
    html = dashboard(service.predict("flamengo", "santos"))
    assert "50,0%" in html and "25,0%" in html
    assert "50.0%" not in html


def test_simulation_renders_and_year_change_resets_it(service, monkeypatch):
    import time

    fake_api(service, monkeypatch)
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    app = AppTest.from_file(str(ROOT / "ui" / "app.py")).run()
    button(app, "Simular campeonato").click().run()
    assert not app.exception
    assert any("Rodada 2 de 2" in item.value for item in app.markdown)
    assert app.session_state["simulation"]["model_name"] == "Frequências históricas"
    app.selectbox[3].select(app.selectbox[3].value + 1).run()
    assert not app.exception
    assert any("Rodada 0 de 2" in item.value for item in app.markdown)


def test_pie_has_no_internal_stroke(service):
    html = dashboard(service.predict("flamengo", "santos"))
    assert html.count("<path ") == 3
    assert html.count('stroke="none"') == 3


def test_switching_model_updates_prediction_and_clears_simulation(service, monkeypatch):
    import time

    service.pipelines["arvore_decisao"] = service.pipeline
    fake_api(service, monkeypatch)
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    app = AppTest.from_file(str(ROOT / "ui" / "app.py")).run()
    button(app, "Simular campeonato").click().run()
    assert app.session_state["simulation"]["model_id"] == "frequencias"
    app.selectbox(key="model_id").select("arvore_decisao").run()
    assert not app.exception
    assert app.session_state["analysis"]["model_id"] == "arvore_decisao"
    assert any("Rodada 0 de 2" in item.value for item in app.markdown)
    button(app, "Simular campeonato").click().run()
    assert app.session_state["simulation"]["model_id"] == "arvore_decisao"
