from flask import Flask, request
import requests

app = Flask(__name__)

CLIENT_ID = "1532930"
CLIENT_SECRET = "4755245a4e62d9c9eb0a2cd2f0ea7f2c8b06d479"
REDIRECT_URI = "http://localhost:8080/oauth/callback"

@app.route('/')
def home():
    return "Local server running!"

@app.route('/oauth/callback')
def oauth_callback():
    code = request.args.get('code')

    if not code:
        return "No code received"

    print("\n🔹 CODE RECEIVED:", code)
    print("\n📩 Sending token exchange request...\n")

    token_url = "https://api.pinterest.com/v5/oauth/token"

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }

    response = requests.post(
        token_url,
        data=data,  # IMPORTANT CHANGE
        auth=(CLIENT_ID, CLIENT_SECRET),
        headers={"Content-Type": "application/x-www-form-urlencoded"}  # IMPORTANT
    )

    print("🔐 Response from Pinterest:")
    print(response.json())

    return "Token received! Check your terminal for details."

if __name__ == "__main__":
    print("🚀 Local server running on http://localhost:8080")
    app.run(port=8080, debug=True)
