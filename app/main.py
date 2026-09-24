import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, otp, user
from app.middlewares.auth_middleware import AuthMiddleware
from app.database.db_config import create_database  # Import create_database function

load_dotenv()

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

API_DESCRIPTION = """
Authentication backend with email/password signup, OTP verification, Google
OAuth, and password reset.

### Typical signup flow

1. `POST /auth/signup` — creates the account and emails or texts a 6-digit code.
   Keep the `user_id` from the response; it is encrypted, not the numeric ID.
2. `POST /otp/verify` — send that `user_id` plus the code to activate the account.
3. `POST /auth/login` — returns a JWT access token.
4. Send `Authorization: Bearer <token>` on protected endpoints.

Logging in before verifying does not fail — it sends a fresh code and returns
the `user_id` again instead of a token.

### Authorizing in this page

Call `/auth/login`, copy the `access_token`, then click **Authorize** above and
paste it to unlock the endpoints marked with a padlock.
"""

TAGS_METADATA = [
    {
        "name": "Auth",
        "description": "Signup, login, Google OAuth, and password reset.",
    },
    {
        "name": "OTP",
        "description": (
            "One-time codes for account verification. Codes are 6 digits and "
            "expire after 5 minutes."
        ),
    },
    {
        "name": "Users",
        "description": "Profile lookups. All endpoints require a bearer token.",
    },
    {
        "name": "Health Check",
        "description": "Liveness probe for uptime monitoring.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to execute during application startup
    print("Application is starting up...")
    create_database()  # Call the function to create the database and tables

    yield  # Application is running here
    # Code to execute during application shutdown
    print("Application is shutting down...")

app = FastAPI(
    title="FastAPI Auth Boilerplate",
    description=API_DESCRIPTION,
    version="1.0.0",
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)

# Include route modules
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(otp.router)




# Health Check Route
@app.get(
    "/",
    tags=["Health Check"],
    summary="Check that the API is up",
    response_description="A static ok payload.",
)
def health_check():
    """
    Liveness probe. Requires no authentication and does not touch the database,
    so it stays fast and will keep returning ok even if the database is down.
    """
    return {"status": "ok", "message": "API is running successfully"}

