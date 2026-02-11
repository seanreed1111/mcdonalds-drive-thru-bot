"""Generate memes via imgflip API and download as PNGs."""

import requests
import os

USERNAME = "SeanReed3"
PASSWORD = "alphaBeta1"
API_URL = "https://api.imgflip.com/caption_image"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

MEMES = [
    {
        "filename": "meme-aj-jake-paul.png",
        "template_id": "630649014",
        "boxes": [
            {
                "text": "My 12-node state machine with explicit routing for every conversation phase"
            },
            {"text": "The 4-node orchestrator that actually shipped"},
        ],
    },
    {
        "filename": "meme-getting-ridiculous.png",
        "template_id": "626206670",
        "boxes": [
            {"text": "conversation_phase"},
            {"text": "last_intent"},
            {"text": "pending_items"},
            {"text": "confirmation_status"},
        ],
    },
    {
        "filename": "meme-turn-lights-off.png",
        "template_id": "630503265",
        "boxes": [
            {"text": "Clean chatbot responses, everything works great"},
            {
                "text": "Why did it add three McFlurries when the customer asked for coffee?"
            },
        ],
    },
    {
        "filename": "meme-same-picture.png",
        "template_id": "180190441",
        "boxes": [
            {"text": "Intent classification, phase routing, multi-intent parsing"},
            {"text": "What LLMs do naturally with conversation history"},
            {"text": "They're the same picture"},
        ],
    },
    {
        "filename": "meme-success-kid.png",
        "template_id": "61544",
        "boxes": [
            {"text": "Threw away my entire 12-node state machine design"},
            {"text": "Replaced it with 4 nodes that handle everything better"},
        ],
    },
    {
        "filename": "meme-bike-fall.png",
        "template_id": "134797956",
        "boxes": [
            {"text": "Me, designing a drive-thru chatbot"},
            {"text": "Adding a 12th node to my state machine"},
            {"text": "Why is this so hard to build?"},
        ],
    },
    {
        "filename": "meme-left-exit.png",
        "template_id": "124822590",
        "boxes": [
            {"text": "Build the 12-node state machine like a responsible engineer"},
            {"text": "4 nodes and let the LLM figure it out"},
            {"text": "Me"},
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
