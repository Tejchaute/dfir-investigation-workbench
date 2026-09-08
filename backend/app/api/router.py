from fastapi import APIRouter

from app.api.routes.artifacts import artifact_router, evidence_artifact_router
from app.api.routes.cases import router as cases_router
from app.api.routes.evidence import case_evidence_router, evidence_router

router = APIRouter()


@router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


router.include_router(cases_router, prefix="/api")
router.include_router(case_evidence_router, prefix="/api")
router.include_router(evidence_router, prefix="/api")
router.include_router(evidence_artifact_router, prefix="/api")
router.include_router(artifact_router, prefix="/api")
