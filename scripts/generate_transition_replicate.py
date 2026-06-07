#!/usr/bin/env python3
"""
Transition MORPH fiche Google → site Bunua, via Kling 3.0 (start/end image), SILENCIEUSE.

Pourquoi silencieuse : la voix off du reveal vient de notre TTS (voix Kling clonée),
muxée au montage. Ici on ne génère QUE l'animation visuelle (pas la voix Kling, qui
serait incohérente avec le reste).

⚠️ Réseau Replicate requis → lancer EN LOCAL.

Usage :
    python3 scripts/generate_transition_replicate.py
    # images par défaut : out/images/google_profile.png → out/images/bunua_site.png
    # durée : --duration 5  (≈ la durée du beat reveal)
"""
from __future__ import annotations

import argparse
import os
import sys
import urllib.request

import replicate

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_google_card import load_dotenv  # noqa: E402

MODEL = "kwaivgi/kling-v3-video"

PROMPT = (
    "9:16 vertical phone screen. Smooth, satisfying UI reveal: a Google Business Profile "
    "listing seamlessly morphs and transforms into a clean, modern professional business "
    "website. Subtle zoom and polish, fluid transition, no text overlay, no people, "
    "ambient silence, no music."
)


def img(path: str):
    """URL si dispo (<path>.url.txt), sinon fichier local."""
    if path.startswith("http"):
        return path
    url_file = path + ".url.txt"
    if os.path.exists(url_file):
        u = open(url_file).read().strip()
        if u.startswith("http"):
            return u
    if os.path.exists(path):
        return open(path, "rb")
    sys.exit(f"❌ Image introuvable : {path}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Transition silencieuse fiche→site (Kling/Replicate).")
    ap.add_argument("--start", default="out/images/google_profile.png")
    ap.add_argument("--end", default="out/images/bunua_site.png")
    ap.add_argument("--duration", type=int, default=5)
    ap.add_argument("--out", default="out/clips/transition.mp4")
    args = ap.parse_args()

    load_dotenv()
    if not os.getenv("REPLICATE_API_TOKEN"):
        sys.exit("❌ Manque REPLICATE_API_TOKEN (env ou .env).")
    for p in (args.start, args.end):
        if not (p.startswith("http") or os.path.exists(p) or os.path.exists(p + ".url.txt")):
            sys.exit(f"❌ Image manquante : {p}")

    print(f"🎬 Transition silencieuse {args.start} → {args.end} ({args.duration}s)…")
    last_err = None
    for attempt in range(1, 4):
        try:
            out = replicate.run(
                MODEL,
                input={
                    "prompt": PROMPT,
                    "start_image": img(args.start),
                    "end_image": img(args.end),
                    "duration": args.duration,
                    "aspect_ratio": "9:16",
                    "generate_audio": False,
                },
            )
            break
        except Exception as e:  # noqa: BLE001
            print(f"  · tentative {attempt}/3 échouée ({e})")
            last_err = e
    else:
        sys.exit(f"❌ Échec après 3 tentatives : {last_err}")

    url = str(out[0] if isinstance(out, list) else out)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    urllib.request.urlretrieve(url, args.out)
    print(f"  ✅ {url}\n  💾 {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
