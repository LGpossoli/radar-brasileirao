"""Simulo partidas sem alterar o histórico usado pelo modelo."""

import random


def schedule(clubs):
    if len(clubs) < 2 or len(clubs) % 2 or len(set(clubs)) != len(clubs):
        raise ValueError("Preciso de uma quantidade par de clubes distintos.")
    wheel = list(clubs)
    rounds = []
    for turn in range(len(wheel) - 1):
        pairs = list(zip(wheel[: len(wheel) // 2], reversed(wheel[len(wheel) // 2 :])))
        if turn % 2:
            pairs = [(away, home) for home, away in pairs]
        rounds.append(pairs)
        wheel = [wheel[0], wheel[-1], *wheel[1:-1]]
    return rounds + [[(away, home) for home, away in pairs] for pairs in rounds]


def simulate(clubs, probabilities, seed):
    rng = random.Random(seed)
    table = {club: dict(team_id=club, points=0, played=0, wins=0, draws=0, losses=0) for club in clubs}
    snapshots = []
    for fixtures in schedule(clubs):
        for home, away in fixtures:
            outcome = rng.choices(["H", "D", "A"], weights=probabilities[(home, away)])[0]
            h, a = table[home], table[away]
            h["played"] += 1
            a["played"] += 1
            if outcome == "D":
                for team in (h, a):
                    team["points"] += 1
                    team["draws"] += 1
            else:
                winner, loser = (h, a) if outcome == "H" else (a, h)
                winner["points"] += 3
                winner["wins"] += 1
                loser["losses"] += 1
        snapshots.append(
            sorted(
                [dict(row) for row in table.values()],
                key=lambda row: (-row["points"], -row["wins"], row["team_id"]),
            )
        )
    return snapshots
