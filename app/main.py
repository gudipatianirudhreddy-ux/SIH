from fastapi import FastAPI, Depends
from .auth import get_current_user
from app.routers import profile_router

app = FastAPI()
app.include_router(profile_router)

@app.get("/")
def read_root():
    return {"Message":"Welcome to SIH project"}

@app.get("/me")
def get_me(user=Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email
    }