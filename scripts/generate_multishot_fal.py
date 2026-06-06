#!/usr/bin/env python3
"""
Multi-shot Kling 3 Omni (3 plans, voix unique) via FAL.AI.
~$0.126/s avec audio (~$1.26 pour 10s) — moins cher que Replicate.

Prérequis :
    1) Compte fal.ai → https://fal.ai/dashboard/keys
    2) pip3 install fal-client
    3) export FAL_KEY="fal_..."

Variables :
    export AVATAR_URL="https://...png"             # avatar boulangère
    export START_IMAGE="out/google_profile.png"    # fiche Google
    export END_IMAGE="out/bunua_site.png"          # site Bunua

Lancement :
    python3 scripts/generate_multishot_fal.py
"""
from __future__ import annotations

import os
import sys
import time
import urllib.request

import fal_client

# Kling Omni (multi-shot natif + audio).
MODEL = "fal-ai/kling-video/o3/standard/image-to-video"

AVATAR = os.getenv(
    "AVATAR_URL",
    "https://d8j0ntlcm91z4.cloudfront.net/user_3Ekpw753qW7Jcpo6p0fI5hXuZui/"
    "hf_20260606_084508_4ac60231-a8d6-408a-8660-16b289156c13.png",
)
GOOGLE = os.getenv("START_IMAGE", "out/google_profile.png")
BUNUA = os.getenv("END_IMAGE", "out/bunua_site.png")

SHOTS = [
    {
        "index": 1,
        "duration": "2",
        "prompt": (
            "Take @Element1 as the subject. 9:16 vertical UGC selfie of the bakery owner, "
            "holding her phone at arm's length inside her warm bakery, smiling at camera, "
            "friendly UGC creator energy. She says: 'Your customers Google you every day...'"
        ),
    },
    {
        "index": 2,
        "duration": "3",
        "prompt": (
            "Hard cut to @Image1: a 9:16 phone screen showing a basic Google Business Profile "
            "listing for a bakery, subtle zoom. Same voice continues: "
            "'...but find nothing. Just a map pin.'"
        ),
    },
    {
        "index": 3,
        "duration": "5",
        "prompt": (
            "Smooth UI reveal: @Image1 morphs into @Image2, a clean professional bakery website "
            "on a phone screen. Same voice: 'Bunua turns your Google profile into a real "
            "website. In five minutes. No signup, no card.'"
        ),
    },
]

OUTPUT = f"out/bunua_clip_multishot_{time.strftime('%Y%m%d_%H%M%S')}.mp4"


def upload(path_or_url: str) -> str:
    """fal-client veut une URL. Upload les fichiers locaux."""
    if path_or_url.startswith("http"):
        return path_or_url
    if not os.path.exists(path_or_url):
        sys.exit(f"❌ Image introuvable : {path_or_url}")
    print(f"  ⬆️  upload {path_or_url}…")
    return fal_client.upload_file(path_or_url)


def main() -> int:
    if not os.getenv("FAL_KEY"):
        print("❌ Manque FAL_KEY (https://fal.ai/dashboard/keys).")
        return 1

    print("🎬 Multi-shot Kling Omni (3 plans, voix unique) via fal.ai…")
    avatar_url = upload(AVATAR)
    google_url = upload(GOOGLE)   # @Image1 dans les prompts
    bunua_url = upload(BUNUA)     # @Image2 dans les prompts

    result = fal_client.subscribe(
        MODEL,
        arguments={
            # Image de départ obligatoire (= 1ère frame de la vidéo).
            "image_url": avatar_url,
            # Avatar comme "Element1" → continuité du personnage entre les plans (@Element1).
            "elements": [{"frontal_image_url": avatar_url}],
            # Écrans Google (@Image1) puis Bunua (@Image2) en références.
            "reference_image_urls": [google_url, bunua_url],
            # Multi-shot (3 plans) + shot_type requis.
            "multi_prompt": SHOTS,
            "shot_type": "customize",
            "aspect_ratio": "9:16",
            "generate_audio": True,
        },
        with_logs=True,
        on_queue_update=lambda u: print(f"  · {getattr(u, 'status', u)}"),
    )

    # Le format de sortie fal : {"video": {"url": "..."}}
    video_url = (
        result.get("video", {}).get("url")
        if isinstance(result, dict)
        else None
    )
    if not video_url:
        print("⚠️ Réponse inattendue :", str(result)[:400])
        return 2

    print(f"✅ Vidéo générée : {video_url}")
    os.makedirs("out", exist_ok=True)
    urllib.request.urlretrieve(video_url, OUTPUT)
    print(f"💾 Sauvegardée → {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
