#!/usr/bin/env python3
"""
Génère l'avatar UGC Bunua (boulangère, 9:16) via le SDK officiel Higgsfield.

Usage:
    pip3 install -r scripts/requirements.txt
    export HF_KEY="your-api-key:your-api-secret"   # voir .env.example
    python3 scripts/generate_avatar.py

Le prompt vient de brief/higgsfield-prompts.md (Étape A — BOULANGERIE).

Note: les identifiants de modèles viennent du catalogue officiel
(https://github.com/higgsfield-ai/cli/blob/main/MODELS.md).
Le script essaie plusieurs modèles connus et garde le premier qui répond.
"""
from __future__ import annotations  # compat type hints sur Python 3.9 (Mac)

import json
import os
import sys
import urllib.request

import higgsfield_client


def load_dotenv() -> None:
    """Charge .env (racine du repo) dans l'environnement, sans écraser l'existant."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, ".env")
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


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

# Identifiants du catalogue officiel CLI (text-to-image), du + adapté au + photoréaliste.
# On essaie dans l'ordre ; le 1er modèle qui accepte la requête est utilisé.
CANDIDATE_MODELS = [
    "nano_banana_2",       # Nano Banana Pro — photoréaliste, 2 cr/image
    "text2image_soul_v2",  # Higgsfield Soul V2 — UGC réaliste, très bon marché
    "seedream_v4_5",       # Seedream 4.5
]

OUTPUT = "out/images/avatar.png"


def extract_url(result) -> str | None:
    """Le schéma de sortie varie selon le modèle : on cherche la 1ère URL d'image."""
    if isinstance(result, dict):
        if "images" in result and result["images"]:
            return result["images"][0].get("url")
        for key in ("image", "url", "output"):
            v = result.get(key)
            if isinstance(v, str) and v.startswith("http"):
                return v
            if isinstance(v, dict) and isinstance(v.get("url"), str):
                return v["url"]
    return None


def main() -> int:
    load_dotenv()
    if not (os.getenv("HF_KEY") or (os.getenv("HF_API_KEY") and os.getenv("HF_API_SECRET"))):
        print('❌ Manque les identifiants. Exporte HF_KEY="key:secret" (voir .env.example).')
        return 1

    print("🎨 Génération de l'avatar boulangerie (9:16)…\n")
    last_err = None
    for model in CANDIDATE_MODELS:
        print(f"→ Essai du modèle : {model}")
        try:
            result = higgsfield_client.subscribe(
                model,
                arguments={
                    "prompt": AVATAR_PROMPT,
                    "aspect_ratio": "9:16",
                    "resolution": "2k",
                },
            )
        except Exception as e:  # noqa: BLE001 — on veut juste passer au modèle suivant
            print(f"  ✗ {model} indisponible ({e})\n")
            last_err = e
            continue

        print(f"  ✓ Réponse reçue de {model}")
        url = extract_url(result)
        if not url:
            print("  ⚠️ Pas d'URL trouvée dans la réponse. Structure brute :")
            print(json.dumps(result, indent=2, default=str)[:1500])
            return 2

        print(f"✅ Image générée : {url}")
        os.makedirs("out/images", exist_ok=True)
        urllib.request.urlretrieve(url, OUTPUT)
        print(f"💾 Sauvegardée → {OUTPUT}")
        print("\n➡️ Étape suivante : faire parler cet avatar via Speak (voix off Étape B du brief).")
        return 0

    print(f"\n❌ Aucun modèle n'a fonctionné. Dernière erreur : {last_err}")
    print("👉 Vérifie les noms dispo avec le CLI : `higgsfield model list`")
    return 1


if __name__ == "__main__":
    sys.exit(main())
