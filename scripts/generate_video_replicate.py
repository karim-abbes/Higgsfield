#!/usr/bin/env python3
"""
Génère le clip UGC parlant (Kling 3.0, audio natif) via REPLICATE,
en réutilisant l'avatar Bunua (image -> vidéo).

Pourquoi Replicate : paiement à l'usage, pas de mur "Pro plan" comme Veo sur
Higgsfield. Modèle : kwaivgi/kling-v3-video (~$0.14/s avec audio).

Usage :
    pip3 install -r scripts/requirements.txt
    export REPLICATE_API_TOKEN="r8_..."         # depuis replicate.com/account
    # avatar : soit une URL publique, soit un fichier local
    export AVATAR="https://d8j0ntlcm91z4.cloudfront.net/.../hf_....png"
    python3 scripts/generate_video_replicate.py

Change LINE pour générer chaque beat (Hook par défaut). Voir brief/higgsfield-prompts.md.
"""
from __future__ import annotations

import os
import sys
import urllib.request

import replicate

MODEL = "kwaivgi/kling-v3-video"

# Avatar généré à l'étape image (URL publique OU chemin local).
AVATAR = os.getenv("AVATAR", "out/bunua_avatar_bakery.png")

# Réplique du beat courant (Hook par défaut).
LINE = "POV: you run a local business... but you still don't have a website."

PROMPT = (
    "9:16 vertical selfie UGC video. The same female bakery owner from the image holds "
    "her phone at arm's length, walking slowly through her warm bakery, talking directly "
    "to camera with friendly, slightly excited energy. Handheld natural motion. "
    f"She says: '{LINE}' "
    "Authentic creator vibe, natural lighting, real human voice, no on-screen text, no music."
)

OUTPUT = "out/bunua_clip_hook.mp4"


def image_input():
    """Replicate accepte une URL (str) ou un fichier uploadé."""
    if AVATAR.startswith("http"):
        return AVATAR
    if os.path.exists(AVATAR):
        return open(AVATAR, "rb")
    sys.exit(f"❌ Avatar introuvable : {AVATAR} (mets une URL ou un chemin local valide).")


def run(image_param: str):
    return replicate.run(
        MODEL,
        input={
            "prompt": PROMPT,
            image_param: image_input(),
            "duration": 5,
            "aspect_ratio": "9:16",
            "generate_audio": True,
        },
    )


def main() -> int:
    if not os.getenv("REPLICATE_API_TOKEN"):
        print("❌ Manque REPLICATE_API_TOKEN (replicate.com/account/api-tokens).")
        return 1

    print("🎬 Génération du clip Hook (Kling 3.0 + audio) via Replicate…")
    # Le nom du champ image varie selon les versions : on tente start_image puis image.
    last_err = None
    for image_param in ("start_image", "image"):
        try:
            out = run(image_param)
            break
        except Exception as e:  # noqa: BLE001
            print(f"  · champ '{image_param}' refusé ({e})")
            last_err = e
    else:
        print(f"❌ Échec. Dernière erreur : {last_err}")
        print("👉 Vérifie le nom exact du champ image sur replicate.com/kwaivgi/kling-v3-video")
        return 1

    url = str(out[0] if isinstance(out, list) else out)
    print(f"✅ Vidéo générée : {url}")

    os.makedirs("out", exist_ok=True)
    urllib.request.urlretrieve(url, OUTPUT)
    print(f"💾 Sauvegardée → {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
