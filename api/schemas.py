from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class PredictInput(Contract):
    home_team_id: str = Field(
        strict=True,
        min_length=1,
        max_length=60,
        pattern=r"^[a-z0-9-]+$",
        description="ID do mandante retornado por /v1/teams",
    )
    away_team_id: str = Field(
        strict=True,
        min_length=1,
        max_length=60,
        pattern=r"^[a-z0-9-]+$",
        description="ID do visitante retornado por /v1/teams",
    )


class Probabilities(Contract):
    home_win: float = Field(ge=0, le=1)
    draw: float = Field(ge=0, le=1)
    away_win: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def sum_to_one(self):
        if abs(self.home_win + self.draw + self.away_win - 1) > 1e-8:
            raise ValueError("As probabilidades devem somar um.")
        return self


Percent = Annotated[float, Field(ge=0, le=100)]
Nonnegative = Annotated[float, Field(ge=0)]


class TeamSummary(Contract):
    team_id: str
    name: str
    games_available: int = Field(ge=0)
    recent_form: list[Literal["V", "E", "D"]] = Field(max_length=5)
    points_percentage_5: Percent | None
    points_percentage_10: Percent | None
    goals_scored_5: Nonnegative | None
    goals_conceded_5: Nonnegative | None
    venue_points_percentage_10: Percent | None
    venue_goals_scored_10: Nonnegative | None
    venue_goals_conceded_10: Nonnegative | None
    elo: float
    limited_history: bool


class Match(Contract):
    date: date
    home: str
    away: str
    home_goals: int = Field(ge=0)
    away_goals: int = Field(ge=0)


class Prediction(Contract):
    probabilities: Probabilities
    home: TeamSummary
    away: TeamSummary
    head_to_head: list[Match]
    model_version: str
    data_through: date
    trained_through: date
    warnings: list[str]


class Health(Contract):
    status: Literal["ok"]
    model_loaded: bool
    model_version: str
    data_through: date
    trained_through: date


class Team(Contract):
    id: str
    name: str


class Teams(Contract):
    model_name: str
    season: int
    data_through: date
    teams: list[Team]


class SimulationInput(Contract):
    year: int = Field(strict=True)
    seed: int = Field(strict=True, ge=0, le=4294967295)

    @model_validator(mode="after")
    def future_year(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo

        current = datetime.now(ZoneInfo("America/Sao_Paulo")).year
        if not current < self.year <= current + 5:
            raise ValueError("Escolha um dos próximos cinco anos.")
        return self


class Standing(Contract):
    team_id: str
    points: int = Field(ge=0)
    played: int = Field(ge=0)
    wins: int = Field(ge=0)
    draws: int = Field(ge=0)
    losses: int = Field(ge=0)


class Simulation(Contract):
    year: int
    seed: int
    rounds: list[list[Standing]]
    model_name: str
    model_version: str
    data_through: date
