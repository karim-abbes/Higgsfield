#!/usr/bin/env python3
"""
TEST du modèle open-source Wan 2.2 S2V (Speech-to-Video) via fal.ai.
Avatar (image) + audio → avatar qui parle, lip-sync piloté par TON audio.

But : juger la qualité de Wan 2.2 (candidat pour le futur pipeline local sur 4090)
AVANT d'investir dans le setup ComfyUI. Bonus : voix 100% contrôlée (ton audio).

Modèle : fal-ai/wan/v2.2-14b/speech-to-video
Prix    : ~$0.15/s en 580p, ~$0.20/s en 720p.

Usage :
    export FAL_KEY="..."
    export AVATAR="out/images/avatar.png"            # image de l'avatar
    export AUDIO="out/voice/voice_sample.wav"        # audio qui pilote le lip-sync
    python3 scripts/test_wan_s2v_fal.py

Si pas d'AUDIO sous la main, réutilise l'échantillon de voix qu'on a déjà
(out/voice/voice_sample.wav = hook+CTA concaténés).
"""
from __future__ import annotations

import os
import sys
import time
import urllib.request

import fal_client

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_google_card import load_dotenv  # noqa: E402

MODEL = "fal-ai/wan/v2.2-14b/speech-to-video"
AVATAR = os.getenv("AVATAR", "out/images/avatar.png")
AUDIO = os.getenv("AUDIO", "out/voice/voice_sample.wav")
RESOLUTION = os.getenv("RESOLUTION", "580p")  # "580p" (cheap) ou "720p"
# L'endpoint exige un prompt (description de la scène/action) en plus image+audio.
PROMPT = os.getenv("PROMPT", (
    "A charismatic young man talks directly to the camera, natural lip-sync, "
    "expressive face, subtle head movements and hand gestures, energetic and "
    "friendly, vertical 9:16 selfie video."
))

OUTPUT = f"out/archive/wan_s2v_test_{time.strftime('%Y%m%d_%H%M%S')}.mp4"


def first_url(result, *keys):
    if not isinstance(result, dict):
        return None
    for k in keys:
        v = result.get(k)
        if isinstance(v, str) and v.startswith("http"):
            return v
        if isinstance(v, dict) and isinstance(v.get("url"), str):
            return v["url"]
    return None


def upload(path: str) -> str:
    if path.startswith("http"):
        return path
    if not os.path.exists(path):
        sys.exit(f"❌ Fichier introuvable : {path}")
    print(f"  ⬆️  upload {path}…")
    return fal_client.upload_file(path)


def main() -> int:
    load_dotenv()
    if not os.getenv("FAL_KEY"):
        print("❌ Manque FAL_KEY (env ou .env).")
        return 1

    start = time.time()
    print(f"🧪 Test Wan 2.2 S2V ({RESOLUTION}) — avatar + audio → parlant…")
    image_url = upload(AVATAR)
    audio_url = upload(AUDIO)

    result = fal_client.subscribe(
        MODEL,
        arguments={
            "image_url": image_url,
            "audio_url": audio_url,
            "prompt": PROMPT,
            "resolution": RESOLUTION,
        },
        with_logs=True,
        on_queue_update=lambda u: print(f"  · {time.time()-start:5.1f}s — {getattr(u, 'status', u)}"),
    )

    video_url = first_url(result, "video", "url", "output")
    if not video_url:
        print("⚠️ Réponse :", str(result)[:400])
        return 2

    print(f"✅ {time.time()-start:.1f}s — {video_url}")
    os.makedirs("out/archive", exist_ok=True)
    urllib.request.urlretrieve(video_url, OUTPUT)
    print(f"💾 {OUTPUT}")
    print("\n👀 Compare avec un clip Kling (out/clips/hook.mp4) pour juger la qualité.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
