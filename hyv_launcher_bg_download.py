import pathlib
import re
import shutil
import subprocess

import requests
import json
import os
from datetime import datetime, UTC
from urllib.parse import urlparse

GAME_IDS = ["4ziysqXOQ8", "gopR6Cufr3", "U5hbdsT9W7"]
JSON_URL = "https://sg-hyp-api.hoyoverse.com/hyp/hyp-connect/api/getAllGameBasicInfo?launcher_id=VYTpXlbWo8&language=en-us"
SAVE_DIR = "archive"
STATE_FILE = "last_check.json"
EXCLUDED_GAME_IDS = {
    "bxPTXSET5t", "g0mMIvshDb", "uxB4MC7nzC", "wkE5P5WsIf"  # other HK 3 regions
}

os.makedirs(SAVE_DIR, exist_ok=True)

def get_games_with_videos():
    data = requests.get(JSON_URL).json()
    for game in data.get("data").get("game_info_list"):
        game_id = game.get("game").get("id")
        for background in game.get("backgrounds"):
            thumbnail = background.get("background").get("url")
            video_url = background.get("video").get("url")
            theme = background.get("theme").get("url")
            if video_url:
                yield game_id, video_url, thumbnail, theme

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

def download_video(game_id, video_url, thumbnail_url):
    print(f"game id: {game_id}")
    date_str = (get_date(video_url) or datetime.now(UTC)).strftime("%Y%m%d")
    filename = date_str + "_" + os.path.basename(video_url)
    filepath = pathlib.Path(SAVE_DIR) / game_id / filename
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    print(f"Downloading new video: {video_url} to {filepath}")
    with requests.get(video_url, stream=True) as r:
        r.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    thumbnail_extension = pathlib.Path(urlparse(thumbnail_url).path).suffix
    filepath = filepath.with_suffix(thumbnail_extension)
    print(f"Downloading thumbnail: {thumbnail_url} to {filepath}")
    with requests.get(thumbnail_url, stream=True) as r:
        r.raise_for_status()
        with open(filepath, "wb") as f:
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

        print("Video successfully converted to mp4.")
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
    video_data = list(get_games_with_videos())
    for game_id, video_url, thumbnail, theme in video_data:
        if game_id in EXCLUDED_GAME_IDS:
            continue

        last_urls = read_last_urls(game_id)

        if video_url in last_urls:
            continue

        download_video(game_id, video_url, thumbnail)

        changed = True

        if changed:
            write_last_urls(game_id, last_urls + [video_url])

    print("Check complete!")

if __name__ == "__main__":
    main()
