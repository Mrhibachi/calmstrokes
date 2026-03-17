import os
import json
import time
import schedule
import requests
import gdown
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account
from config import *

GDRIVE_FOLDER_ID = "1_1AZn3XjrrqrM_dNfS5yKmb0DqHHWxu9"
DOWNLOAD_FOLDER = "images"
SCOPES = ["https://www.googleapis.com/auth/drive"]

def get_drive_service():
    """Get authenticated Google Drive service from env var or file."""
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if sa_json:
        sa_info = json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(
            sa_info, scopes=SCOPES
        )
    else:
        creds = service_account.Credentials.from_service_account_file(
            "service_account.json", scopes=SCOPES
        )
    return build("drive", "v3", credentials=creds)

def get_drive_files():
    """Get list of image files in Drive folder."""
    service = get_drive_service()
    results = service.files().list(
        q=f"'{GDRIVE_FOLDER_ID}' in parents and trashed=false",
        fields="files(id, name)",
        orderBy="name"
    ).execute()
    return results.get("files", [])

def download_file_from_drive(file_id, filename):
    """Download a single file from Drive."""
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    output_path = os.path.join(DOWNLOAD_FOLDER, filename)
    url = f"https://drive.google.com/uc?id={file_id}"
    gdown.download(url, output_path, quiet=True)
    return output_path

def load_posted():
    """Load posted history from env var (Railway) or local file."""
    raw_history = os.environ.get("POSTED_HISTORY", "[]")
    try:
        env_history = json.loads(raw_history)
        if isinstance(env_history, list):
            return env_history
        print("⚠️ POSTED_HISTORY is not a list, ignoring it")
    except json.JSONDecodeError:
        print("⚠️ Invalid POSTED_HISTORY, ignoring it")

    # Fall back to local file
    if os.path.exists(POSTED_FILE):
        try:
            with open(POSTED_FILE, "r") as f:
                file_history = json.load(f)
            if isinstance(file_history, list):
                return file_history
            print("⚠️ Local posted history is not a list, resetting")
        except (json.JSONDecodeError, OSError):
            print("⚠️ Local posted history is invalid, resetting")

    return []

def save_posted(posted):
    """Save posted history to local file."""
    with open(POSTED_FILE, "w") as f:
        json.dump(posted, f, indent=2)
    # Print updated history so Railway logs show it
    print(f"📝 Posted history updated: {len(posted)} total posts")

def post_image_to_facebook(image_path, caption=None):
    if caption is None:
        caption = DEFAULT_CAPTION
    url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/photos"
    with open(image_path, "rb") as image_file:
        response = requests.post(
            url,
            data={"caption": caption, "access_token": PAGE_ACCESS_TOKEN},
            files={"source": image_file}
        )
    result = response.json()
    if "id" in result:
        print(f"✅ Posted: {os.path.basename(image_path)} at {datetime.now().strftime('%H:%M:%S')}")
        posted = load_posted()
        posted.append({
            "file": os.path.basename(image_path),
            "post_id": result["id"],
            "posted_at": datetime.now().isoformat()
        })
        save_posted(posted)
        try:
            os.remove(image_path)
        except:
            pass
        return True
    else:
        print(f"❌ Failed: {result}")
        return False

def run_post():
    """Get next image from Drive, post it."""
    print(f"🎮 Checking for images to post at {datetime.now().strftime('%H:%M')}")

    try:
        files = get_drive_files()

        if not files:
            print("📭 No images left in Drive folder")
            return

        posted = load_posted()
        posted_files = [p["file"] for p in posted]

        next_file = None
        for f in files:
            if f["name"] not in posted_files:
                next_file = f
                break

        if not next_file:
            print("📭 All images have been posted")
            return

        print(f"📥 Downloading {next_file['name']}...")
        image_path = download_file_from_drive(next_file["id"], next_file["name"])

        if not os.path.exists(image_path):
            print("❌ Download failed")
            return

        post_image_to_facebook(image_path)

    except Exception as e:
        print(f"❌ Error in run_post: {e}")

def start():
    print("🎮 CalmStrokes Cloud Scheduler Started!")
    print(f"📅 Posting {POSTS_PER_DAY} times per day")

    times = POST_TIMES[:POSTS_PER_DAY]
    for t in times:
        schedule.every().day.at(t).do(run_post)

    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    start()
