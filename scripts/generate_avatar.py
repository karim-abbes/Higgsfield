#!/usr/bin/env python3
"""
Génère l'avatar PRÉSENTATEUR du Makeover Reveal Show (host masculin, 9:16).

Pourquoi la CLI et pas le SDK : sur ce compte, `higgsfield_client.subscribe()`
renvoie "Model not found" pour TOUS les modèles (court ou format long), alors que
la CLI `higgsfield` fonctionne (cf. `higgsfield model list`). On pilote donc la CLI.

Usage:
    higgsfield auth login        # une fois (la CLI doit être authentifiée)
    python3 scripts/generate_avatar.py
    # modèle au choix : --model nano_banana_2 | seedream_v4_5 | flux_2 …

Noms de modèles = ceux de `higgsfield model list` (noms courts).
"""
from __future__ import annotations  # compat type hints sur Python 3.9 (Mac)

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request

# --- Prompt avatar : PRÉSENTATEUR récurrent (host énergique masculin) ---
AVATAR_PROMPT = (
    "Vertical 9:16 UGC selfie video still, authentic iPhone front-camera look. A "
    "charismatic, energetic 30-year-old American man holding the phone at arm's length, "
    "filming himself mid-sentence. Confident genuine smile, looking straight into the "
    "lens, expressive. Casual modern style (plain t-shirt or hoodie). Realistic skin "
    "texture and pores, natural daylight, candid and real, slight handheld feel, no "
    "studio polish. Clean simple modern interior, softly blurred. Shallow depth of field."
)

# Noms courts (cf. `higgsfield model list`), photoréalistes, essayés dans l'ordre.
CANDIDATE_MODELS = ["nano_banana_2", "seedream_v4_5", "flux_2"]

OUTPUT = "out/images/avatar.png"
IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")


def find_image_url(text: str):
    """Cherche l'URL de l'image dans la sortie CLI : JSON d'abord, sinon regex.
    Préfère une URL qui ressemble à une image, sinon la 1ère URL http trouvée."""
    candidates: list[str] = []

    def walk(o):
        if isinstance(o, str) and o.startswith("http"):
            candidates.append(o)
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    try:
        walk(json.loads(text))
    except Exception:  # noqa: BLE001 — sortie non-JSON → regex
        candidates = re.findall(r'https?://[^\s"\'<>]+', text)

    if not candidates:
        return None
    for u in candidates:
        if any(ext in u.lower() for ext in IMG_EXT):
            return u
    return candidates[0]


def generate(model: str) -> str | None:
    cmd = [
        "higgsfield", "generate", "create", model,
        "--prompt", AVATAR_PROMPT,
        "--aspect_ratio", "9:16",
        "--resolution", "2k",
        "--wait", "--json",
    ]
    print(f"→ Modèle : {model}")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    except FileNotFoundError:
        sys.exit("❌ CLI 'higgsfield' introuvable dans le PATH. Installe-la / ouvre un shell où elle est dispo.")
    except subprocess.TimeoutExpired:
        print("  ⚠️ timeout (>15min)")
        return None

    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if proc.returncode != 0:
        print(f"  ✗ échec (code {proc.returncode}) : {out.strip()[:200]}")
        return None

    url = find_image_url(out)
    if not url:
        print(f"  ⚠️ pas d'URL dans la sortie : {out.strip()[:200]}")
        return None
    return url


def main() -> int:
    ap = argparse.ArgumentParser(description="Génère l'avatar présentateur via la CLI Higgsfield.")
    ap.add_argument("--model", help="Force un modèle (sinon essaie la liste par défaut)")
    ap.add_argument("--out", default=OUTPUT, help=f"Chemin de sortie (défaut {OUTPUT})")
    args = ap.parse_args()

    print("🎨 Génération de l'avatar PRÉSENTATEUR (host masculin, 9:16)…\n")
    models = [args.model] if args.model else CANDIDATE_MODELS
    for model in models:
        url = generate(model)
        if not url:
            print()
            continue
        print(f"✅ Image générée : {url}")
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        urllib.request.urlretrieve(url, args.out)
        print(f"💾 Sauvegardée → {args.out}")
        print("\n➡️ Étape suivante : test Wan S2V (avatar + un MP3 TTS → avatar parlant).")
        return 0

    print("❌ Aucun modèle n'a fonctionné.")
    print("👉 Vérifie que la CLI est authentifiée (`higgsfield auth login`) et teste à la main :")
    print('   higgsfield generate create nano_banana_2 --prompt "test" --aspect_ratio 9:16 --wait')
    return 1


if __name__ == "__main__":
    sys.exit(main())
