#!/usr/bin/env python3
"""
Multi-shot Kling 3.0 (3 plans en 1 seule génération, voix unique) via Replicate.
Plans :
  1) Avatar boulangère 2s (intro parlée)
  2) Capture fiche Google 3s (continuité voix)
  3) Capture site Bunua 5s (suite + fin)

Usage :
    export REPLICATE_API_TOKEN="r8_..."
    export AVATAR_URL="https://.../bakery_v2.png"        # ou laisser l'URL CloudFront en dur
    export START_IMAGE="out/google_profile.png"
    export END_IMAGE="out/bunua_site.png"
    python3 scripts/generate_multishot_replicate.py

Si Replicate rejette `multi_prompt` (feature non exposée sur l'endpoint basique),
on bascule sur fal.ai — voir scripts/generate_multishot_fal.py.
"""
from __future__ import annotations

import os
import sys
import time
import urllib.request

import replicate

MODEL = "kwaivgi/kling-v3-video"

AVATAR = os.getenv(
    "AVATAR_URL",
    "https://d8j0ntlcm91z4.cloudfront.net/user_3Ekpw753qW7Jcpo6p0fI5hXuZui/"
    "hf_20260606_084508_4ac60231-a8d6-408a-8660-16b289156c13.png",
)
GOOGLE = os.getenv("START_IMAGE", "out/google_profile.png")
BUNUA = os.getenv("END_IMAGE", "out/bunua_site.png")

# Narration unique (continuité voix) répartie sur les 3 plans.
SHOTS = [
    {
        "index": 1,
        "duration": 2,
        "prompt": (
            "9:16 vertical UGC selfie. The bakery owner from the reference image holds her "
            "phone at arm's length, smiling at camera, friendly UGC energy. She says: "
            "'Your customers Google you every day...'"
        ),
    },
    {
        "index": 2,
        "duration": 3,
        "prompt": (
            "Cut to a 9:16 phone screen showing a basic Google Business Profile listing. "
            "Subtle zoom. Same voice continues: '...but find nothing. Just a map pin.'"
        ),
    },
    {
        "index": 3,
        "duration": 5,
        "prompt": (
            "Smooth UI reveal: the Google profile transforms into a clean professional bakery "
            "website on a phone, modern and polished. Same voice continues: 'Bunua turns your "
            "Google profile into a real website. In five minutes. No signup, no card.'"
        ),
    },
]

OUTPUT = f"out/bunua_clip_multishot_{time.strftime('%Y%m%d_%H%M%S')}.mp4"


def img(path: str):
    if path.startswith("http"):
        return path
    if os.path.exists(path):
        return open(path, "rb")
    sys.exit(f"❌ Image introuvable : {path}")


def main() -> int:
    if not os.getenv("REPLICATE_API_TOKEN"):
        print("❌ Manque REPLICATE_API_TOKEN.")
        return 1

    images = [img(AVATAR), img(GOOGLE), img(BUNUA)]
    base = {"aspect_ratio": "9:16", "generate_audio": True}

    # Plusieurs conventions de noms à essayer (le schéma exact varie selon l'endpoint).
    attempts = [
        {**base, "multi_prompt": SHOTS, "image_urls": images},
        {**base, "multi_prompt": SHOTS, "elements": images},
        {**base, "multi_prompt": SHOTS, "reference_images": images},
        # Variante : seulement multi_prompt + start_image (1ère)
        {**base, "multi_prompt": SHOTS, "start_image": images[0]},
    ]

    print("🎬 Tentative Replicate multi-shot (3 plans, voix unique)…")
    last_err = None
    for i, payload in enumerate(attempts, 1):
        keys = [k for k in payload if k not in base]
        print(f"  · essai {i} : champs {keys}")
        try:
            out = replicate.run(MODEL, input=payload)
        except Exception as e:  # noqa: BLE001
            print(f"    ✗ {e}")
            last_err = e
            continue

        url = str(out[0] if isinstance(out, list) else out)
        print(f"✅ Vidéo générée : {url}")
        os.makedirs("out", exist_ok=True)
        urllib.request.urlretrieve(url, OUTPUT)
        print(f"💾 Sauvegardée → {OUTPUT}")
        return 0

    print(f"\n❌ Replicate n'expose pas multi-shot sur ce modèle.")
    print(f"   Dernière erreur : {last_err}")
    print("👉 Bascule fal.ai : scripts/generate_multishot_fal.py")
    return 2


if __name__ == "__main__":
    sys.exit(main())
