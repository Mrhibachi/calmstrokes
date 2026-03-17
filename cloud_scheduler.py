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
        # Running on Railway - use environment variable
        sa_info = json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(
            sa_info, scopes=SCOPES
        )
    else:
        # Running locally - use file
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
def delete_from_drive(file_id):
    try:
        service = get_drive_service()
        service.files().update(fileId=file_id, body={"trashed": True}).execute()
        print(f"🗑️ Deleted from Drive: {file_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to delete from Drive: {e}")
        return False

def download_file_from_drive(file_id, filename):
    """Download a single file from Drive."""
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    output_path = os.path.join(DOWNLOAD_FOLDER, filename)
    url = f"https://drive.google.com/uc?id={file_id}"
    gdown.download(url, output_path, quiet=True)
    return output_path

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return []

def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

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
        posted = load_json(POSTED_FILE)
        posted.append({
            "file": os.path.basename(image_path),
            "post_id": result["id"],
            "posted_at": datetime.now().isoformat()
        })
        save_json(POSTED_FILE, posted)
        try:
            os.remove(image_path)
        except:
            pass
        return True
    else:
        print(f"❌ Failed: {result}")
        return False

def run_post():
    """Get next image from Drive, post it, then delete it from Drive."""
    print(f"🎮 Checking for images to post at {datetime.now().strftime('%H:%M')}")

    try:
        files = get_drive_files()

        if not files:
            print("📭 No images left in Drive folder")
            return

        posted = load_json(POSTED_FILE)
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

        success = post_image_to_facebook(image_path)

        if success:
            delete_from_drive(next_file["id"])

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
