#!/usr/bin/env python3
"""
Transition PARLANTE (beats 2-3-4) via fal.ai Kling Omni Std :
start_image = fiche Google, end_image = site Bunua → Kling interpole
en respectant les VRAIES captures (pixel-perfect aux extrémités).
Audio natif ON → narration générée par Kling.

~$1.26 pour 10s avec audio.

Usage :
    export FAL_KEY="..."
    export START_IMAGE="out/google_profile.png"
    export END_IMAGE="out/bunua_site.png"
    python3 scripts/generate_transition_fal.py
"""
from __future__ import annotations

import os
import sys
import time
import urllib.request

import fal_client

MODEL = "fal-ai/kling-video/o3/standard/image-to-video"
START_IMAGE = os.getenv("START_IMAGE", "out/google_profile.png")
END_IMAGE = os.getenv("END_IMAGE", "out/bunua_site.png")

NARRATION = (
    "Your customers Google you every day, but find nothing. "
    "Bunua turns your Google profile into a real website. "
    "In five minutes. No signup, no card."
)

PROMPT = (
    "9:16 vertical phone screen. Smooth satisfying UI reveal: a basic Google Business "
    "Profile listing slowly transforms into a clean, professional bakery website. "
    "Subtle zoom and modern polish, seamless transition. Hands holding the phone visible "
    "at the edges. "
    "Friendly young female creator voice-over, warm and slightly excited UGC tone, "
    f"saying: '{NARRATION}'. No background music."
)

OUTPUT = f"out/bunua_clip_transition_{time.strftime('%Y%m%d_%H%M%S')}.mp4"


def upload(path: str) -> str:
    if path.startswith("http"):
        return path
    if not os.path.exists(path):
        sys.exit(f"❌ Image introuvable : {path}")
    print(f"  ⬆️  upload {path}…")
    return fal_client.upload_file(path)


def main() -> int:
    if not os.getenv("FAL_KEY"):
        print("❌ Manque FAL_KEY.")
        return 1

    start = time.time()
    print("🎬 Transition parlante fal.ai (Google → Bunua, captures réelles)…")

    start_url = upload(START_IMAGE)
    end_url = upload(END_IMAGE)

    result = fal_client.subscribe(
        MODEL,
        arguments={
            "image_url": start_url,
            "end_image_url": end_url,
            "prompt": PROMPT,
            "duration": "10",
            "aspect_ratio": "9:16",
            "generate_audio": True,
        },
        with_logs=True,
        on_queue_update=lambda u: print(
            f"  · {time.time()-start:5.1f}s — {getattr(u, 'status', u)}"
        ),
    )

    video_url = (
        result.get("video", {}).get("url") if isinstance(result, dict) else None
    )
    if not video_url:
        print("⚠️ Réponse :", str(result)[:400])
        return 2

    print(f"✅ {time.time()-start:.1f}s — {video_url}")
    os.makedirs("out", exist_ok=True)
    urllib.request.urlretrieve(video_url, OUTPUT)
    print(f"💾 {OUTPUT}")
    print("\n👉 Copie ce fichier en `out/bunua_clip_transition.mp4` pour le montage :")
    print(f"   cp {OUTPUT} out/bunua_clip_transition.mp4")
    print("   bash scripts/assemble_video.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
