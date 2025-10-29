import requests
import json
import os
from datetime import datetime

JSON_URL = "https://sg-hyp-api.hoyoverse.com/hyp/hyp-connect/api/getAllGameBasicInfo?launcher_id=VYTpXlbWo8&language=en-us&game_id=gopR6Cufr3"  # ← replace this with your JSON URL
SAVE_DIR = "downloads"
STATE_FILE = "last_video.json"

os.makedirs(SAVE_DIR, exist_ok=True)

def get_video_urls():
    data = requests.get(JSON_URL).json()
    for game in data.get("data").get("game_info_list"):
        for background in game.get("backgrounds"):
            video_url = background.get("video").get("url")
            if video_url:
                yield video_url

def read_last_urls():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f).get("video_urls")
    return []

def write_last_urls(urls):
    with open(STATE_FILE, "w") as f:
        json.dump({"video_urls": urls, "timestamp": datetime.utcnow().isoformat()}, f)

def download_video(url):
    filename = os.path.join(SAVE_DIR, os.path.basename(url))
    print(f"Downloading new video: {url}")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"Saved: {filename}")

def main():
    current_urls = list(get_video_urls())
    last_urls = read_last_urls()

    for url in current_urls:
        if url not in last_urls:
            download_video(url)

    write_last_urls(current_urls + last_urls)
    print("Check complete!")

if __name__ == "__main__":
    main()
