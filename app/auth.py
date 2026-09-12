import os
from dotenv import load_dotenv
from supabase import create_client,Client
from fastapi.security import HTTPBearer
from fastapi import Depends, HTTPException, status
load_dotenv()
security=HTTPBearer()
SUPABASE_URL=os.getenv("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY=os.getenv("SUPABASE_PUBLISHABLE_KEY")

supabase: Client =create_client(
    SUPABASE_URL,
    SUPABASE_PUBLISHABLE_KEY
)


def get_current_user(credentials=Depends(security)):
    cred=credentials.credentials
    response=supabase.auth.get_user(cred)
    if not response.user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid authentication credentials")
    return response.user
