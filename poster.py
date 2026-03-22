import requests
import json
import os
import shutil
from datetime import datetime
from config import *
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaIoBaseDownload
import io
SCOPES = ['https://www.googleapis.com/auth/drive']

import os
import json

creds_json = os.environ.get("GOOGLE_CREDS")

creds_dict = json.loads(creds_json)

creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

FB_FOLDER_ID = "1_1AZn3XjrrqrM_dNfS5yKmb0DqHHWxu9"
POSTED_FOLDER_ID = "1U7Fp77ZKy3Y_Kgs9DJjUx0sLeIPpO38U"
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
        log_posted(image_path, result["id"], caption)
        move_to_posted(image_path)
        return True
    else:
        print(f"❌ Failed: {result}")
        return False

def log_posted(image_path, post_id, caption):
    posted = load_json(POSTED_FILE)
    posted.append({"file": os.path.basename(image_path), "post_id": post_id, "caption": caption, "posted_at": datetime.now().isoformat()})
    save_json(POSTED_FILE, posted)

def move_to_posted(image_path):
    shutil.move(image_path, os.path.join(POSTED_FOLDER, os.path.basename(image_path)))

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return []

def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def get_queued_images():
    supported = (".jpg", ".jpeg", ".png", ".gif", ".webp")
    if os.path.exists(IMAGES_FOLDER):
        return [os.path.join(IMAGES_FOLDER, f) for f in sorted(os.listdir(IMAGES_FOLDER)) if f.lower().endswith(supported)]
    return []

def build_queue():
    from datetime import date, timedelta
    images = get_queued_images()
    queue = []
    current_date = date.today()
    times = POST_TIMES[:POSTS_PER_DAY]
    day = 0
    img_index = 0
    while img_index < len(images):
        post_date = current_date + timedelta(days=day)
        for time_slot in times:
            if img_index >= len(images):
                break
            queue.append({"file": images[img_index], "filename": os.path.basename(images[img_index]), "date": post_date.isoformat(), "time": time_slot, "status": "queued"})
            img_index += 1
        day += 1
    save_json(QUEUE_FILE, queue)
    return queue

def build_queue(image_folder="images"):
    queue = []

    if not os.path.exists(image_folder):
        print("⚠️ Image folder not found")
        return queue

    for file in os.listdir(image_folder):
        if file.lower().endswith((".jpg", ".jpeg", ".png")):
            queue.append({
                "filename": file,
                "path": os.path.join(image_folder, file)
            })

    print(f"✅ Queue built with {len(queue)} images")
    return queue
def move_to_posted(image_path):
    posted_folder = "posted"

    if not os.path.exists(posted_folder):
        os.makedirs(posted_folder)

    filename = os.path.basename(image_path)
    new_path = os.path.join(posted_folder, filename)

    shutil.move(image_path, new_path)

    print(f"📦 Moved to posted: {filename}")
if __name__ == "__main__":
    print("🔥 Running manual post test...")

    image_folder = "images"
    images = os.listdir(image_folder)

    if images:
        image_path = os.path.join(image_folder, images[0])
        post_image_to_facebook(image_path)
    else:
        print("❌ No images found")
def get_drive_images():
    results = drive_service.files().list(
        q=f"'{FB_FOLDER_ID}' in parents and mimeType contains 'image/'",
        fields="files(id, name)"
    ).execute()

    return results.get('files', [])
def download_image(file_id, filename):
    request = drive_service.files().get_media(fileId=file_id)
    fh = open(f"images/{filename}", 'wb')

    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()

    fh.close()
def move_drive_file(file_id):
    file = drive_service.files().get(fileId=file_id, fields='parents').execute()
    previous_parents = ",".join(file.get('parents'))

    drive_service.files().update(
        fileId=file_id,
        addParents=POSTED_FOLDER_ID,
        removeParents=previous_parents
    ).execute()
def run_drive_post():
    images = get_drive_images()

    if not images:
        print("❌ No images in Drive")
        return

    image = images[0]
    file_id = image['id']
    filename = image['name']

    print(f"📥 Downloading {filename}")
    download_image(file_id, filename)

    image_path = f"images/{filename}"

    result = post_image_to_facebook(image_path)

    if result:
        move_drive_file(file_id)
        os.remove(image_path)
        print(f"📦 Moved in Drive + cleaned local: {filename}")

