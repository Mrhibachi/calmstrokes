import os
import json
import time
import schedule
import requests
import gdown
from datetime import datetime
from config import *

GDRIVE_FOLDER_ID = "1_1AZn3XjrrqrM_dNfS5yKmb0DqHHWxu9"
DOWNLOAD_FOLDER = "images"

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return []

def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def get_drive_file_list():
    """Get list of files in Google Drive folder using Drive API."""
    posted = load_json(POSTED_FILE)
    posted_files = [p["file"] for p in posted]

    # Use gdown to list files in the folder
    url = f"https://drive.google.com/drive/folders/{GDRIVE_FOLDER_ID}"
    try:
        # Get folder contents without downloading
        files = gdown.download_folder(
            url,
            output=DOWNLOAD_FOLDER,
            quiet=True,
            use_cookies=False,
            remaining_ok=True  # Don't fail if >50 files
        )
        return files
    except Exception as e:
        print(f"Error listing folder: {e}")
        return []

def download_one_image():
    """Download just one unposted image from Drive."""
    posted = load_json(POSTED_FILE)
    posted_files = [p["file"] for p in posted]

    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

    # Check if we already have unposted images locally
    supported = (".jpg", ".jpeg", ".png", ".gif", ".webp")
    local_images = [f for f in sorted(os.listdir(DOWNLOAD_FOLDER))
                    if f.lower().endswith(supported) and f not in posted_files]

    if local_images:
        # Already have images locally, use them
        return os.path.join(DOWNLOAD_FOLDER, local_images[0])

    # Need to download more - get them in small batches
    try:
        url = f"https://drive.google.com/drive/folders/{GDRIVE_FOLDER_ID}"
        print("📥 Downloading images from Google Drive...")
        gdown.download_folder(
            url,
            output=DOWNLOAD_FOLDER,
            quiet=True,
            use_cookies=False,
            remaining_ok=True
        )
    except Exception as e:
        print(f"Error downloading from Drive: {e}")
        return None

    # Check again after download
    local_images = [f for f in sorted(os.listdir(DOWNLOAD_FOLDER))
                    if f.lower().endswith(supported) and f not in posted_files]

    if local_images:
        return os.path.join(DOWNLOAD_FOLDER, local_images[0])

    return None

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
        # Remove image after posting to save space
        try:
            os.remove(image_path)
        except:
            pass
        return True
    else:
        print(f"❌ Failed: {result}")
        return False

def run_post():
    """Download next image from Drive and post it."""
    print(f"🎮 Checking for images to post at {datetime.now().strftime('%H:%M')}")

    image_path = download_one_image()

    if image_path and os.path.exists(image_path):
        post_image_to_facebook(image_path)
    else:
        print("📭 No new images to post")

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
