#!/usr/bin/env python3
"""
Génère l'avatar UGC Bunua (boulangère, 9:16) via le SDK officiel Higgsfield.

Usage:
    pip install -r scripts/requirements.txt
    export HF_KEY="your-api-key:your-api-secret"   # voir .env.example
    python scripts/generate_avatar.py

Le prompt vient de brief/higgsfield-prompts.md (Étape A — BOULANGERIE).
"""
import os
import sys
import urllib.request

import higgsfield_client

# --- Prompt avatar (Étape A du brief) ---
AVATAR_PROMPT = (
    "Vertical 9:16 UGC selfie photo, authentic iPhone front-camera look. A friendly "
    "30-year-old female bakery owner holding the phone at arm's length, filming herself "
    "inside a warm artisan bakery. Soft morning window light, slight handheld feel, "
    "genuine relaxed smile, looking into the lens. Wearing a flour-dusted apron over a "
    "simple top. Realistic skin texture and pores, no studio polish, candid and real. "
    "Background: pastry display case with bread and croissants, wooden counter, softly "
    "blurred. Shallow depth of field."
)

# Modèle text-to-image (format: provider/model/version/task-type)
MODEL = "bytedance/seedream/v4/text-to-image"
OUTPUT = "out/bunua_avatar_bakery.png"


def main() -> int:
    if not (os.getenv("HF_KEY") or (os.getenv("HF_API_KEY") and os.getenv("HF_API_SECRET"))):
        print("❌ Manque les identifiants. Exporte HF_KEY=\"key:secret\" (voir .env.example).")
        return 1

    print("🎨 Génération de l'avatar boulangerie (9:16)…")
    result = higgsfield_client.subscribe(
        MODEL,
        arguments={
            "prompt": AVATAR_PROMPT,
            "resolution": "2K",
            "aspect_ratio": "9:16",
            "camera_fixed": False,
        },
    )

    url = result["images"][0]["url"]
    print(f"✅ Image générée : {url}")

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    urllib.request.urlretrieve(url, OUTPUT)
    print(f"💾 Sauvegardée → {OUTPUT}")
    print("\n➡️ Étape suivante : faire parler cet avatar via Speak (voix off Étape B du brief).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
