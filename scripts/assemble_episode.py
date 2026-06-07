#!/usr/bin/env python3
"""
Assemble un ÉPISODE Makeover complet à partir des morceaux déjà générés.

Timeline (cf. brief/makeover-episode.md) :
  [hook.mp4 +voix Kling]
  → [carte Google tenue + voix off stakes+setup]
  → [transition morph + voix off reveal]
  → [site Bunua tenu + voix off kicker]
  → [cta.mp4 +voix Kling]
  → sous-titres brûlés (Whisper, autosubtitle.py)

La voix off (milieu) = MP3 clonés (render_voiceover.py). Les durées des segments
image suivent les durées RÉELLES des MP3 (manifest). Tout est normalisé 1080×1920@30
/ aac 48k stéréo, puis concaténé (concat demuxer).

⚠️ ffmpeg/ffprobe requis. FAL_KEY (sous-titres) → lancer EN LOCAL.

Usage :
    python3 scripts/assemble_episode.py out/scripts/<slug>.script.json
    python3 scripts/assemble_episode.py <script.json> --no-subs   # sans sous-titres
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_google_card import load_dotenv  # noqa: E402

W, H, FPS = 1080, 1920, 30
VF_NORM = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
           f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,fps={FPS},setsar=1")
VENC = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "20"]
AENC = ["-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k"]

FF = "ffmpeg"
FP = "ffprobe"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def dur(path: str) -> float:
    out = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    return float(out.stdout.strip())


def norm_clip(src: str, out: str) -> None:
    """Normalise un clip vidéo (hook/cta) au format standard."""
    run([FF, "-y", "-loglevel", "error", "-i", src, "-vf", VF_NORM, *VENC, *AENC, out])


def image_segment(img: str, audios: list[str], out: str) -> None:
    """Image fixe tenue pendant la durée des MP3 voix off (concaténés)."""
    cmd = [FF, "-y", "-loglevel", "error", "-loop", "1", "-i", img]
    for a in audios:
        cmd += ["-i", a]
    n = len(audios)
    concat = "".join(f"[{i+1}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1[a]"
    cmd += ["-filter_complex", f"[0:v]{VF_NORM}[v];{concat}",
            "-map", "[v]", "-map", "[a]", "-shortest", *VENC, *AENC, out]
    run(cmd)


def reveal_segment(video: str, audio: str, out: str) -> None:
    """Morph (silencieux) + voix off reveal : on gèle la dernière image si la voix
    dépasse la vidéo, et on pad l'audio si la vidéo dépasse → durée = max des deux."""
    vd, ad = dur(video), dur(audio)
    m = max(vd, ad) + 0.05
    pad = m - vd + 0.1
    run([FF, "-y", "-loglevel", "error", "-i", video, "-i", audio,
         "-filter_complex",
         f"[0:v]{VF_NORM},tpad=stop_mode=clone:stop_duration={pad:.2f}[v];[1:a]apad[a]",
         "-map", "[v]", "-map", "[a]", "-t", f"{m:.2f}", *VENC, *AENC, out])


def main() -> int:
    ap = argparse.ArgumentParser(description="Assemble un épisode Makeover complet.")
    ap.add_argument("script", help="Script JSON de l'épisode (render_script.py)")
    ap.add_argument("--clips", default="out/clips", help="Dossier des clips (hook/cta/transition)")
    ap.add_argument("--card", default="out/images/google_profile.png")
    ap.add_argument("--site", default="out/images/bunua_site.png")
    ap.add_argument("--out", help="Vidéo finale (défaut out/episodes/<slug>.mp4)")
    ap.add_argument("--no-subs", action="store_true", help="Ne pas brûler les sous-titres")
    args = ap.parse_args()

    load_dotenv()
    if not shutil.which(FF) or not shutil.which(FP):
        sys.exit("❌ ffmpeg/ffprobe introuvables dans le PATH.")
    slug = os.path.basename(args.script).replace(".script.json", "")
    voice_dir = os.path.join("out", "voice", slug)
    manifest_p = os.path.join(voice_dir, "voiceover.manifest.json")
    for p in (args.script, manifest_p, args.card, args.site,
              f"{args.clips}/hook.mp4", f"{args.clips}/transition.mp4", f"{args.clips}/cta.mp4"):
        if not os.path.exists(p):
            sys.exit(f"❌ Manque : {p}")

    manifest = json.load(open(manifest_p))
    audio = {b["beat"]: b["audio"] for b in manifest["beats"]}
    for beat in ("stakes", "setup", "reveal", "kicker"):
        if not os.path.exists(audio.get(beat, "")):
            sys.exit(f"❌ MP3 voix off manquant pour le beat '{beat}'. Relance render_voiceover.py.")

    tmp = "out/.tmp_episode"
    os.makedirs(tmp, exist_ok=True)
    print("🎬 Construction des segments…")
    print("  · hook"); norm_clip(f"{args.clips}/hook.mp4", f"{tmp}/1_hook.mp4")
    print("  · carte + stakes/setup"); image_segment(args.card, [audio["stakes"], audio["setup"]], f"{tmp}/2_card.mp4")
    print("  · morph + reveal"); reveal_segment(f"{args.clips}/transition.mp4", audio["reveal"], f"{tmp}/3_reveal.mp4")
    print("  · site + kicker"); image_segment(args.site, [audio["kicker"]], f"{tmp}/4_site.mp4")
    print("  · cta"); norm_clip(f"{args.clips}/cta.mp4", f"{tmp}/5_cta.mp4")

    concat_f = f"{tmp}/concat.txt"
    with open(concat_f, "w") as f:
        for name in ("1_hook", "2_card", "3_reveal", "4_site", "5_cta"):
            f.write(f"file '{name}.mp4'\n")
    merged = f"{tmp}/merged.mp4"
    print("🧩 Concaténation…")
    run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", concat_f, "-c", "copy", merged])

    out = args.out or os.path.join("out", "episodes", f"{slug}.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    if args.no_subs or not os.getenv("FAL_KEY"):
        shutil.copy(merged, out)
        if not args.no_subs:
            print("ℹ️  FAL_KEY absent → pas de sous-titres (export FAL_KEY pour les activer).")
    else:
        print("💬 Sous-titres auto (Whisper)…")
        srt = os.path.join("out", "episodes", f"{slug}.srt")
        r = subprocess.run([sys.executable, "scripts/autosubtitle.py", merged, out, srt])
        if r.returncode != 0:
            print("⚠️  Sous-titres échoués → version sans sous-titres.")
            shutil.copy(merged, out)

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n✅ Épisode → {out}   (⏱ {dur(out):.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
