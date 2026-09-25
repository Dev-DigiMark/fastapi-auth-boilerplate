import asyncio
import os

import httpx
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2 import id_token

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleAuthService:
    @staticmethod
    def get_google_auth_url():
        """
        Generate Google OAuth URL for authentication.
        """
        return (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"response_type=code&"
            f"client_id={GOOGLE_CLIENT_ID}&"
            f"redirect_uri={GOOGLE_REDIRECT_URI}&"
            f"scope=email profile"
        )

    @staticmethod
    async def exchange_code_for_tokens(code: str):
        """
        Exchange the authorization code for access and ID tokens.
        """
        payload = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(GOOGLE_TOKEN_URL, data=payload)

        if response.status_code != 200:
            raise Exception("Failed to fetch tokens")

        return response.json()

    @staticmethod
    async def get_user_info(id_token_str: str):
        """
        Get user information from the ID token.

        google-auth's verifier is synchronous, so it runs in a worker thread.
        """
        try:
            id_info = await asyncio.to_thread(
                id_token.verify_oauth2_token,
                id_token_str,
                Request(),
                GOOGLE_CLIENT_ID,
            )
            return {
                "email": id_info["email"],
                "name": id_info.get("name", ""),
                "picture": id_info.get("picture", ""),
                "sub": id_info["sub"],
            }
        except ValueError as e:
            raise Exception(f"Invalid ID token: {e}")
