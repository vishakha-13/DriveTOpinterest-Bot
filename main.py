import os
import io
import base64
import time
import json
import requests
import webbrowser
from dotenv import load_dotenv
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime, time as dt_time
import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from mail import send_email_notification
from token_manager import refresh_and_update_env


# =====================
# Load environment
# =====================
load_dotenv()

APP_ID = os.getenv("PINTEREST_APP_ID")
APP_SECRET = os.getenv("PINTEREST_APP_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
BOARD_ID = os.getenv("PINTEREST_BOARD_ID")

FOLDER_IDS = [value for key, value in os.environ.items() if key.startswith("DRIVE_FOLDER_ID_")]


# Posting Schedule Settings
MAX_PINS_PER_DAY = int(os.getenv("MAX_PINS_PER_DAY", 3))
POST_TIME = os.getenv("POST_TIME", "20:30")  # Format: HH:MM
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")


PIN_TITLE = "Ma Adya Mahakali"
PIN_DESCRIPTION = (
    "#UnderstandingKaali #AdyaKaaliSampradaya #BhairavKaaliKeNamoStute #Mahakali "
    "#DakshinaKali #KaliMaa #Bhairava #KaalBhairav #Shakti #SanatanDharma #Hinduism "
    "#Hindu #DivineMother #Devi #ShaktiSadhana #KaaliBhakti #Tantra #Aghor #Mahadev "
    "#Rudra #DashaMahavidya #KaliMantra #Adya #Maadya #BatukBhairava #MaKali "
    "#SwarnakarshanaBhairava #Kali #Krishna"
)
PIN_LINK = "https://youtube.com/@praveenrkalabhairava?feature=shared"

TOKEN_FILE = "pinterest_token.json"
DOWNLOAD_DIR = "downloads"
LOG_DIR = "logs"
UPLOADED_LOG = "uploaded_files.txt"
LAST_UPLOAD_DATE_FILE = "last_upload_date.txt"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# =====================
# Google Drive Setup
# =====================
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def connect_drive():
    """Connect to Google Drive API (Render-compatible, no browser needed)."""
    creds = None
    token_data = os.getenv("GOOGLE_TOKEN_JSON")

    try:
        # ✅ Use token from environment if available (for Render)
        if token_data:
            creds = Credentials.from_authorized_user_info(json.loads(token_data), SCOPES)
            print("🔐 Loaded Drive token from environment.")
        # ✅ Otherwise, fall back to local token.json (for local testing)
        elif os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
            print("📁 Loaded Drive token from local file.")
        else:
            raise RuntimeError("❌ No Google Drive token found — run locally once to generate token.json")

        # ✅ Refresh token if expired
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            print("🔁 Token refreshed successfully.")

        print("✅ Connected to Google Drive (Render-compatible).")
        send_email_notification("Drive Connected", "✅ Successfully connected to Google Drive API.")
        return build("drive", "v3", credentials=creds)

    except Exception as e:
        print(f"❌ Failed to connect to Google Drive: {e}")
        send_email_notification("Drive Connection Failed", f"❌ Error: {e}")
        raise

def list_images(service, folder_id):
    """List images in a Drive folder."""
    print(f"\n🔍 Checking folder: {folder_id}")
    
    results = service.files().list(
        q=f"'{folder_id}' in parents and mimeType contains 'image/' and trashed=false",
        fields="files(id, name, mimeType)"
    ).execute()
    
    images = results.get('files', [])
    print(f"🖼️  Image files found: {len(images)}")
    
    return images

def download_images(service, items):
    """Download new images from Drive."""
    downloaded = []
    skipped = 0
    
    for item in items:
        name = item['name']
        file_path = os.path.join(DOWNLOAD_DIR, name)
        
        if os.path.exists(file_path):
            skipped += 1
            continue
            
        request = service.files().get_media(fileId=item['id'])
        with io.FileIO(file_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        downloaded.append(file_path)
        print(f"📥 Downloaded: {name}")
    
    if skipped > 0:
        print(f"⏭️  Skipped {skipped} already downloaded files")
    
    return downloaded

# =====================
# Pinterest OAuth & Upload
# =====================
def get_pinterest_token():
    """Always load access token from environment or refresh with refresh token."""
    access_token = os.getenv("PINTEREST_ACCESS_TOKEN")
    refresh_token = os.getenv("PINTEREST_REFRESH_TOKEN")

    # If we already have access token, return it
    if access_token:
        return access_token

    # If no access token but refresh token exists → refresh
    if refresh_token:
        print("🔄 No access token found — refreshing using refresh token...")
        return refresh_and_update_env()

    print("❌ No Pinterest tokens found! Add this to .env:")
    print("PINTEREST_REFRESH_TOKEN=your_refresh_token")
    return None


def refresh_pinterest_token(token_data=None):
    """Refresh token only using environment refresh token."""
    refresh_token = os.getenv("PINTEREST_REFRESH_TOKEN")

    if not refresh_token:
        print("❌ Refresh token missing!")
        return None

    url = "https://api.pinterest.com/v5/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
    }

    res = requests.post(url, data=data)
    response = res.json()

    if "access_token" in response:
        print("🔄 Token refreshed successfully")
        return response["access_token"]

    print("❌ Failed to refresh token:", response)
    return None


def pinterest_auth():
    """Authenticate to Pinterest (skip if token exists in environment)."""
    # ✅ Check if token exists in environment variables
    if os.getenv("PINTEREST_ACCESS_TOKEN"):
        print("✅ Pinterest connected using PINTEREST_ACCESS_TOKEN from environment.")
        return
    
    if os.getenv("PINTEREST_TOKEN_JSON"):
        print("✅ Pinterest connected using PINTEREST_TOKEN_JSON environment.")
        return
    
    # ✅ Check if local token file exists
    if os.path.exists(TOKEN_FILE):
        print("✅ Pinterest connected using saved token file.")
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
                token_json = res.json()
                
                # Save to file
                with open(TOKEN_FILE, "w") as f:
                    json.dump(token_json, f, indent=2)
                
                # Print for environment variable
                print("\n" + "="*60)
                print("✅ OAuth success! Token saved to", TOKEN_FILE)
                print("\n🔑 For .env file, add these lines:")
                print(f"PINTEREST_ACCESS_TOKEN={token_json.get('access_token', '')}")
                print(f"PINTEREST_REFRESH_TOKEN={token_json.get('refresh_token', '')}")
                print("="*60 + "\n")
                
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Authentication successful! Check your terminal for the tokens.")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"OAuth failed.")

    print("⚙️ Waiting for Pinterest authorization callback...")
    server = HTTPServer(("localhost", 8080), Handler)
    server.handle_request()

def is_uploaded(filename):
    """Check if a file has already been uploaded."""
    if not os.path.exists(UPLOADED_LOG):
        return False
    with open(UPLOADED_LOG, 'r') as f:
        uploaded_files = f.read().splitlines()
    return filename in uploaded_files

def mark_as_uploaded(filename):
    """Mark a file as uploaded."""
    with open(UPLOADED_LOG, 'a') as f:
        f.write(filename + '\n')

def get_today_upload_count():
    """Get number of uploads done today."""
    if not os.path.exists(LAST_UPLOAD_DATE_FILE):
        return 0
    
    try:
        with open(LAST_UPLOAD_DATE_FILE, 'r') as f:
            data = json.load(f)
            last_date = data.get('date')
            count = data.get('count', 0)
            
            tz = pytz.timezone(TIMEZONE)
            today = datetime.now(tz).strftime('%Y-%m-%d')
            
            if last_date == today:
                return count
            else:
                return 0
    except:
        return 0

def update_upload_count(count):
    """Update today's upload count."""
    tz = pytz.timezone(TIMEZONE)
    today = datetime.now(tz).strftime('%Y-%m-%d')
    
    with open(LAST_UPLOAD_DATE_FILE, 'w') as f:
        json.dump({'date': today, 'count': count}, f)

def upload_to_pinterest(image_path):
    """Upload image to Pinterest (v5 JSON format)."""
    filename = os.path.basename(image_path)

    if is_uploaded(filename):
        print(f"⏭️  Already uploaded: {filename}")
        return True

    print(f"📸 Uploading {filename} to Pinterest...")

    # ----------------------------------------------------------
    # 🔐 STEP 1 — Get token (may auto-refresh if expired)
    # ----------------------------------------------------------
    token = get_pinterest_token()

    # If still no token → force a refresh using Render API
    if not token:
        print("❌ No valid token — forcing refresh via Render...")
        from token_manager import refresh_and_update_env
        token = refresh_and_update_env()

        if not token:
            print("❌ Could not refresh token. Upload aborted.")
            return False
    
    # ----------------------------------------------------------
    # 🖼️ STEP 2 — Prepare upload request
    # ----------------------------------------------------------
    try:
        url = "https://api.pinterest.com/v5/pins"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        with open(image_path, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode("utf-8")

        payload = {
            "board_id": BOARD_ID,
            "title": PIN_TITLE,
            "description": PIN_DESCRIPTION,
            "link": PIN_LINK,
            "media_source": {
                "source_type": "image_base64",
                "content_type": "image/jpeg",
                "data": img_base64
            }
        }

        res = requests.post(url, headers=headers, json=payload)

        # ----------------------------------------------------------
        # ⚠️ STEP 3 — If token expired → auto-refresh and RETRY once
        # ----------------------------------------------------------
        if res.status_code == 401:
            print("🔄 Token expired during upload — refreshing...")
            from token_manager import refresh_and_update_env
            token = refresh_and_update_env()

            if token:
                headers["Authorization"] = f"Bearer {token}"
                res = requests.post(url, headers=headers, json=payload)

        # After retry:
        if res.status_code in (200, 201):
            print(f"✅ Uploaded successfully: {filename}")
            mark_as_uploaded(filename)
            return True
        else:
            print(f"❌ Upload failed ({res.status_code}): {res.text}")
            return False

    except Exception as e:
        print(f"⚠️ Upload error for {filename}: {e}")
        return False



def get_pending_uploads():
    """Get list of downloaded files that haven't been uploaded yet."""
    pending = []
    if os.path.exists(DOWNLOAD_DIR):
        for filename in sorted(os.listdir(DOWNLOAD_DIR)):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                if not is_uploaded(filename):
                    pending.append(os.path.join(DOWNLOAD_DIR, filename))
    return pending
def post_to_pinterest(access_token, max_pins=None):
    """
    Called by cron_job.py.
    - access_token: freshly obtained access token (string)
    - max_pins: max pins to post in this run (defaults to MAX_PINS_PER_DAY)
    """
    if not access_token:
        print("❌ No access token provided to post_to_pinterest(). Aborting.")
        return {"posted": 0, "error": "no_access_token"}

    # Ensure upload functions that call get_pinterest_token() pick this token:
    os.environ["PINTEREST_ACCESS_TOKEN"] = access_token

    if max_pins is None:
        try:
            max_pins = int(MAX_PINS_PER_DAY)
        except Exception:
            max_pins = 3

    pending = get_pending_uploads()
    if not pending:
        print("📭 No pending images to upload.")
        return {"posted": 0}

    to_upload = pending[:max_pins]
    success = 0
    for img in to_upload:
        ok = upload_to_pinterest(img)
        if ok:
            success += 1
        # small delay to avoid hammering the API
        time.sleep(1)

    summary = {"posted": success, "attempted": len(to_upload)}
    print(f"✅ post_to_pinterest summary: {summary}")
    return summary


def is_posting_time():
    """Check if current time matches the scheduled posting time."""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    
    # Parse POST_TIME (format: HH:MM)
    post_hour, post_minute = map(int, POST_TIME.split(':'))
    post_time = dt_time(post_hour, post_minute)
    current_time = now.time()
    
    # Check if within 5 minutes of posting time
    time_diff = abs((current_time.hour * 60 + current_time.minute) - 
                    (post_time.hour * 60 + post_time.minute))
    
    return time_diff <= 5

def wait_until_post_time():
    """Calculate time to wait until next posting time."""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    
    post_hour, post_minute = map(int, POST_TIME.split(':'))
    
    # Create posting time for today
    post_datetime = now.replace(hour=post_hour, minute=post_minute, second=0, microsecond=0)
    
    # If posting time has passed today, schedule for tomorrow
    if now >= post_datetime:
        from datetime import timedelta
        post_datetime += timedelta(days=1)
    
    time_diff = (post_datetime - now).total_seconds()
    return time_diff

# =====================
# Automation Loop
# =====================
CHECK_INTERVAL = 60 * 5  # Check every 5 minutes

def main_loop():
    """Main automation loop with scheduled posting."""
    print("----- Starting Pinterest Automation -----")
    print(f"📅 Schedule: Upload {MAX_PINS_PER_DAY} pins daily at {POST_TIME} {TIMEZONE}")
    send_email_notification("Automation Started", 
                           f"🚀 Pinterest automation started.\n"
                           f"Schedule: {MAX_PINS_PER_DAY} pins per day at {POST_TIME} {TIMEZONE}")
    
    try:
        drive_service = connect_drive()
        pinterest_auth()
        
        print(f"🔄 Bot will check for new images every 5 minutes and upload at scheduled time.\n")
        
        while True:
            try:
                # Download new images from Drive
                new_images = []
                for folder_id in FOLDER_IDS:
                    items = list_images(drive_service, folder_id)
                    downloaded = download_images(drive_service, items)
                    new_images.extend(downloaded)

                if new_images:
                    print(f"📥 Downloaded {len(new_images)} new images.")
                
                # Check if it's posting time
                if is_posting_time():
                    today_count = get_today_upload_count()
                    remaining_slots = MAX_PINS_PER_DAY - today_count
                    
                    if remaining_slots > 0:
                        pending_uploads = get_pending_uploads()
                        
                        if pending_uploads:
                            to_upload = pending_uploads[:remaining_slots]
                            print(f"\n⏰ Posting time! Uploading {len(to_upload)} images...")
                            
                            successful_uploads = 0
                            for img in to_upload:
                                if upload_to_pinterest(img):
                                    successful_uploads += 1
                                    time.sleep(2)  # Small delay between uploads
                            
                            new_count = today_count + successful_uploads
                            update_upload_count(new_count)
                            
                            summary = (f"✅ Uploaded {successful_uploads} images to Pinterest.\n"
                                     f"Today's total: {new_count}/{MAX_PINS_PER_DAY}")
                            print(f"\n{summary}")
                            send_email_notification("Daily Upload Complete", summary)
                        else:
                            print("📭 No pending images to upload.")
                    else:
                        print(f"✋ Already uploaded {MAX_PINS_PER_DAY} images today. Will resume tomorrow.")
                else:
                    pending_count = len(get_pending_uploads())
                    today_count = get_today_upload_count()
                    
                    tz = pytz.timezone(TIMEZONE)
                    current_time = datetime.now(tz).strftime('%H:%M:%S')
                    
                    print(f"⏳ [{current_time}] Waiting for posting time ({POST_TIME})")
                    print(f"   📊 Pending: {pending_count} | Uploaded today: {today_count}/{MAX_PINS_PER_DAY}")
                
                print(f"💤 Sleeping for 5 minutes...\n")
                time.sleep(CHECK_INTERVAL)

            except Exception as e:
                error_msg = f"Error in main loop: {str(e)}"
                print(f"⚠️ {error_msg}")
                send_email_notification("Automation Error", error_msg)
                print(f"🕒 Retrying in 5 minutes...")
                time.sleep(CHECK_INTERVAL)
                
    except Exception as e:
        critical_error = f"Critical error during startup: {str(e)}"
        print(f"❌ {critical_error}")
        send_email_notification("Critical Automation Error", critical_error)
        raise

if __name__ == "__main__":
    try:
        # Run your Pinterest automation loop
        from threading import Thread
        t = Thread(target=main_loop)
        t.start()

        # 🟢 Keep-alive mini web server (so Render detects a port)
        from http.server import SimpleHTTPRequestHandler, HTTPServer
        import socket

        PORT = int(os.environ.get("PORT", 10000))
        with HTTPServer(("0.0.0.0", PORT), SimpleHTTPRequestHandler) as httpd:
            print(f"✅ Keep-alive server running on port {PORT}")
            httpd.serve_forever()

    except Exception as e:
        print(f"❌ Critical error during startup: {e}")
        send_email_notification("Critical Error", str(e))
