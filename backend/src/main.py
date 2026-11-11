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

from src.modules.classes.router import router as classes_router
from src.modules.events.router import router as events_router
from src.modules.syllabus.router import router as syllabus_router
from src.middlewares.security import (
    BodyLimitMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    env_flag,
    parse_cors_origins,
)
from src.middlewares.upload_limits import UploadLimitsMiddleware


# A documentação interativa descreve toda a superfície da API. Em
# homologação/produção, definir API_DOCS_ENABLED=false.
docs_enabled = env_flag("API_DOCS_ENABLED", True)

app = FastAPI(
    title="Agenda UnB API",
    version="1.0.0",
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_url="/openapi.json" if docs_enabled else None,
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
    logger.error("Database failure on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=503,
        content={"detail": "O serviço de dados está indisponível no momento."},
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning("Validation error on %s %s", request.method, request.url.path)
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
        content={"detail": "; ".join(messages), "errors": [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]},
    )

default_origins = "http://localhost:5173,http://127.0.0.1:5173"
# Deploys da Vercel entram como origens exatas e passam pela mesma validação.
vercel_origins = [
    f"https://{host.strip()}"
    for host in (os.getenv("VERCEL_URL", ""), os.getenv("VERCEL_PROJECT_PRODUCTION_URL", ""))
    if host.strip()
]
allowed_origins = parse_cors_origins(",".join([os.getenv("CORS_ORIGINS", default_origins), *vercel_origins]))

# A última camada adicionada é a mais externa. Ordem de entrada da requisição:
# cabeçalhos de segurança -> CORS -> limite de taxa -> limites de corpo -> rotas.
# O CORS fica por fora dos limites para que 413/429 cheguem legíveis ao navegador.
app.add_middleware(UploadLimitsMiddleware)
app.add_middleware(BodyLimitMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    # A sessão viaja no cabeçalho Authorization, nunca em cookie.
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Idempotency-Key"],
    expose_headers=["Retry-After"],
    max_age=600,
)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(classes_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")
app.include_router(syllabus_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
@app.get("/api/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
