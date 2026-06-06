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

import os
import sys
import urllib.request

import replicate

MODEL = "kwaivgi/kling-v3-video"
AVATAR = os.getenv("AVATAR", "out/images/avatar.png")

# Répliques tête-parlante (la voix est générée nativement par Kling).
BEATS = {
    "hook": "POV: you run a local business... but you still don't have a website.",
    "cta": "If you've been putting it off — go to bunua dot com and search your business. That's it.",
    # Variantes de hook à A/B tester :
    "hook_b": "If you own a local shop, this is honestly a cheat code.",
    "hook_c": "Your customers Google you every day, and find nothing. Let's fix that in five minutes.",
}


def build_prompt(line: str) -> str:
    return (
        "9:16 vertical selfie UGC video. The same female bakery owner from the image holds "
        "her phone at arm's length, walking slowly through her warm bakery, talking directly "
        "to camera with friendly, slightly excited energy. Handheld natural motion. "
        f"She says: '{line}' "
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


def main(argv: list[str]) -> int:
    if not os.getenv("REPLICATE_API_TOKEN"):
        print("❌ Manque REPLICATE_API_TOKEN (replicate.com/account/api-tokens).")
        return 1

    target = argv[1] if len(argv) > 1 else "hook"
    if target == "all":
        for beat in ("hook", "cta"):
            generate(beat, BEATS[beat])
    elif target in BEATS:
        generate(target, BEATS[target])
    else:
        print(f"Beat inconnu : {target}. Choix : {', '.join(BEATS)} ou 'all'.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
