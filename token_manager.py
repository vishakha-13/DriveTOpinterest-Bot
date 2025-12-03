# token_manager.py
import os
import requests

APP_ID = os.getenv("PINTEREST_APP_ID")
APP_SECRET = os.getenv("PINTEREST_APP_SECRET")


def _call_refresh_api(refresh_token):
    """Internal: call Pinterest token endpoint and return parsed JSON."""
    url = "https://api.pinterest.com/v5/oauth/token"

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
    }

    # IMPORTANT: Pinterest REQUIRES form-data, NOT JSON
    res = requests.post(url, data=data, timeout=30)

    try:
        return res.json()
    except Exception:
        return {"error": "invalid_json_response", "raw": res.text}


def refresh_access_token():
    """
    Public: refresh access token using the refresh token from env.
    Returns access_token string on success, or None on failure.
    """
    refresh_token = os.getenv("PINTEREST_REFRESH_TOKEN")
    if not refresh_token:
        print("❌ No REFRESH TOKEN found in environment variables!")
        return None

    print("🔄 Refreshing Pinterest access token...")
    result = _call_refresh_api(refresh_token)
    print("🔐 Pinterest Token Response:", result)

    if "access_token" not in result:
        print("❌ Failed to refresh token:", result)
        return None

    access_token = result["access_token"]

    print("✅ Token refresh complete. Access token created for this job.")
    return access_token


def refresh_and_update_env():
    """Compatibility wrapper used by your existing code."""
    return refresh_access_token()
