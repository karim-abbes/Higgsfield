#!/usr/bin/env python3
"""
Transition "AVANT / APRÈS" : anime le passage de la FICHE GOOGLE au SITE BUNUA
via Kling 3.0 (start_image -> end_image) sur Replicate.

Idée : start = capture de la fiche Google Business, end = capture du site bunua.com
généré pour ce même business. Kling interpole → reveal satisfaisant.
(Pas de voix ici : la voix off vient des clips avatar / du montage. generate_audio=False = moins cher.)

Usage :
    export REPLICATE_API_TOKEN="r8_..."
    export START_IMAGE="https://.../google_profile.png"   # ou chemin local
    export END_IMAGE="https://.../bunua_site.png"          # ou chemin local
    python3 scripts/generate_transition_replicate.py

⚠️ Le morph IA d'écrans d'UI peut être imparfait. Si le rendu "bave", préfère une
transition propre au montage (wipe/zoom) sur les 2 captures — voir le README.
"""
from __future__ import annotations

import os
import sys
import urllib.request

import replicate

MODEL = "kwaivgi/kling-v3-video"
START_IMAGE = os.getenv("START_IMAGE", "out/google_profile.png")
END_IMAGE = os.getenv("END_IMAGE", "out/bunua_site.png")

PROMPT = (
    "Smooth satisfying UI reveal on a vertical phone screen: a basic Google Business "
    "Profile listing transforms into a clean, professional bakery website. Subtle zoom, "
    "modern and polished, seamless transition, 9:16 phone screen, no extra text overlay."
)
OUTPUT = "out/bunua_clip_transition.mp4"


def img(path: str):
    if path.startswith("http"):
        return path
    if os.path.exists(path):
        return open(path, "rb")
    sys.exit(f"❌ Image introuvable : {path} (URL ou chemin local valide).")


def main() -> int:
    if not os.getenv("REPLICATE_API_TOKEN"):
        print("❌ Manque REPLICATE_API_TOKEN.")
        return 1

    print("🎬 Transition avant/après (fiche Google → site bunua)…")
    last_err = None
    # Noms de champs variables selon la version : on tente les 2 conventions.
    for s_key, e_key in (("start_image", "end_image"), ("start_image_url", "end_image_url")):
        try:
            out = replicate.run(
                MODEL,
                input={
                    "prompt": PROMPT,
                    s_key: img(START_IMAGE),
                    e_key: img(END_IMAGE),
                    "duration": 5,
                    "aspect_ratio": "9:16",
                    "generate_audio": False,
                },
            )
            break
        except Exception as e:  # noqa: BLE001
            print(f"  · champs '{s_key}/{e_key}' refusés ({e})")
            last_err = e
    else:
        sys.exit(f"❌ Échec. Dernière erreur : {last_err}")

    url = str(out[0] if isinstance(out, list) else out)
    print(f"✅ Vidéo générée : {url}")
    os.makedirs("out", exist_ok=True)
    urllib.request.urlretrieve(url, OUTPUT)
    print(f"💾 Sauvegardée → {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
