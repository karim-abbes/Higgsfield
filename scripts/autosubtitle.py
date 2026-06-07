#!/usr/bin/env python3
"""
Génère des sous-titres PARFAITEMENT synchronisés depuis l'audio réel d'une vidéo,
via fal Whisper (timestamps mot-à-mot), puis les incruste.

Fini le décalage : les sous-titres collent à la voix réelle, quelle que soit la
durée des clips. Marche pour n'importe quelle vidéo (automatisation friendly).

Usage :
    export FAL_KEY="..."
    python3 scripts/autosubtitle.py <video_in> <video_out> [srt_out]

Ex :
    python3 scripts/autosubtitle.py out/bunua_ugc_final_nosubs.mp4 out/bunua_ugc_final.mp4
"""
from __future__ import annotations

import os
import subprocess
import sys

import fal_client

WORDS_PER_CAPTION = 4   # style TikTok : 3-5 mots par ligne
MAX_GAP = 0.6           # nouvelle ligne si silence > 0.6s entre 2 mots


def srt_time(t: float) -> str:
    h = int(t // 3600); t -= h * 3600
    m = int(t // 60); t -= m * 60
    s = int(t)
    ms = int(round((t - s) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def extract_audio(video: str) -> str:
    audio = "out/.tmp_subs_audio.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", video,
         "-vn", "-acodec", "libmp3lame", "-q:a", "4", audio],
        check=True,
    )
    return audio


def transcribe_words(audio_url: str) -> list[dict]:
    """Renvoie une liste de {'text','start','end'} au niveau mot."""
    result = fal_client.subscribe(
        "fal-ai/whisper",
        arguments={"audio_url": audio_url, "chunk_level": "word"},
        with_logs=True,
        on_queue_update=lambda u: print(f"  · {getattr(u, 'status', u)}"),
    )
    chunks = result.get("chunks") if isinstance(result, dict) else None
    if not chunks:
        sys.exit(f"❌ Pas de chunks dans la réponse Whisper : {str(result)[:400]}")

    words = []
    for c in chunks:
        ts = c.get("timestamp") or c.get("timestamps") or [None, None]
        start, end = (ts + [None, None])[:2]
        if start is None:
            continue
        words.append({"text": (c.get("text") or "").strip(), "start": start, "end": end})
    return words


def build_srt(words: list[dict]) -> str:
    lines, group = [], []

    def flush(idx):
        if not group:
            return idx
        start = srt_time(group[0]["start"])
        end = srt_time(group[-1]["end"] or group[-1]["start"] + 0.4)
        text = " ".join(w["text"] for w in group).strip()
        lines.append(f"{idx}\n{start} --> {end}\n{text}\n")
        return idx + 1

    idx = 1
    for i, w in enumerate(words):
        if group:
            gap = w["start"] - (group[-1]["end"] or group[-1]["start"])
            if len(group) >= WORDS_PER_CAPTION or gap > MAX_GAP:
                idx = flush(idx)
                group = []
        group.append(w)
    flush(idx)
    return "\n".join(lines)


def burn(video_in: str, srt: str, video_out: str) -> None:
    # Alignment=2 (ancré en bas) + MarginV en échelle libass (~288px de haut).
    # MarginV=85 ≈ 70% de la hauteur : sous le visage, AU-DESSUS de l'UI TikTok/IG
    # (qui occupe le bas ~18%). Ajustable via SUB_MARGIN_V (plus petit = plus bas).
    margin_v = os.getenv("SUB_MARGIN_V", "85")
    style = (f"Fontname=Arial Black,Fontsize=14,PrimaryColour=&H00FFFFFF,"
             f"OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,"
             f"Alignment=2,MarginV={margin_v}")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", video_in,
         "-vf", f"subtitles={srt}:force_style='{style}'",
         "-c:a", "copy", video_out],
        check=True,
    )


def main(argv: list[str]) -> int:
    if not os.getenv("FAL_KEY"):
        print("❌ Manque FAL_KEY.")
        return 1
    if len(argv) < 3:
        print("Usage: autosubtitle.py <video_in> <video_out> [srt_out]")
        return 1

    video_in, video_out = argv[1], argv[2]
    srt_out = argv[3] if len(argv) > 3 else "out/subtitles_auto.srt"

    print("🎤 Extraction audio…")
    audio = extract_audio(video_in)
    print("  ⬆️  upload…")
    audio_url = fal_client.upload_file(audio)

    print("📝 Transcription Whisper (mot-à-mot)…")
    words = transcribe_words(audio_url)
    print(f"  {len(words)} mots détectés.")

    srt_content = build_srt(words)
    with open(srt_out, "w") as f:
        f.write(srt_content)
    print(f"💬 SRT auto → {srt_out}")

    print("🔥 Incrustation…")
    burn(video_in, srt_out, video_out)
    os.remove(audio) if os.path.exists(audio) else None
    print(f"✅ Vidéo sous-titrée → {video_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
