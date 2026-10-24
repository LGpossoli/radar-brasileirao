from fastapi import APIRouter, HTTPException, Request

from api.schemas import Health, PredictInput, Prediction, Teams

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
    return service.predict(payload.home_team_id, payload.away_team_id)
