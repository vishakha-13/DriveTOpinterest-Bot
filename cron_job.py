from token_manager import refresh_access_token
from main import run_daily_uploads

def run():
    tokens = refresh_access_token()
    if not tokens:
        print("❌ Failed to refresh Pinterest token. Aborting.")
        return

    access_token = tokens["access_token"]
    run_daily_uploads(access_token)

if __name__ == "__main__":
    run()
