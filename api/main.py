import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.routers import router
from api.services import PredictionService

logger = logging.getLogger("radar.api")


def create_app(service_factory=PredictionService):
    @asynccontextmanager
    async def lifespan(app):
        app.state.service = service_factory()
        yield
        app.state.service = None

    app = FastAPI(
        title="Radar do Brasileirão",
        version="1.0.0",
        lifespan=lifespan,
        description="Confrontos hipotéticos baseados no histórico do Kaggle / Adão Duque.",
    )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logger.error("Falha em %s", request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=500, content={"detail": "Não foi possível concluir a análise. Tente novamente."}
        )

    app.include_router(router)
    return app


app = create_app()
