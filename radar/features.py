"""Indicadores pré-jogo. Atualizações acontecem somente após processar o dia inteiro."""

from collections import defaultdict

import numpy as np
import pandas as pd

FEATURE_VERSION = 1
METRICS = [
    "points5",
    "points10",
    "scored5",
    "conceded5",
    "venue_points10",
    "venue_scored10",
    "venue_conceded10",
    "history_count",
]
FEATURES = [f"{side}_{key}" for side in ["home", "away"] for key in METRICS] + ["elo_difference"]


def average(records, key):
    return float(np.mean([r[key] for r in records])) if records else float("nan")


class History:
    def __init__(self):
        self.games = defaultdict(list)
        self.elo = defaultdict(lambda: 1500.0)
        self.matches = []
        self.names = {}

    def indicators(self, club, venue):
        games = self.games[club]
        same_venue = [g for g in games if g["venue"] == venue][-10:]
        return {
            "points5": average(games[-5:], "points"),
            "points10": average(games[-10:], "points"),
            "scored5": average(games[-5:], "scored"),
            "conceded5": average(games[-5:], "conceded"),
            "venue_points10": average(same_venue, "points"),
            "venue_scored10": average(same_venue, "scored"),
            "venue_conceded10": average(same_venue, "conceded"),
            "history_count": min(len(games), 10),
        }

    def vector(self, home, away):
        values = {f"home_{k}": v for k, v in self.indicators(home, "H").items()}
        values.update({f"away_{k}": v for k, v in self.indicators(away, "A").items()})
        values["elo_difference"] = self.elo[home] - self.elo[away]
        return values

    def update_day(self, records):
        changes = defaultdict(float)
        for row in records:
            home, away = row["home"], row["away"]
            expected = 1 / (1 + 10 ** ((self.elo[away] - self.elo[home] - 65) / 400))
            actual = {"H": 1.0, "D": 0.5, "A": 0.0}[row["result"]]
            delta = 20 * (actual - expected)
            changes[home] += delta
            changes[away] -= delta
            for club, opponent, venue, scored, conceded, points in [
                (home, away, "H", row["hg"], row["ag"], 3 if actual == 1 else 1 if actual == 0.5 else 0),
                (away, home, "A", row["ag"], row["hg"], 3 if actual == 0 else 1 if actual == 0.5 else 0),
            ]:
                self.games[club].append(
                    {
                        "date": row["date"],
                        "opponent": opponent,
                        "venue": venue,
                        "scored": scored,
                        "conceded": conceded,
                        "points": points,
                    }
                )
            self.names[home], self.names[away] = row["home_name"], row["away_name"]
            self.matches.append(row)
        for club, delta in changes.items():
            self.elo[club] += delta


def build_features(matches: pd.DataFrame) -> tuple[pd.DataFrame, History]:
    history = History()
    rows = []
    for _, group in matches.sort_values(["date", "id"]).groupby("date", sort=True):
        records = group.to_dict(orient="records")
        for row in records:
            rows.append(
                {
                    **history.vector(row["home"], row["away"]),
                    "result": row["result"],
                    "season": row["season"],
                    "id": row["id"],
                }
            )
        history.update_day(records)
    return pd.DataFrame(rows), history


def summarize(history: History, club: str, venue: str) -> dict:
    values = history.indicators(club, venue)
    games = history.games[club]
    return {
        "team_id": club,
        "name": history.names.get(club, club),
        "games_available": len(games),
        "recent_form": [{3: "V", 1: "E", 0: "D"}[g["points"]] for g in games[-5:]],
        "points_percentage_5": None if not games else values["points5"] / 3 * 100,
        "points_percentage_10": None if not games else values["points10"] / 3 * 100,
        "goals_scored_5": None if not games else values["scored5"],
        "goals_conceded_5": None if not games else values["conceded5"],
        "venue_points_percentage_10": None
        if np.isnan(values["venue_points10"])
        else values["venue_points10"] / 3 * 100,
        "venue_goals_scored_10": None if np.isnan(values["venue_scored10"]) else values["venue_scored10"],
        "venue_goals_conceded_10": None
        if np.isnan(values["venue_conceded10"])
        else values["venue_conceded10"],
        "elo": history.elo[club],
        "limited_history": len(games) < 10,
    }
