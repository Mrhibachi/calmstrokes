from flask import Flask, render_template, jsonify, request
import os
from poster import build_queue, get_queued_images, load_json, save_json
from config import *

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/queue")
def get_queue():
    return jsonify(load_json(QUEUE_FILE))

@app.route("/api/rebuild-queue", methods=["POST"])
def rebuild_queue():
    data = request.json
    import config
    config.POSTS_PER_DAY = data.get("posts_per_day", POSTS_PER_DAY)
    queue = build_queue()
    return jsonify({"success": True, "total": len(queue)})

@app.route("/api/stats")
def get_stats():
    queue = load_json(QUEUE_FILE)
    posted = load_json(POSTED_FILE)
    images = get_queued_images()
    queued = [q for q in queue if q["status"] == "queued"]
    total_days = len(set(q["date"] for q in queued)) if queued else 0
    return jsonify({"total_images": len(images), "total_queued": len(queued), "total_posted": len(posted), "days_of_content": total_days, "posts_per_day": POSTS_PER_DAY})

@app.route("/api/remove-from-queue", methods=["POST"])
def remove_from_queue():
    data = request.json
    queue = load_json(QUEUE_FILE)
    queue = [q for q in queue if q["filename"] != data.get("filename")]
    save_json(QUEUE_FILE, queue)
    return jsonify({"success": True})

@app.route("/api/images")
def list_images():
    return jsonify([os.path.basename(i) for i in get_queued_images()])

if __name__ == "__main__":
    build_queue()
    print("🎮 CalmStrokes Dashboard running at http://localhost:5000")
    app.run(debug=True, port=5000)
