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


def audio_concat(audios: list[str], out: str) -> float:
    """Concatène des MP3 en un m4a unique. Renvoie la durée (s)."""
    cmd = [FF, "-y", "-loglevel", "error"]
    for a in audios:
        cmd += ["-i", a]
    n = len(audios)
    cmd += ["-filter_complex", "".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1[a]",
            "-map", "[a]", *AENC, out]
    run(cmd)
    return dur(out)


def card_segment(card: str, audios: list[str], circle: str | None, out: str, tmp: str) -> None:
    """Fiche Google DYNAMIQUE, SANS déformation (toujours en 9:16) :
    (1) Ken Burns push-in, puis (3) cercle rouge (ellipse) fade-in sur la RANGÉE de
    boutons d'action (Directions/Call/Save/Share → aucun bouton site). Durée = voix off."""
    ca = f"{tmp}/card_audio.m4a"
    total = audio_concat(audios, ca)
    d1 = max(1.0, round(total * 0.55, 2))
    d2 = max(0.8, round(total - d1, 2))
    s1, s2, vid = f"{tmp}/card_s1.mp4", f"{tmp}/card_s2.mp4", f"{tmp}/card_vid.mp4"

    # Shot 1 — Ken Burns (zoom lent) sur la fiche entière (prescale = anti-jitter).
    run([FF, "-y", "-loglevel", "error", "-loop", "1", "-t", f"{d1}", "-i", card,
         "-filter_complex",
         f"[0:v]scale={W*2}:{H*2},zoompan=z='min(1+0.0011*on,1.10)':"
         f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(d1*FPS)}:s={W}x{H}:fps={FPS},setsar=1[v]",
         "-map", "[v]", "-t", f"{d1}", *VENC, s1])

    # Shot 2 — fiche ENTIÈRE (pas de crop = pas de déformation) + ellipse rouge qui
    # apparaît sur la rangée de boutons (≈ 64% de hauteur). Tunable via CIRCLE_Y.
    cy = int(os.getenv("CIRCLE_Y", "990"))     # haut de l'ellipse (px sur 1920 ; rangée ≈ y1173)
    cw, ch = 1010, 360                          # ellipse large = englobe les 4 boutons
    if circle and os.path.exists(circle):
        run([FF, "-y", "-loglevel", "error", "-loop", "1", "-t", f"{d2}", "-i", card,
             "-loop", "1", "-t", f"{d2}", "-i", circle,
             "-filter_complex",
             f"[0:v]scale={W}:{H},setsar=1,fps={FPS}[b];"
             f"[1:v]format=rgba,fade=in:st=0.2:d=0.5:alpha=1,scale={cw}:{ch}[r];"
             f"[b][r]overlay=(W-w)/2:{cy}[v]",
             "-map", "[v]", "-t", f"{d2}", *VENC, s2])
    else:
        run([FF, "-y", "-loglevel", "error", "-loop", "1", "-t", f"{d2}", "-i", card,
             "-filter_complex", f"[0:v]scale={W}:{H},setsar=1,fps={FPS}[v]",
             "-map", "[v]", "-t", f"{d2}", *VENC, s2])

    cf = f"{tmp}/card_concat.txt"
    with open(cf, "w") as f:
        f.write("file 'card_s1.mp4'\nfile 'card_s2.mp4'\n")
    run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", cf, "-an", "-c", "copy", vid])
    run([FF, "-y", "-loglevel", "error", "-i", vid, "-i", ca,
         "-map", "0:v", "-map", "1:a", "-shortest", *VENC, *AENC, out])


def site_scroll_segment(site_full: str, audios: list[str], out: str, tmp: str) -> None:
    """Site Bunua DYNAMIQUE : scroll vertical d'un screenshot pleine page pendant la
    voix kicker (si l'image est plus haute que l'écran ; sinon plan fixe en haut)."""
    ca = f"{tmp}/site_audio.m4a"
    total = audio_concat(audios, ca)
    y = f"'min(max((ih-{H})*t/{total}\\,0)\\,ih-{H})'"
    run([FF, "-y", "-loglevel", "error", "-loop", "1", "-i", site_full, "-i", ca,
         "-filter_complex",
         f"[0:v]scale={W}:-1,crop={W}:{H}:0:{y},fps={FPS},setsar=1[v]",
         "-map", "[v]", "-map", "1:a", "-t", f"{total}", *VENC, *AENC, out])


def main() -> int:
    ap = argparse.ArgumentParser(description="Assemble un épisode Makeover complet.")
    ap.add_argument("script", help="Script JSON de l'épisode (render_script.py)")
    ap.add_argument("--clips", default="out/clips", help="Dossier des clips (hook/cta/transition)")
    ap.add_argument("--card", default="out/images/google_profile.png")
    ap.add_argument("--site", default="out/images/bunua_site.png",
                    help="Image du site pour le kicker (idéalement pleine page → scroll)")
    ap.add_argument("--circle", default="assets/red_circle.png",
                    help="Cercle rouge (overlay sur la fiche). Ignoré si absent.")
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
    print("  · fiche (Ken Burns + punch-in + cercle)"); card_segment(args.card, [audio["stakes"], audio["setup"]], args.circle, f"{tmp}/2_card.mp4", tmp)
    print("  · morph + reveal"); reveal_segment(f"{args.clips}/transition.mp4", audio["reveal"], f"{tmp}/3_reveal.mp4")
    print("  · site (scroll vertical)"); site_scroll_segment(args.site, [audio["kicker"]], f"{tmp}/4_site.mp4", tmp)
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
