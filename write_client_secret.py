# write_client_secret.py
import os, json
js = os.getenv("CLIENT_SECRET_JSON")
if not js:
    print("No CLIENT_SECRET_JSON env var set; skipping.")
else:
    with open("client_secret.json", "w") as f:
        f.write(js)
    print("client_secret.json written.")
