from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from api.main import create_app
from radar.simulation import schedule, simulate


def test_calendar_has_380_unique_games_and_balanced_venues():
    clubs = [str(i) for i in range(20)]
    rounds = schedule(clubs)
    matches = [pair for fixtures in rounds for pair in fixtures]
    assert len(rounds) == 38
    assert len(matches) == len(set(matches)) == 380
    for fixtures in rounds:
        assert sorted(team for pair in fixtures for team in pair) == sorted(clubs)
    for team in clubs:
        assert sum(h == team for h, a in matches) == 19
        assert sum(a == team for h, a in matches) == 19


def test_table_conserves_results_and_seed_is_reproducible():
    clubs = [str(i) for i in range(20)]
    probabilities = {pair: [0.45, 0.3, 0.25] for fixtures in schedule(clubs) for pair in fixtures}
    result = simulate(clubs, probabilities, 123)
    assert result == simulate(clubs, probabilities, 123)
    assert result != simulate(clubs, probabilities, 124)
    for number, table in enumerate(result, 1):
        assert all(row["played"] == number for row in table)
        assert sum(row["wins"] for row in table) == sum(row["losses"] for row in table)
        for row in table:
            assert row["points"] == row["wins"] * 3 + row["draws"]
            assert row["played"] == row["wins"] + row["draws"] + row["losses"]


def test_api_simulation_and_validation(service):
    year = datetime.now(ZoneInfo("America/Sao_Paulo")).year + 1
    before = service.predict("flamengo", "santos")
    with TestClient(create_app(lambda: service)) as client:
        response = client.post("/v1/simulate", json={"year": year, "seed": 9})
        assert response.status_code == 200
        assert len(response.json()["rounds"]) == 2
        for invalid in (
            {"year": year - 1, "seed": 9},
            {"year": year + 5, "seed": 9},
            {"year": str(year), "seed": 9},
            {"year": year, "seed": -1},
            {"year": year, "seed": 9, "extra": True},
        ):
            assert client.post("/v1/simulate", json=invalid).status_code == 422
    assert service.predict("flamengo", "santos") == before
