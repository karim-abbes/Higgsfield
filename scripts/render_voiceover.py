#!/usr/bin/env python3
"""
Voix off d'un épisode Makeover : lit le script JSON (render_script.py) et
synthétise UN audio par beat via Qwen3-TTS, avec une voix d'hôte STABLE.

Pourquoi par beat : les beats `host_oncam` piloteront le lip-sync de l'avatar
(Wan S2V), les beats `voiceover` se posent sur le reveal. Le montage a besoin des
deux séparément, avec leur DURÉE RÉELLE (mesurée ici par ffprobe) — ça remplace
les estimations à 2,6 mots/s de render_script.py.

Voix de l'hôte (récurrente) : clonée/conçue UNE fois → empreinte mise en cache
dans out/voice/host/ → réutilisée par tous les épisodes (cohérence de marque).

Pipeline (fal.ai, cf. skill fal-ai) :
  voix hôte = empreinte en cache  ||  --sample (clone)  ||  voice-design (défaut)
  puis : qwen-3-tts/text-to-speech/1.7b (texte + empreinte) → MP3 par beat

Usage (⚠️ réseau fal requis → lancer EN LOCAL) :
    export FAL_KEY="key_id:key_secret"
    python3 scripts/render_voiceover.py out/scripts/austin-plumbing-drain-pros.script.json
    # voix custom : --sample chemin_ou_url.wav   |   --voice <nom_predefini>
    #               --design "energetic friendly american host"   |   --refresh-voice
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

import fal_client

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_google_card import load_dotenv  # noqa: E402

M_CLONE = "fal-ai/qwen-3-tts/clone-voice/1.7b"
M_TTS = "fal-ai/qwen-3-tts/text-to-speech/1.7b"
M_DESIGN = "fal-ai/qwen-3-tts/voice-design/1.7b"

# Empreinte de l'hôte récurrent, partagée par tous les épisodes.
HOST_DIR = "out/voice/host"
EMBED_CACHE = os.path.join(HOST_DIR, "embedding_url.txt")

# Persona vocale par défaut (avatar IA → pas de vraie voix : on la conçoit).
DEFAULT_VOICE_DESIGN = (
    "Energetic, friendly, confident American male host in his early thirties, "
    "warm and upbeat, clear diction, like a popular short-form video creator."
)


# ───────────────────────── Helpers fal ─────────────────────────
def first_url(result, *keys):
    """1ère clé non-vide d'une réponse fal (parfois imbriquée sous .url)."""
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
    print(f"    · {time.time()-start:5.1f}s — {getattr(u, 'status', u)}")


def _subscribe_trying(model, base, candidate_keys, value, label):
    """Appelle `model` en essayant plusieurs noms de champ (schémas fal variables)."""
    start = time.time()
    last_err = None
    for key in candidate_keys:
        try:
            return fal_client.subscribe(
                model, arguments={**base, key: value}, with_logs=True,
                on_queue_update=lambda u, s=start: progress(s, u),
            )
        except Exception as e:  # noqa: BLE001
            print(f"    · champ '{key}' refusé ({type(e).__name__})")
            last_err = e
    sys.exit(f"❌ {label} : aucun champ accepté ({last_err}).")


# ───────────────────────── Voix de l'hôte ─────────────────────────
def clone_to_embedding(audio_ref: str) -> str:
    """Clone un échantillon (chemin local ou URL) → URL d'empreinte."""
    url = audio_ref if audio_ref.startswith("http") else fal_client.upload_file(audio_ref)
    print("🧬 Clonage de la voix…")
    res = _subscribe_trying(M_CLONE, {}, ("audio_url", "voice_url", "input_audio_url"),
                            url, "Clonage voix")
    embed = first_url(res, "speaker_embedding", "speaker_embedding_url", "embedding_url",
                      "voice_url", "audio", "output", "url")
    if not embed:
        sys.exit(f"❌ Pas d'empreinte dans la réponse clone : {str(res)[:300]}")
    return embed


# Phrase d'exemple lue par la voix conçue (l'endpoint exige `prompt` ET `text`).
DESIGN_SAMPLE_TEXT = (
    "Hey — check this out. Your business deserves a real website, "
    "and I'm about to show you exactly how."
)


def design_to_embedding(description: str) -> str:
    """Conçoit une voix depuis une description → URL d'empreinte.
    voice-design exige `prompt` (description) ET `text` (phrase à dire). Si la
    réponse ne rend qu'un audio, on le clone pour obtenir l'empreinte réutilisable."""
    print(f"🎨 Conception de la voix : « {description[:60]}… »")
    start = time.time()
    try:
        res = fal_client.subscribe(
            M_DESIGN,
            arguments={"prompt": description, "text": DESIGN_SAMPLE_TEXT},
            with_logs=True, on_queue_update=lambda u, s=start: progress(s, u),
        )
    except Exception as e:  # noqa: BLE001
        sys.exit(f"❌ Voice-design a échoué : {type(e).__name__} {e}")

    embed = first_url(res, "speaker_embedding", "speaker_embedding_url", "embedding_url")
    if embed:
        return embed
    audio = first_url(res, "audio", "audio_url", "url", "output")
    if audio:
        print("  · voice-design a rendu un audio → clonage pour l'empreinte")
        return clone_to_embedding(audio)
    sys.exit(f"❌ Réponse voice-design inattendue : {str(res)[:400]}")


def resolve_voice(args, embed_cache: str) -> tuple[dict, str]:
    """Renvoie (kwargs TTS de voix, description). Précédence : --voice > cache >
    --sample > voice-design. L'empreinte créée est mise en cache (par épisode)."""
    if args.voice:
        return {"voice": args.voice}, f"voix prédéfinie « {args.voice} »"

    if os.path.exists(embed_cache) and not args.refresh_voice:
        url = open(embed_cache).read().strip()
        if url.startswith("http"):
            print(f"♻️  Empreinte en cache : …{url[-32:]}")
            return {"speaker_voice_embedding_file_url": url}, "empreinte en cache"

    embed = clone_to_embedding(args.sample) if args.sample else design_to_embedding(args.design)
    os.makedirs(os.path.dirname(embed_cache), exist_ok=True)
    with open(embed_cache, "w") as f:
        f.write(embed)
    print(f"✅ Empreinte sauvegardée → {embed_cache}")
    return {"speaker_voice_embedding_file_url": embed}, "nouvelle empreinte"


# ───────────────────────── Synthèse + mesure ─────────────────────────
def synth(text: str, voice_kwargs: dict, out_path: str) -> None:
    res = fal_client.subscribe(
        M_TTS, arguments={"text": text, **voice_kwargs}, with_logs=True,
        on_queue_update=lambda u, s=time.time(): progress(s, u),
    )
    audio = first_url(res, "audio", "audio_url", "url", "output")
    if not audio:
        sys.exit(f"❌ Pas d'audio dans la réponse TTS : {str(res)[:300]}")
    urllib.request.urlretrieve(audio, out_path)


def audio_duration(path: str) -> float | None:
    """Durée réelle (s) via ffprobe."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path],
            capture_output=True, text=True, check=True,
        )
        return round(float(out.stdout.strip()), 2)
    except Exception:  # noqa: BLE001
        return None


# ───────────────────────── Main ─────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description="Voix off d'un épisode (Qwen3-TTS).")
    ap.add_argument("script", help="Chemin du script JSON (render_script.py)")
    ap.add_argument("--sample", help="Échantillon voix à cloner (chemin local ou URL)")
    ap.add_argument("--voice", help="Nom de voix prédéfinie Qwen (au lieu d'une empreinte)")
    ap.add_argument("--design", default=DEFAULT_VOICE_DESIGN,
                    help="Description de la voix à concevoir (si ni --voice ni --sample ni cache)")
    ap.add_argument("--refresh-voice", action="store_true",
                    help="Ignore l'empreinte en cache et en recrée une")
    ap.add_argument("--out-dir", help="Dossier de sortie (défaut out/voice/<slug>)")
    args = ap.parse_args()

    load_dotenv()
    if not os.getenv("FAL_KEY"):
        sys.exit("❌ Manque FAL_KEY (env ou .env).")
    if not os.path.exists(args.script):
        sys.exit(f"❌ Script introuvable : {args.script}")

    with open(args.script) as f:
        script = json.load(f)
    beats = script.get("beats") or []
    slug = os.path.basename(args.script).replace(".script.json", "")
    out_dir = args.out_dir or os.path.join("out", "voice", slug)
    os.makedirs(out_dir, exist_ok=True)

    print(f"🎬 {script.get('business', slug)} · {len(beats)} beats")
    # Empreinte par épisode (cohérence intra-épisode avec la voix Kling de hook/CTA).
    embed_cache = os.path.join(out_dir, "embedding_url.txt")
    voice_kwargs, voice_desc = resolve_voice(args, embed_cache)
    print(f"🎙  Voix : {voice_desc}\n")

    manifest = []
    for i, b in enumerate(beats, 1):
        name = f"{i:02d}_{b['beat']}.mp3"
        path = os.path.join(out_dir, name)
        print(f"[{i}/{len(beats)}] {b['beat']} ({b['type']}) — « {b['text'][:50]}… »")
        synth(b["text"], voice_kwargs, path)
        dur = audio_duration(path)
        est = b.get("duration_s")
        flag = ""
        if dur and est and abs(dur - est) >= 1.5:
            flag = f"  ⚠️ écart vs estimation ({est}s)"
        print(f"    ✅ {name}  {dur}s{flag}")
        manifest.append({
            "beat": b["beat"], "type": b["type"], "text": b["text"],
            "audio": path, "duration_s": dur, "cues": b.get("cues", []),
        })

    real_total = round(sum(m["duration_s"] for m in manifest if m["duration_s"]), 2)
    out = {
        "business": script.get("business"), "lang": script.get("lang"),
        "hook_variant": script.get("hook_variant"), "url": script.get("url"),
        "voice": voice_desc, "real_total_duration_s": real_total, "beats": manifest,
    }
    manifest_path = os.path.join(out_dir, "voiceover.manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n⏱  Durée réelle totale : {real_total}s "
          f"(estimée {script.get('total_duration_s')}s)")
    print(f"✅ Manifest → {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
