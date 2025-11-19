import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get your access token
access_token = os.getenv("PINTEREST_ACCESS_TOKEN")

if not access_token:
    print("❌ PINTEREST_ACCESS_TOKEN not found in .env file")
    exit(1)

# Fetch all boards
url = "https://api.pinterest.com/v5/boards"
headers = {
    "Authorization": f"Bearer {access_token}"
}

try:
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        boards = data.get('items', [])
        
        print("\n" + "="*60)
        print("📌 YOUR PINTEREST BOARDS:")
        print("="*60)
        
        for board in boards:
            board_id = board.get('id')
            board_name = board.get('name')
            print(f"\n📋 Name: {board_name}")
            print(f"   ID: {board_id}")
        
        print("\n" + "="*60)
        print("Copy the ID of the board you want to use and update your .env file:")
        print("PINTEREST_BOARD_ID=<paste_the_numeric_id_here>")
        print("="*60 + "\n")
    else:
        print(f"❌ Failed to fetch boards: {response.status_code}")
        print(f"Response: {response.text}")

except Exception as e:
    print(f"⚠️ Error: {e}")