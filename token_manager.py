import os
import json
import time
import requests

RENDER_API_KEY = os.getenv("RENDER_API_KEY")
SERVICE_ID = os.getenv("RENDER_SERVICE_ID")
APP_ID = os.getenv("PINTEREST_APP_ID")
APP_SECRET = os.getenv("PINTEREST_APP_SECRET")


def refresh_and_update_env():
    """Refresh Pinterest token and update Render env variables automatically."""

    refresh_token = os.getenv("PINTEREST_REFRESH_TOKEN")
    if not refresh_token:
        print("❌ No refresh token found! Cannot refresh.")
        return None

    print("🔄 Refreshing Pinterest token...")

    url = "https://api.pinterest.com/v5/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
    }

    res = requests.post(url, data=data)
    result = res.json()
    print("Pinterest Response:", result)

    if "access_token" not in result:
        print("❌ Token refresh failed:", result)
        return None

    new_access_token = result["access_token"]
    new_refresh_token = result.get("refresh_token", refresh_token)  # fallback

    print("✅ Token refreshed. Updating Render environment…")

    update_url = f"https://api.render.com/v1/services/{SERVICE_ID}/env-vars"

    payload = {
        "envVars": [
            {"key": "PINTEREST_ACCESS_TOKEN", "value": new_access_token},
            {"key": "PINTEREST_REFRESH_TOKEN", "value": new_refresh_token},
        ]
    }

    headers = {
        "Authorization": f"Bearer {RENDER_API_KEY}",
        "Content-Type": "application/json"
    }

    r = requests.put(update_url, headers=headers, json=payload)

    if r.status_code == 200:
        print("🎉 SUCCESS! Render env variables updated automatically.")
    else:
        print("❌ FAILED to update Render:", r.text)

    return new_access_token
