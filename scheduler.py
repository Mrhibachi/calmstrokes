import schedule
import time
import os
from datetime import datetime
from poster import build_queue, post_image_to_facebook, load_json, save_json
from config import *

def run_scheduled_post():
    now = datetime.now().strftime("%H:%M")
    today = datetime.now().strftime("%Y-%m-%d")
    queue = load_json(QUEUE_FILE)
    for i, item in enumerate(queue):
        if item["date"] == today and item["time"] == now and item["status"] == "queued":
            image_path = item["file"]
            if os.path.exists(image_path):
                success = post_image_to_facebook(image_path)
                queue[i]["status"] = "posted" if success else "failed"
                save_json(QUEUE_FILE, queue)
            else:
                queue[i]["status"] = "missing"
                save_json(QUEUE_FILE, queue)

def start_scheduler():
    print("🎮 CalmStrokes Scheduler Started!")
    print(f"📅 Posting {POSTS_PER_DAY} times per day")
    print("Press Ctrl+C to stop.\n")
    build_queue()
    schedule.every(1).minutes.do(run_scheduled_post)
    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    start_scheduler()
