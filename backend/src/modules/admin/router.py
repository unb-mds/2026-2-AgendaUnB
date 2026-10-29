from fastapi import APIRouter, Depends
from src.middlewares.auth import require_admin

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])
