#!/usr/bin/env python3
"""
Recadre le HAUT d'une image d'avatar (enlève la fausse barre d'état "téléphone"
hallucinée par le modèle image) + downscale léger pour un upload Replicate fiable.

Pourquoi : une barre d'état dans un "selfie vidéo" est irréaliste (la caméra ne
filme pas ton propre écran) et trahit l'IA. On la coupe sur l'image de départ
→ elle disparaît du clip Kling (qui part de cette image via start_image).

⚠️ Supprime aussi le <out>.url.txt : il pointe vers l'image CDN NON recadrée ;
sans ça, Replicate re-téléchargerait la version avec la barre. Après ce script,
generate_video_replicate.py uploadera le fichier local recadré (petit → pas de timeout).

Usage :
    python3 scripts/crop_avatar.py                 # out/images/avatar.png en place
    python3 scripts/crop_avatar.py --top-frac 0.05 --max-width 1080
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description="Recadre le haut d'un avatar (barre d'état).")
    ap.add_argument("--in", dest="src", default="out/images/avatar.png")
    ap.add_argument("--out", help="Défaut : écrase l'entrée")
    ap.add_argument("--top-frac", type=float, default=0.06,
                    help="Fraction de hauteur coupée en haut (déf 0.06 = 6%%)")
    ap.add_argument("--max-width", type=int, default=1080,
                    help="Largeur max après recadrage (upload léger). 0 = pas de downscale")
    args = ap.parse_args()

    ff = shutil.which("ffmpeg")
    if not ff:
        sys.exit("❌ ffmpeg introuvable dans le PATH.")
    if not os.path.exists(args.src):
        sys.exit(f"❌ Image introuvable : {args.src}")

    out = args.out or args.src
    tmp = out + ".tmp.png"
    # crop=largeur:hauteur:x:y — on garde toute la largeur, on coupe top_frac en haut.
    keep = 1.0 - args.top_frac
    vf = f"crop=iw:ih*{keep:.4f}:0:ih*{args.top_frac:.4f}"
    if args.max_width:
        vf += f",scale='min({args.max_width},iw)':-2"

    subprocess.run([ff, "-y", "-loglevel", "error", "-i", args.src,
                    "-vf", vf, "-frames:v", "1", "-update", "1", tmp], check=True)
    os.replace(tmp, out)
    print(f"✅ Recadré ({int(args.top_frac*100)}% en haut) → {out}")

    url_file = out + ".url.txt"
    if os.path.exists(url_file):
        os.remove(url_file)
        print(f"🗑  Supprimé {url_file} (pointait vers l'image CDN non recadrée)")
    print("➡️ Relance maintenant le hook : il uploadera ce fichier local recadré.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
