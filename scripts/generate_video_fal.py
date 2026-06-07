#!/usr/bin/env python3
"""
Clips parlants (hook / CTA) via fal.ai Kling — moins cher et plus rapide que Replicate
pour Kling (~$0.126/s vs ~$1.68/clip). La voix est générée nativement par Kling.

Modèle : fal-ai/kling-video/o3/standard/image-to-video (cf. skill fal-ai).
Image passée par fal_client.upload_file → URL côté serveur (pas de timeout d'upload).

⚠️ Réseau fal requis → lancer EN LOCAL.

Usage :
    python3 scripts/generate_video_fal.py hook --script out/scripts/<slug>.script.json
    python3 scripts/generate_video_fal.py all  --script ...
    # --force pour régénérer un clip déjà présent (sinon il est conservé)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request

import fal_client

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_google_card import load_dotenv  # noqa: E402

M_VIDEO = "fal-ai/kling-video/o3/standard/image-to-video"
AVATAR = os.getenv("AVATAR", "out/images/avatar.png")

BEATS = {
    "hook": "This local business has hundreds of five-star reviews... and no website.",
    "cta": "If this is your business, it's already online — link's in bio. Free to try.",
}


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


def build_prompt(line: str) -> str:
    return (
        "9:16 vertical selfie UGC video. The same charismatic young man from the image holds "
        "his phone at arm's length, talking directly to camera with friendly, energetic "
        "creator energy. Natural handheld motion, expressive face and subtle hand gestures. "
        f"He says: '{line}' "
        "Authentic creator vibe, natural lighting, real human voice, no on-screen text, no music."
    )


def avatar_url() -> str:
    """URL de l'avatar : <AVATAR>.url.txt si dispo, sinon upload du fichier local."""
    if AVATAR.startswith("http"):
        return AVATAR
    url_file = AVATAR + ".url.txt"
    if os.path.exists(url_file):
        u = open(url_file).read().strip()
        if u.startswith("http"):
            return u
    if not os.path.exists(AVATAR):
        sys.exit(f"❌ Avatar introuvable : {AVATAR}")
    return fal_client.upload_file(AVATAR)


def line_for(beat: str, script_path: str | None) -> str:
    if script_path:
        with open(script_path) as f:
            data = json.load(f)
        for b in data.get("beats", []):
            if b.get("beat") == beat:
                return b["text"]
        sys.exit(f"❌ Beat {beat!r} absent du script {script_path}.")
    if beat in BEATS:
        return BEATS[beat]
    sys.exit(f"❌ Beat inconnu : {beat} (ou fournis --script).")


def generate(beat: str, line: str, force: bool) -> None:
    out = f"out/clips/{beat}.mp4"
    if os.path.exists(out) and not force:
        print(f"⏭  [{beat}] {out} existe déjà → conservé (--force pour régénérer).")
        return
    print(f"\n🎬 [{beat}] {line!r}")
    start = time.time()
    img = avatar_url()
    result = fal_client.subscribe(
        M_VIDEO,
        arguments={
            "image_url": img,
            "prompt": build_prompt(line),
            "duration": "5",            # ⚠️ STRING pour Kling sur fal
            "aspect_ratio": "9:16",
            "generate_audio": True,
        },
        with_logs=True,
        on_queue_update=lambda u, s=start: print(f"  · {time.time()-s:5.1f}s — {getattr(u,'status',u)}"),
    )
    url = first_url(result, "video", "url", "output")
    if not url:
        sys.exit(f"❌ Pas de vidéo : {str(result)[:300]}")
    os.makedirs("out/clips", exist_ok=True)
    urllib.request.urlretrieve(url, out)
    print(f"  ✅ {url}\n  💾 {out}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Clips parlants Kling via fal.ai.")
    ap.add_argument("beat", nargs="?", default="hook", help="hook | cta | all")
    ap.add_argument("--script", help="Script JSON pour le texte exact du beat")
    ap.add_argument("--force", action="store_true", help="Régénère même si le clip existe")
    args = ap.parse_args()

    load_dotenv()
    if not os.getenv("FAL_KEY"):
        sys.exit("❌ Manque FAL_KEY (env ou .env).")

    beats = ("hook", "cta") if args.beat == "all" else (args.beat,)
    for beat in beats:
        generate(beat, line_for(beat, args.script), args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
