import requests
import json
import os
import shutil
from datetime import datetime
from config import *

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
