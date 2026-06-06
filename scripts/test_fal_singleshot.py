#!/usr/bin/env python3
"""
Test rapide fal.ai Kling Omni Std — SINGLE SHOT pour valider que ton compte/clé
fonctionne et que l'endpoint est réactif avant de relancer le multi-shot.

5s vidéo avec audio = ~$0.63. Beaucoup moins risqué qu'un multi-shot de 10s.

Usage :
    export FAL_KEY="..."
    python3 scripts/test_fal_singleshot.py
"""
from __future__ import annotations

import os
import sys
import time
import urllib.request

import fal_client

MODEL = "fal-ai/kling-video/o3/standard/image-to-video"
AVATAR = os.getenv(
    "AVATAR_URL",
    "https://d8j0ntlcm91z4.cloudfront.net/user_3Ekpw753qW7Jcpo6p0fI5hXuZui/"
    "hf_20260606_084508_4ac60231-a8d6-408a-8660-16b289156c13.png",
)
OUTPUT = f"out/archive/test_fal_{time.strftime('%Y%m%d_%H%M%S')}.mp4"


def main() -> int:
    if not os.getenv("FAL_KEY"):
        print("❌ Manque FAL_KEY.")
        return 1

    start = time.time()
    print("🧪 Test single-shot fal Omni Std (5s + audio)…")
    result = fal_client.subscribe(
        MODEL,
        arguments={
            "image_url": AVATAR,
            "prompt": (
                "9:16 vertical UGC selfie. The bakery owner from the image holds her phone "
                "at arm's length, smiling and saying: 'Hello from my bakery!' "
                "Authentic UGC creator energy."
            ),
            "duration": "5",
            "aspect_ratio": "9:16",
            "generate_audio": True,
        },
        with_logs=True,
        on_queue_update=lambda u: print(f"  · {time.time()-start:5.1f}s — {getattr(u, 'status', u)}"),
    )

    video_url = result.get("video", {}).get("url") if isinstance(result, dict) else None
    if not video_url:
        print("⚠️ Réponse :", str(result)[:400])
        return 2

    print(f"✅ {time.time()-start:.1f}s — {video_url}")
    os.makedirs("out/archive", exist_ok=True)
    urllib.request.urlretrieve(video_url, OUTPUT)
    print(f"💾 {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
