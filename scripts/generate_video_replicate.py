#!/usr/bin/env python3
"""
Génère les clips UGC parlants (Kling 3.0, audio natif) via REPLICATE,
en réutilisant l'avatar Bunua (image -> vidéo).

Pourquoi Replicate : paiement à l'usage, pas de mur "Pro plan" comme Veo sur
Higgsfield. Modèle : kwaivgi/kling-v3-video (~$0.14/s avec audio).

Usage :
    pip3 install -r scripts/requirements.txt
    export REPLICATE_API_TOKEN="r8_..."         # replicate.com/account/api-tokens
    export AVATAR="https://.../avatar.png"      # URL publique OU chemin local

    python3 scripts/generate_video_replicate.py hook     # 1 beat
    python3 scripts/generate_video_replicate.py cta
    python3 scripts/generate_video_replicate.py all       # tous les beats parlants

Beats issus de brief/bunua-ugc-brief.md. Les beats "screen" (démo bunua.com) se
tournent en capture d'écran réelle + voix off, pas ici.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

import replicate

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_google_card import load_dotenv  # noqa: E402

MODEL = "kwaivgi/kling-v3-video"
AVATAR = os.getenv("AVATAR", "out/images/avatar.png")

# Répliques par défaut (fallback si pas de --script). Le texte réel d'un épisode
# vient du script JSON (render_script.py) via --script. La voix est générée
# nativement par Kling, puis clonée pour la voix off de la transition.
BEATS = {
    "hook": "This local business has hundreds of five-star reviews... and no website.",
    "cta": "If this is your business, it's already online — link's in bio. Free to try.",
}


def build_prompt(line: str) -> str:
    return (
        "9:16 vertical selfie UGC video. The same charismatic young man from the image holds "
        "his phone at arm's length, talking directly to camera with friendly, energetic "
        "creator energy. Natural handheld motion, expressive face and subtle hand gestures. "
        f"He says: '{line}' "
        "Authentic creator vibe, natural lighting, real human voice, no on-screen text, no music."
    )


def image_input():
    """Replicate accepte une URL (str) ou un fichier uploadé."""
    if AVATAR.startswith("http"):
        return AVATAR
    if os.path.exists(AVATAR):
        return open(AVATAR, "rb")
    sys.exit(f"❌ Avatar introuvable : {AVATAR} (mets une URL ou un chemin local valide).")


def generate(beat: str, line: str) -> None:
    print(f"\n🎬 [{beat}] {line!r}")
    last_err = None
    # Le nom du champ image varie selon les versions : on tente start_image puis image.
    for image_param in ("start_image", "image"):
        try:
            out = replicate.run(
                MODEL,
                input={
                    "prompt": build_prompt(line),
                    image_param: image_input(),
                    "duration": 5,
                    "aspect_ratio": "9:16",
                    "generate_audio": True,
                },
            )
            break
        except Exception as e:  # noqa: BLE001
            print(f"  · champ '{image_param}' refusé ({e})")
            last_err = e
    else:
        sys.exit(f"❌ Échec [{beat}]. Dernière erreur : {last_err}")

    url = str(out[0] if isinstance(out, list) else out)
    output = f"out/clips/{beat}.mp4"
    os.makedirs("out/clips", exist_ok=True)
    urllib.request.urlretrieve(url, output)
    print(f"  ✅ {url}\n  💾 {output}")


def line_for(beat: str, script_path: str | None) -> str:
    """Texte du beat : depuis le script JSON si fourni, sinon le défaut BEATS."""
    if script_path:
        with open(script_path) as f:
            data = json.load(f)
        for b in data.get("beats", []):
            if b.get("beat") == beat:
                return b["text"]
        sys.exit(f"❌ Beat {beat!r} absent du script {script_path}.")
    if beat in BEATS:
        return BEATS[beat]
    sys.exit(f"❌ Beat inconnu : {beat}. Choix : {', '.join(BEATS)} (ou fournis --script).")


def main() -> int:
    ap = argparse.ArgumentParser(description="Clips parlants Kling (Replicate) sur l'avatar hôte.")
    ap.add_argument("beat", nargs="?", default="hook", help="hook | cta | all")
    ap.add_argument("--script", help="Script JSON (render_script.py) pour le texte exact du beat")
    args = ap.parse_args()

    load_dotenv()
    if not os.getenv("REPLICATE_API_TOKEN"):
        print("❌ Manque REPLICATE_API_TOKEN (env ou .env).")
        return 1

    beats = ("hook", "cta") if args.beat == "all" else (args.beat,)
    for beat in beats:
        generate(beat, line_for(beat, args.script))
    return 0


if __name__ == "__main__":
    sys.exit(main())
