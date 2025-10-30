import re
import shutil
import subprocess

import requests
import json
import os
from datetime import datetime, UTC

GAME_IDS = ["4ziysqXOQ8", "gopR6Cufr3", "U5hbdsT9W7"]
JSON_URL = "https://sg-hyp-api.hoyoverse.com/hyp/hyp-connect/api/getAllGameBasicInfo?launcher_id=VYTpXlbWo8&language=en-us&game_id="
SAVE_DIR = "archive"
STATE_FILE = "last_check.json"

os.makedirs(SAVE_DIR, exist_ok=True)

def get_video_urls(game_id):
    data = requests.get(JSON_URL + game_id).json()
    for game in data.get("data").get("game_info_list"):
        for background in game.get("backgrounds"):
            video_url = background.get("video").get("url")
            if video_url:
                yield video_url

def read_last_urls(game_id):
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f).get(game_id, {}).get("video_urls", [])
    return []

def write_last_urls(game_id, urls):
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {}

    if game_id not in data:
        data[game_id] = {}

    data[game_id]["video_urls"] = urls
    data[game_id]["checked_at"] = datetime.now(UTC).isoformat()

    with open(STATE_FILE, "w") as f:
        json.dump(data, f)

def download_video(game_id, url):
    date_str = (get_date(url) or datetime.now(UTC)).strftime("%Y%m%d")
    filename = os.path.join(SAVE_DIR, game_id, date_str + "_" + os.path.basename(url))
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    print(f"Downloading new video: {url}")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    process_video(filename)
    print(f"Saved: {filename}")

def process_video(filename):
    if not filename.endswith(".webm"):
        return

    if shutil.which("ffmpeg") is None:
        print("ffmpeg not found — skipping video conversion.")
        return

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-i", filename,
                "-c:v", "libx264",
                "-profile:v", "high",
                "-level", "4.0",
                "-pix_fmt", "yuv420p",
                "-preset", "medium",
                "-crf", "23",
                "-y",
                filename.replace(".webm", ".mp4"),
            ],
            check=True
        )
        subprocess.run(
            [
                "ffmpeg",
                "-i", filename,
                "-vf", "thumbnail,scale=640:-1",
                "-vframes", "1",
                "-q:v", "2",
                "-y",
                filename.replace(".webm", ".jpg")
            ],
            check=True
        )

        print("Video successfully converted to mp4 and generated thumbnail.")
    except subprocess.CalledProcessError:
        print("ffmpeg failed to process the file.")

def get_date(url):
    pattern = r"/(\d{4})/(\d{2})/(\d{2})/"
    match = re.search(pattern, url)
    if match:
        year, month, day = map(int, match.groups())

        if 2020 <= year <= 2050:
            try:
                # Validate that it’s a real date (e.g. no Feb 30)
                date_obj = datetime(year, month, day)
                return date_obj
            except ValueError:
                pass

    return None

def main():
    for game_id in GAME_IDS:
        current_urls = list(get_video_urls(game_id))
        last_urls = read_last_urls(game_id)
        changed = False

        for url in current_urls:
            if url not in last_urls:
                download_video(game_id, url)
                changed = True

        if changed:
            write_last_urls(game_id, current_urls + last_urls)

    print("Check complete!")

if __name__ == "__main__":
    main()
