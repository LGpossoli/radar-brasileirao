from fastapi import APIRouter, HTTPException, Request

from api.schemas import Health, PredictInput, Prediction, Simulation, SimulationInput, Teams

router = APIRouter()


@router.get("/health", response_model=Health, tags=["Monitoramento"])
def health(request: Request):
    return request.app.state.service.health()


@router.get("/v1/teams", response_model=Teams, tags=["Confrontos"])
def teams(request: Request):
    return request.app.state.service.teams()


@router.post(
    "/v1/predict",
    response_model=Prediction,
    tags=["Confrontos"],
    responses={
        400: {"description": "Clubes iguais ou desconhecidos"},
        500: {"description": "Falha interna controlada"},
    },
)
def predict(payload: PredictInput, request: Request):
    service = request.app.state.service
    if payload.home_team_id == payload.away_team_id:
        raise HTTPException(400, "Escolha dois clubes diferentes.")
    if payload.home_team_id not in service.clubs or payload.away_team_id not in service.clubs:
        raise HTTPException(400, "Clube desconhecido ou ausente da temporada disponível.")
    if payload.model_id is not None and payload.model_id not in service.pipelines:
        raise HTTPException(400, "Modelo desconhecido ou indisponível.")
    return service.predict(payload.home_team_id, payload.away_team_id, payload.model_id)


@router.post("/v1/simulate", response_model=Simulation, tags=["Campeonato"])
def simulate(payload: SimulationInput, request: Request):
    service = request.app.state.service
    if payload.model_id is not None and payload.model_id not in service.pipelines:
        raise HTTPException(400, "Modelo desconhecido ou indisponível.")
    return service.simulate(payload.year, payload.seed, payload.model_id)
