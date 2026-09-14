import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_PUBLISHABLE_KEY")
)

response = supabase.auth.sign_in_with_password({
    "email": "test@transition.dev",
    "password": "Hello123123"
})

print(response.session.access_token)
