"""Generate memes for the eval blog via Imgflip API."""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.environ["IMAGEFLIP_USERNAME"]
PASSWORD = os.environ["IMAGEFLIP_PASSWORD"]
API_URL = "https://api.imgflip.com/caption_image"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

MEMES = [
    {
        "filename": "meme-drake-vibes-vs-metrics.png",
        "template_id": "181913649",
        "boxes": [
            {"text": "Chatting with your agent 3 times and shipping"},
            {"text": "One command, a score, and the confidence to ship"},
        ],
    },
    {
        "filename": "meme-grus-plan.png",
        "template_id": "131940431",
        "boxes": [
            {"text": "Change the prompt"},
            {"text": "Chat with the agent a few times"},
            {"text": "Users report broken orders a week later"},
            {"text": "Users report broken orders a week later"},
        ],
    },
    {
        "filename": "meme-is-this-a-breakfast-item.png",
        "template_id": "100777631",
        "boxes": [
            {"text": "Drive-thru agent"},
            {"text": "Big Mac"},
            {"text": "Is this a breakfast menu item?"},
        ],
    },
]


def generate_meme(meme: dict) -> str:
    data = {
        "template_id": meme["template_id"],
        "username": USERNAME,
        "password": PASSWORD,
    }
    for i, box in enumerate(meme["boxes"]):
        data[f"boxes[{i}][text]"] = box["text"]

    resp = requests.post(API_URL, data=data)
    result = resp.json()
    if not result["success"]:
        print(f"FAILED {meme['filename']}: {result.get('error_message', result)}")
        return ""

    img_url = result["data"]["url"]
    img_resp = requests.get(img_url)
    out_path = os.path.join(OUT_DIR, meme["filename"])
    with open(out_path, "wb") as f:
        f.write(img_resp.content)
    print(f"OK {meme['filename']} -> {out_path}")
    return out_path


if __name__ == "__main__":
    for m in MEMES:
        generate_meme(m)
    print("\nDone!")
