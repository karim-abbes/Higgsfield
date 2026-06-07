#!/usr/bin/env python3
"""
Transition MORPH fiche Google → site Bunua via fal.ai Kling, SILENCIEUSE.
(Remplace l'ancien pipeline tout-en-un : la voix off vient désormais de
clone_host_voice + render_voiceover, muxée au montage.)

Moins cher/rapide que Replicate pour Kling. Images uploadées côté serveur fal
(pas de timeout d'upload). Modèle : fal-ai/kling-video/o3/standard/image-to-video.

⚠️ Réseau fal requis → lancer EN LOCAL.

Usage :
    python3 scripts/generate_transition_fal.py --duration 5
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.request

import fal_client

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_google_card import load_dotenv  # noqa: E402

M_VIDEO = "fal-ai/kling-video/o3/standard/image-to-video"

PROMPT = (
    "9:16 vertical phone screen. Smooth, satisfying UI reveal: a Google Business Profile "
    "listing seamlessly morphs and transforms into a clean, modern professional business "
    "website. Subtle zoom and polish, fluid transition, no text overlay, no people, "
    "ambient silence, no music."
)


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


def to_url(path: str) -> str:
    if path.startswith("http"):
        return path
    url_file = path + ".url.txt"
    if os.path.exists(url_file):
        u = open(url_file).read().strip()
        if u.startswith("http"):
            return u
    if not os.path.exists(path):
        sys.exit(f"❌ Image introuvable : {path}")
    return fal_client.upload_file(path)


def main() -> int:
    ap = argparse.ArgumentParser(description="Transition silencieuse fiche→site (Kling/fal).")
    ap.add_argument("--start", default="out/images/google_profile.png")
    ap.add_argument("--end", default="out/images/bunua_site.png")
    ap.add_argument("--duration", type=int, default=5)
    ap.add_argument("--out", default="out/clips/transition.mp4")
    ap.add_argument("--force", action="store_true", help="Régénère même si le clip existe")
    args = ap.parse_args()

    load_dotenv()
    if not os.getenv("FAL_KEY"):
        sys.exit("❌ Manque FAL_KEY (env ou .env).")
    if os.path.exists(args.out) and not args.force:
        print(f"⏭  {args.out} existe déjà → conservé (--force pour régénérer).")
        return 0

    print(f"🎬 Transition silencieuse {args.start} → {args.end} ({args.duration}s)…")
    start = time.time()
    result = fal_client.subscribe(
        M_VIDEO,
        arguments={
            "image_url": to_url(args.start),
            "end_image_url": to_url(args.end),
            "prompt": PROMPT,
            "duration": str(args.duration),   # ⚠️ STRING
            "aspect_ratio": "9:16",
            "generate_audio": False,
        },
        with_logs=True,
        on_queue_update=lambda u, s=start: print(f"  · {time.time()-s:5.1f}s — {getattr(u,'status',u)}"),
    )
    url = first_url(result, "video", "url", "output")
    if not url:
        sys.exit(f"❌ Pas de vidéo : {str(result)[:300]}")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    urllib.request.urlretrieve(url, args.out)
    print(f"  ✅ {url}\n  💾 {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
