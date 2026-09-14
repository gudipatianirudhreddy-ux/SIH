from fastapi import Depends, FastAPI

from app.auth import get_current_user
from app.routers import issue_router, profile_router, solution_router

tags_metadata = [
    {
        "name": "profiles",
        "description": "User profile management and role querying.",
    },
    {
        "name": "issues",
        "description": "Civic/societal problem reporting, GPS tagging, and AI categorization.",
    },
    {
        "name": "solutions",
        "description": "Student solution/prototype submissions and industry evaluations.",
    },
]

app = FastAPI(
    title="SIH 2026 Problem-Solving Platform API",
    description=(
        "A university-industry collaborative problem-solving platform connecting "
        "citizens, students, and industry partners."
    ),
    version="0.2.0",
    openapi_tags=tags_metadata,
)

app.include_router(profile_router)
app.include_router(issue_router)
app.include_router(solution_router)


@app.get("/", summary="Root health check")
def read_root():
    return {"Message": "Welcome to SIH project"}


@app.get("/me", summary="Authenticated user information")
def get_me(user=Depends(get_current_user)):
    return {
        "id": user.id,
        "email": getattr(user, "email", None),
    }