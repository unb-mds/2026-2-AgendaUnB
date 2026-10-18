import os
import logging
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.modules.events.router import router as events_router


app = FastAPI(
    title="Agenda UnB API",
    version="1.0.0",
)
logger = logging.getLogger("agenda_unb.api")


@app.exception_handler(IntegrityError)
async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.info("Database constraint rejected %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=409,
        content={"detail": "A operação conflita com os dados existentes."},
    )


@app.exception_handler(SQLAlchemyError)
async def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database failure on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=503,
        content={"detail": "O serviço de dados está indisponível no momento."},
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning("Validation error on %s %s: %s (body=%s)", request.method, request.url.path, exc.errors(), exc.body)
    field_labels = {
        "title": "Título",
        "description": "Descrição",
        "starts_at": "Data e horário",
        "campus": "Campus",
        "category": "Área / Categoria",
        "location": "Local",
        "external_url": "Link externo",
    }
    messages = []
    for error in exc.errors():
        field_name = str(error.get("loc", ["campo"])[-1])
        label = field_labels.get(field_name, field_name)
        msg = error.get("msg", "Inválido")
        if "at least 3 characters" in msg:
            msg = "deve ter pelo menos 3 caracteres"
        elif "at least 2 characters" in msg:
            msg = "deve ter pelo menos 2 caracteres"
        elif "fuso horário" in msg:
            msg = "deve incluir data e horário válidos com fuso"
        messages.append(f"{label}: {msg}")
    return JSONResponse(
        status_code=422,
        content={"detail": "; ".join(messages), "errors": exc.errors()},
    )

default_origins = "http://localhost:5173,http://127.0.0.1:5173"
allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", default_origins).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(events_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
