# cron_job.py
from token_manager import refresh_token
from main import post_to_pinterest

def run():
    access_token = refresh_token()  # now returns a string
    if not access_token:
        print("❌ Failed to refresh access token. Aborting job.")
        return
    result = post_to_pinterest(access_token)
    print("Job finished:", result)

if __name__ == "__main__":
    run()
