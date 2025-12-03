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
    res = requests.post(url, data=data, timeout=30)

    try:
        return res.json()
    except Exception:
        return {"error": "invalid_json_response", "raw": res.text}


def refresh_access_token():
    """
    Public function used by cron_job.py.
    Returns:
        { "access_token": "string", "refresh_token": "string" }
        OR None on failure.
    """
    refresh_token = os.getenv("PINTEREST_REFRESH_TOKEN")
    if not refresh_token:
        print("❌ No REFRESH TOKEN found in environment variables!")
        return None

    print("🔄 Refreshing Pinterest access token...")
    result = _call_refresh_api(refresh_token)
    print("Pinterest Token Response:", result)

    if "access_token" not in result:
        print("❌ Failed to refresh token:", result)
        return None

    access_token = result["access_token"]

    # Pinterest sometimes gives a new refresh token, else reuse old one
    new_refresh_token = result.get("refresh_token", refresh_token)

    print("✅ Token refresh complete.")

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token
    }


# For backward compatibility with your old main.py code:
def refresh_and_update_env():
    data = refresh_access_token()
    if not data:
        return None
    return data["access_token"]
