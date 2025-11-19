def pinterest_auth():
    """Authenticate to Pinterest and store token."""
    if os.path.exists(TOKEN_FILE):
        print("✅ Pinterest connected using saved token.")
        return
    
    print("🌐 Opening Pinterest OAuth login...")
    auth_url = (
        f"https://www.pinterest.com/oauth/?response_type=code"
        f"&client_id={APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=boards:read,pins:read,pins:write,boards:write"
    )
    webbrowser.open(auth_url)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            code = query.get("code", [None])[0]
            if code:
                token_url = "https://api.pinterest.com/v5/oauth/token"
                data = {
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": REDIRECT_URI,
                    "client_id": APP_ID,
                    "client_secret": APP_SECRET,
                }
                res = requests.post(token_url, data=data)
                with open(TOKEN_FILE, "w") as f:
                    f.write(res.text)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"The authentication flow has completed. You may close this window.")
                print("✅ OAuth success! Token saved.")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"OAuth failed.")

    print("⚙️ Waiting for Pinterest authorization callback...")
    server = HTTPServer(("localhost", 8080), Handler)
    server.handle_request()

def get_pinterest_token():
    """Read access token and auto-refresh if needed."""
    try:
        if not os.path.exists(TOKEN_FILE):
            print("❌ No token file found.")
            return None

        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)

        # Return valid access token if not expired
        if "expires_at" in token_data:
            if time.time() > token_data["expires_at"]:
                print("⏳ Token expired — refreshing...")
                new_token = refresh_pinterest_token()
                return new_token
            else:
                return token_data.get("access_token")

        # If no expires_at field — fallback (Pinterest v5)
        return token_data.get("access_token")

    except Exception as e:
        print(f"⚠️ Failed to load Pinterest token: {e}")
        return None


def refresh_pinterest_token():
    """Refresh Pinterest access token if expired."""
    try:
        token_data = None
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                token_data = json.load(f)

        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            print("❌ No refresh token found!")
            return None

        url = "https://api.pinterest.com/v5/oauth/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
        }

        res = requests.post(url, data=data)
        response_json = res.json()

        if "access_token" in response_json:
            with open(TOKEN_FILE, "w") as f:
                json.dump(response_json, f)
            print("🔄 Pinterest token refreshed successfully!")
            return response_json["access_token"]
        else:
            print(f"❌ Refresh failed: {response_json}")
            return None

    except Exception as e:
        print(f"⚠️ Token refresh error: {e}")
        return None
