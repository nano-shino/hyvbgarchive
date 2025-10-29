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
    data[game_id]["checked_at"] = datetime.utcnow().isoformat()

    with open(STATE_FILE, "w") as f:
        json.dump(data, f)

def download_video(game_id, url):
    filename = os.path.join(SAVE_DIR, game_id, datetime.now(UTC).strftime("%Y%m%d") + "_" + os.path.basename(url))
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    print(f"Downloading new video: {url}")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"Saved: {filename}")

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
