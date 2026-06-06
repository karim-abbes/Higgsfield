#!/usr/bin/env python3
"""
Transition PARLANTE via fal.ai, avec CLONAGE AUTO de la voix du hook (Kling create-voice).

Workflow auto :
  1) Si out/voice_id.txt n'existe pas :
     - Extrait 15s d'audio du clip hook via ffmpeg
     - Upload sur fal.ai
     - Appelle fal-ai/kling-video/create-voice → renvoie un voice_id
     - Cache le voice_id dans out/voice_id.txt (1 fois suffit)
  2) Génère la transition (start_image = Google, end_image = Bunua)
     avec <<<voice_1>>> dans le prompt → Kling utilise la voix clonée.

Usage :
    export FAL_KEY="..."
    export HOOK_CLIP="out/bunua_clip_hook.mp4"     # source pour cloner la voix
    export START_IMAGE="out/google_profile.png"
    export END_IMAGE="out/bunua_site.png"
    python3 scripts/generate_transition_fal.py

Coût : voice control = ~$0.154/s × 10s = ~$1.54 (vs $1.26 sans clonage).
Clonage lui-même : généralement quelques cents, 1 seule fois.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request

import fal_client

MODEL_VIDEO = "fal-ai/kling-video/o3/standard/image-to-video"
MODEL_VOICE = "fal-ai/kling-video/create-voice"

HOOK_CLIP = os.getenv("HOOK_CLIP", "out/clips/hook.mp4")
CTA_CLIP = os.getenv("CTA_CLIP", "out/clips/cta.mp4")
START_IMAGE = os.getenv("START_IMAGE", "out/images/google_profile.png")
END_IMAGE = os.getenv("END_IMAGE", "out/images/bunua_site.png")

VOICE_ID_FILE = "out/voice/voice_id.txt"
VOICE_SAMPLE = "out/voice/voice_sample.wav"

NARRATION = (
    "Your customers Google you every day, but find nothing. "
    "Bunua turns your Google profile into a real website. "
    "In five minutes. No signup, no card."
)

PROMPT = (
    "9:16 vertical phone screen. Smooth satisfying UI reveal: a basic Google Business "
    "Profile listing slowly transforms into a clean, professional bakery website. "
    "Subtle zoom and modern polish, seamless transition, hands holding the phone at edges. "
    f"<<<voice_1>>> says with friendly, warm UGC creator energy: '{NARRATION}'. No music."
)

OUTPUT = f"out/clips/transition_{time.strftime('%Y%m%d_%H%M%S')}.mp4"


def upload(path: str) -> str:
    if path.startswith("http"):
        return path
    if not os.path.exists(path):
        sys.exit(f"❌ Image introuvable : {path}")
    print(f"  ⬆️  upload {path}…")
    return fal_client.upload_file(path)


def extract_audio_sample() -> str:
    """Concatène l'audio de hook + CTA (jusqu'à 30s) en un seul WAV via ffmpeg.
    Plus de data = meilleur clonage."""
    sources = [p for p in (HOOK_CLIP, CTA_CLIP) if os.path.exists(p)]
    if not sources:
        sys.exit(f"❌ Aucun clip source trouvé pour cloner ({HOOK_CLIP} ou {CTA_CLIP}).")
    print(f"🎤 Extraction audio depuis {', '.join(sources)} (max 30s)…")
    os.makedirs(os.path.dirname(VOICE_SAMPLE), exist_ok=True)

    inputs: list[str] = []
    for src in sources:
        inputs += ["-i", src]
    n = len(sources)
    filter_complex = (
        "".join(f"[{i}:a]" for i in range(n))
        + f"concat=n={n}:v=0:a=1[a]"
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[a]",
            "-t", "30",
            "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1",
            VOICE_SAMPLE,
        ],
        check=True,
    )
    return VOICE_SAMPLE


def get_or_create_voice_id() -> str:
    """Renvoie le voice_id en cache, ou clone la voix du hook si absent."""
    if os.path.exists(VOICE_ID_FILE):
        voice_id = open(VOICE_ID_FILE).read().strip()
        if voice_id:
            print(f"♻️  voice_id en cache : {voice_id}")
            return voice_id

    sample = extract_audio_sample()
    sample_url = fal_client.upload_file(sample)
    print(f"  ⬆️  voice sample uploadé")
    print("🧬 Clonage de la voix via Kling create-voice…")

    result = fal_client.subscribe(
        MODEL_VOICE,
        arguments={"voice_url": sample_url},
        with_logs=True,
        on_queue_update=lambda u: print(f"  · {getattr(u, 'status', u)}"),
    )

    # Le voice_id peut être à la racine ou dans un sous-objet selon la réponse.
    voice_id = None
    if isinstance(result, dict):
        voice_id = result.get("voice_id") or (result.get("voice") or {}).get("voice_id")
    if not voice_id:
        sys.exit(f"❌ Pas de voice_id dans la réponse : {str(result)[:400]}")

    os.makedirs(os.path.dirname(VOICE_ID_FILE), exist_ok=True)
    with open(VOICE_ID_FILE, "w") as f:
        f.write(voice_id)
    print(f"✅ voice_id sauvegardé → {VOICE_ID_FILE} ({voice_id})")
    return voice_id


def main() -> int:
    if not os.getenv("FAL_KEY"):
        print("❌ Manque FAL_KEY.")
        return 1

    voice_id = get_or_create_voice_id()

    start = time.time()
    print("\n🎬 Transition (Google → Bunua) avec voix clonée…")
    start_url = upload(START_IMAGE)
    end_url = upload(END_IMAGE)

    # On essaie 2 conventions pour passer le voice_id selon le schéma exact.
    payload_base = {
        "image_url": start_url,
        "end_image_url": end_url,
        "prompt": PROMPT,
        "duration": "10",
        "aspect_ratio": "9:16",
        "generate_audio": True,
    }

    last_err = None
    for key in ("voice_ids", "voice_id_list"):
        try:
            result = fal_client.subscribe(
                MODEL_VIDEO,
                arguments={**payload_base, key: [voice_id]},
                with_logs=True,
                on_queue_update=lambda u: print(
                    f"  · {time.time()-start:5.1f}s — {getattr(u, 'status', u)}"
                ),
            )
            break
        except Exception as e:  # noqa: BLE001
            print(f"  · champ '{key}' refusé ({type(e).__name__})")
            last_err = e
    else:
        sys.exit(f"❌ Aucun champ voice_ids accepté : {last_err}")

    video_url = (
        result.get("video", {}).get("url") if isinstance(result, dict) else None
    )
    if not video_url:
        print("⚠️ Réponse :", str(result)[:400])
        return 2

    print(f"✅ {time.time()-start:.1f}s — {video_url}")
    os.makedirs("out/clips", exist_ok=True)
    urllib.request.urlretrieve(video_url, OUTPUT)
    print(f"💾 {OUTPUT}")
    print(f"\n👉 Pour le montage :")
    print(f"   cp {OUTPUT} out/clips/transition.mp4")
    print( "   bash scripts/assemble_video.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
