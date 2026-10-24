import pandas as pd

from radar.features import FEATURES, build_features


def test_future_results_do_not_change_earlier_features(clean):
    original, _ = build_features(clean)
    modified = clean.copy()
    modified.loc[3, ["hg", "ag", "result"]] = [0, 7, "A"]
    updated, _ = build_features(modified)
    pd.testing.assert_frame_equal(original[FEATURES], updated[FEATURES])


def test_same_day_results_cannot_leak(clean):
    clean.loc[1, "date"] = clean.loc[0, "date"]
    original, _ = build_features(clean)
    clean.loc[0, ["hg", "ag", "result"]] = [0, 7, "A"]
    updated, _ = build_features(clean)
    pd.testing.assert_frame_equal(original.iloc[:2][FEATURES], updated.iloc[:2][FEATURES])


def test_points_goals_and_mando_are_calculated(clean):
    _, history = build_features(clean)
    indicators = history.indicators("flamengo", "H")
    assert indicators["points5"] == 3
    assert indicators["scored5"] == 4 / 3
    assert indicators["venue_scored10"] == 1.5
