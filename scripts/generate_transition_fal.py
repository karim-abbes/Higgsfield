#!/usr/bin/env python3
"""
Transition PARLANTE avec voix clonée — version Qwen3-TTS (qui fonctionne).

Pourquoi cette version :
  Le voice_id de Kling n'est PAS appliqué sur image-to-video (limitation officielle
  fal.ai : "Voice binding only supported for video elements, not image elements").
  → On clone la voix avec Qwen3-TTS, on génère la transition SANS audio, puis on
    colle l'audio TTS dessus avec ffmpeg.

Pipeline (tout sur fal.ai) :
  1) ffmpeg extrait hook + CTA → un WAV concaténé (sample voix)
  2) fal-ai/qwen-3-tts/clone-voice/1.7b → empreinte vocale (safetensors URL)
  3) fal-ai/qwen-3-tts/text-to-speech/1.7b → MP3 de la narration avec voix clonée
  4) fal-ai/kling-video/o3/standard/image-to-video → transition Google→Bunua MUETTE
  5) ffmpeg mux : vidéo (4) + audio (3) → transition finale avec voix clonée

Coût estimé : ~$0.90 (vs $1.54 avec voice_id Kling qui ne marchait pas).

Usage :
    export FAL_KEY="..."
    python3 scripts/generate_transition_fal.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request

import fal_client

# --- Endpoints ---
M_CLONE = "fal-ai/qwen-3-tts/clone-voice/1.7b"
M_TTS = "fal-ai/qwen-3-tts/text-to-speech/1.7b"
M_VIDEO = "fal-ai/kling-video/o3/standard/image-to-video"

# --- Sources ---
HOOK_CLIP = os.getenv("HOOK_CLIP", "out/clips/hook.mp4")
CTA_CLIP = os.getenv("CTA_CLIP", "out/clips/cta.mp4")
START_IMAGE = os.getenv("START_IMAGE", "out/images/google_profile.png")
END_IMAGE = os.getenv("END_IMAGE", "out/images/bunua_site.png")

# --- Cache ---
EMBED_FILE = "out/voice/speaker_embedding_url.txt"
VOICE_SAMPLE = "out/voice/voice_sample.wav"

# --- Contenu ---
NARRATION = (
    "Your customers Google you every day, but find nothing. "
    "Bunua turns your Google profile into a real website. "
    "In five minutes. No signup, no card."
)
VIDEO_PROMPT = (
    "9:16 vertical phone screen. Smooth satisfying UI reveal: a basic Google Business "
    "Profile listing transforms into a clean, professional bakery website. Subtle zoom "
    "and modern polish, seamless transition, hands holding the phone visible at edges. "
    "No text overlay, no music, ambient silence."
)

TS = time.strftime("%Y%m%d_%H%M%S")
SILENT_VIDEO = f"out/clips/transition_silent_{TS}.mp4"
NARRATION_AUDIO = f"out/voice/narration_{TS}.mp3"
OUTPUT = f"out/clips/transition_{TS}.mp4"


# --- Helpers ---
def first_url(result, *keys):
    """Cherche la 1ère clé non-vide dans une réponse fal (parfois imbriquée)."""
    if not isinstance(result, dict):
        return None
    for k in keys:
        v = result.get(k)
        if isinstance(v, str) and v.startswith("http"):
            return v
        if isinstance(v, dict) and isinstance(v.get("url"), str):
            return v["url"]
    return None


def progress(start, u):
    print(f"  · {time.time()-start:5.1f}s — {getattr(u, 'status', u)}")


# --- Étape 1 : sample audio ---
def make_voice_sample() -> str:
    sources = [p for p in (HOOK_CLIP, CTA_CLIP) if os.path.exists(p)]
    if not sources:
        sys.exit(f"❌ Aucun clip source ({HOOK_CLIP} ou {CTA_CLIP}).")
    print(f"🎤 Concaténation audio depuis {', '.join(sources)} (max 30s)…")
    os.makedirs(os.path.dirname(VOICE_SAMPLE), exist_ok=True)

    inputs: list[str] = []
    for src in sources:
        inputs += ["-i", src]
    n = len(sources)
    fc = "".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1[a]"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", *inputs,
         "-filter_complex", fc, "-map", "[a]", "-t", "30",
         "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1",
         VOICE_SAMPLE],
        check=True,
    )
    return VOICE_SAMPLE


# --- Étape 2 : clonage voix → embedding ---
def get_or_create_embedding() -> str:
    if os.path.exists(EMBED_FILE):
        url = open(EMBED_FILE).read().strip()
        if url.startswith("http"):
            print(f"♻️  embedding en cache : …{url[-40:]}")
            return url

    sample = make_voice_sample()
    sample_url = fal_client.upload_file(sample)
    print(f"  ⬆️  sample uploadé")

    start = time.time()
    print("🧬 Clonage de la voix (Qwen3-TTS)…")
    last_err = None
    for key in ("audio_url", "voice_url", "input_audio_url"):
        try:
            result = fal_client.subscribe(
                M_CLONE,
                arguments={key: sample_url},
                with_logs=True,
                on_queue_update=lambda u, s=start: progress(s, u),
            )
            break
        except Exception as e:  # noqa: BLE001
            print(f"  · champ '{key}' refusé ({type(e).__name__})")
            last_err = e
    else:
        sys.exit(f"❌ Aucun champ d'audio accepté pour le clonage : {last_err}")

    embed_url = first_url(result, "speaker_embedding", "speaker_embedding_url",
                          "embedding_url", "voice_url", "audio", "output", "url")
    if not embed_url:
        sys.exit(f"❌ Pas d'URL d'empreinte dans la réponse : {str(result)[:400]}")

    with open(EMBED_FILE, "w") as f:
        f.write(embed_url)
    print(f"✅ embedding sauvegardé → {EMBED_FILE}")
    return embed_url


# --- Étape 3 : TTS narration → MP3 ---
def synthesize_narration(embed_url: str) -> str:
    start = time.time()
    print("\n🗣  Synthèse TTS de la narration (voix clonée)…")

    base = {"text": NARRATION}
    last_err = None
    for key in ("speaker_embedding_url", "voice_url", "embedding_url"):
        try:
            result = fal_client.subscribe(
                M_TTS,
                arguments={**base, key: embed_url},
                with_logs=True,
                on_queue_update=lambda u, s=start: progress(s, u),
            )
            break
        except Exception as e:  # noqa: BLE001
            print(f"  · champ '{key}' refusé ({type(e).__name__})")
            last_err = e
    else:
        sys.exit(f"❌ Aucun champ d'embedding accepté pour le TTS : {last_err}")

    audio_url = first_url(result, "audio", "audio_url", "url", "output")
    if not audio_url:
        sys.exit(f"❌ Pas d'audio dans la réponse TTS : {str(result)[:400]}")

    os.makedirs(os.path.dirname(NARRATION_AUDIO), exist_ok=True)
    urllib.request.urlretrieve(audio_url, NARRATION_AUDIO)
    print(f"✅ narration → {NARRATION_AUDIO}")
    return NARRATION_AUDIO


# --- Étape 4 : transition vidéo silencieuse ---
def generate_silent_video() -> str:
    if not os.path.exists(START_IMAGE):
        sys.exit(f"❌ {START_IMAGE} introuvable.")
    if not os.path.exists(END_IMAGE):
        sys.exit(f"❌ {END_IMAGE} introuvable.")

    start = time.time()
    print("\n🎬 Génération transition silencieuse (Google → Bunua)…")
    start_url = fal_client.upload_file(START_IMAGE)
    end_url = fal_client.upload_file(END_IMAGE)

    result = fal_client.subscribe(
        M_VIDEO,
        arguments={
            "image_url": start_url,
            "end_image_url": end_url,
            "prompt": VIDEO_PROMPT,
            "duration": "10",
            "aspect_ratio": "9:16",
            "generate_audio": False,
        },
        with_logs=True,
        on_queue_update=lambda u, s=start: progress(s, u),
    )

    video_url = first_url(result, "video", "url", "output")
    if not video_url:
        sys.exit(f"❌ Pas de vidéo : {str(result)[:400]}")

    os.makedirs(os.path.dirname(SILENT_VIDEO), exist_ok=True)
    urllib.request.urlretrieve(video_url, SILENT_VIDEO)
    print(f"✅ vidéo muette → {SILENT_VIDEO}")
    return SILENT_VIDEO


# --- Étape 5 : mux ---
def mux(video: str, audio: str) -> str:
    print(f"\n🔗 Mux vidéo + voix clonée…")
    # -shortest : si l'audio est plus court que la vidéo, la vidéo est coupée à la fin de l'audio.
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-i", video, "-i", audio,
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-shortest", OUTPUT],
        check=True,
    )
    print(f"✅ Transition finale : {OUTPUT}")
    return OUTPUT


# --- Main ---
def main() -> int:
    if not os.getenv("FAL_KEY"):
        print("❌ Manque FAL_KEY.")
        return 1

    embed_url = get_or_create_embedding()
    narration_path = synthesize_narration(embed_url)
    silent_video_path = generate_silent_video()
    mux(silent_video_path, narration_path)

    print(f"\n👉 Pour le montage final :")
    print(f"   cp {OUTPUT} out/clips/transition.mp4")
    print( "   bash scripts/assemble_video.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
