#!/usr/bin/env python3
"""
Clone la voix de l'HÔTE depuis les clips Kling (hook + CTA) → empreinte en cache.

Pourquoi : hook/CTA sont générés par Kling avec SA voix. Pour que la voix off du
milieu (render_voiceover.py) soit LA MÊME voix, on clone celle de Kling et on
écrase l'empreinte hôte en cache. Résultat : une seule voix sur tout l'épisode.

Pipeline (cf. skill fal-ai) :
  ffmpeg extrait+concatène l'audio hook+CTA → WAV (≤30s)
  → fal-ai/qwen-3-tts/clone-voice/1.7b → empreinte → out/voice/host/embedding_url.txt

⚠️ Réseau fal requis → lancer EN LOCAL.

Usage :
    python3 scripts/clone_host_voice.py
    python3 scripts/render_voiceover.py out/scripts/<slug>.script.json   # réutilise la voix clonée
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

import fal_client

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_google_card import load_dotenv  # noqa: E402
from render_voiceover import clone_to_embedding  # noqa: E402

CLIPS = [os.getenv("HOOK_CLIP", "out/clips/hook.mp4"),
         os.getenv("CTA_CLIP", "out/clips/cta.mp4")]


def build_sample(work_dir: str) -> str:
    ff = shutil.which("ffmpeg")
    if not ff:
        sys.exit("❌ ffmpeg introuvable dans le PATH.")
    srcs = [c for c in CLIPS if os.path.exists(c)]
    if not srcs:
        sys.exit(f"❌ Aucun clip source ({' / '.join(CLIPS)}). Génère hook et cta d'abord.")
    os.makedirs(work_dir, exist_ok=True)
    sample = os.path.join(work_dir, "kling_voice_sample.wav")
    print(f"🎤 Extraction audio depuis {', '.join(srcs)} (≤30s)…")
    inputs = []
    for s in srcs:
        inputs += ["-i", s]
    n = len(srcs)
    fc = "".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1[a]"
    subprocess.run([ff, "-y", "-loglevel", "error", *inputs,
                    "-filter_complex", fc, "-map", "[a]", "-t", "30",
                    "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1", sample],
                   check=True)
    return sample


def main() -> int:
    ap = argparse.ArgumentParser(description="Clone la voix Kling (hook+CTA) → empreinte.")
    ap.add_argument("--embed-out", default="out/voice/host/embedding_url.txt",
                    help="Où écrire l'URL d'empreinte (par épisode via l'orchestrateur)")
    args = ap.parse_args()

    load_dotenv()
    if not os.getenv("FAL_KEY"):
        sys.exit("❌ Manque FAL_KEY (env ou .env).")

    work_dir = os.path.dirname(args.embed_out) or "."
    sample = build_sample(work_dir)
    embed = clone_to_embedding(sample)  # upload + clone-voice (réutilisé de render_voiceover)
    os.makedirs(work_dir, exist_ok=True)
    with open(args.embed_out, "w") as f:
        f.write(embed)
    print(f"✅ Voix Kling clonée → {args.embed_out}")
    print("➡️ render_voiceover.py utilisera CETTE voix (même dossier d'épisode).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
