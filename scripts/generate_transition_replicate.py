#!/usr/bin/env python3
"""
Transition PARLANTE qui couvre les beats 2-3-4 du brief (problème → solution → preuve).
Anime la fiche Google → site Bunua via Kling 3.0 (start/end image), avec voix off
native générée par Kling (même direction que le hook pour la continuité).

⚠️ Kling ne clone PAS la voix du hook — il en génère une nouvelle à chaque appel.
La voix sera proche (même direction de prompt) mais peut varier légèrement.

Usage :
    export REPLICATE_API_TOKEN="r8_..."
    export START_IMAGE="out/google_profile.png"
    export END_IMAGE="out/bunua_site.png"
    python3 scripts/generate_transition_replicate.py
"""
from __future__ import annotations

import os
import sys
import urllib.request

import replicate

MODEL = "kwaivgi/kling-v3-video"
START_IMAGE = os.getenv("START_IMAGE", "out/google_profile.png")
END_IMAGE = os.getenv("END_IMAGE", "out/bunua_site.png")

# Narration condensée des beats 2-3-4 (~10s).
NARRATION = (
    "Your customers Google you every day, but find nothing. "
    "Bunua turns your Google profile into a real website. "
    "In five minutes. No signup, no card."
)

PROMPT = (
    "9:16 vertical phone screen. Smooth satisfying UI reveal: a basic Google Business "
    "Profile listing slowly transforms into a clean, professional bakery website. "
    "Subtle zoom and modern polish, seamless transition. "
    "Voice-over by a friendly young female creator with authentic UGC energy, warm and "
    f"slightly excited tone, saying: '{NARRATION}'. No music."
)
OUTPUT = "out/bunua_clip_transition.mp4"


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

    print("🎬 Transition PARLANTE (Google → Bunua + narration beats 2-3-4)…")
    last_err = None
    for s_key, e_key in (("start_image", "end_image"), ("start_image_url", "end_image_url")):
        try:
            out = replicate.run(
                MODEL,
                input={
                    "prompt": PROMPT,
                    s_key: img(START_IMAGE),
                    e_key: img(END_IMAGE),
                    "duration": 10,
                    "aspect_ratio": "9:16",
                    "generate_audio": True,
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
