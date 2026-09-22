from app.routers.application import router as application_router
from app.routers.collaboration import router as collaboration_router
from app.routers.dashboard import router as dashboard_router
from app.routers.evidence import router as evidence_router
from app.routers.issue import router as issue_router
from app.routers.points import router as points_router
from app.routers.profile import router as profile_router
from app.routers.solution import router as solution_router
from app.routers.sponsorship import router as sponsorship_router

__all__ = [
    "profile_router",
    "issue_router",
    "points_router",
    "solution_router",
    "application_router",
    "collaboration_router",
    "evidence_router",
    "sponsorship_router",
    "dashboard_router",
]
