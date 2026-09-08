from fastapi import APIRouter

from app.api.routes.cases import router as cases_router

router = APIRouter()


@router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


router.include_router(cases_router, prefix="/api")
