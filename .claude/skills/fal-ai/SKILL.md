---
name: fal-ai
description: Référence pratique fal.ai pour ce projet UGC (Kling video, Qwen3-TTS, voice clone). Lire AVANT de coder un nouvel appel fal pour éviter les essais-erreurs coûteux.
when-to-use: Tout appel à un endpoint fal.ai (kling-video, qwen-3-tts, create-voice, etc.). Lire en premier si l'utilisateur demande une nouvelle génération vidéo/audio ou un changement d'endpoint.
---

# Référence fal.ai — projet UGC Bunua

## Conventions globales

- **Auth** : `export FAL_KEY="key_id:key_secret"`. Le SDK Python `fal_client` lit automatiquement cette variable.
- **Upload** : `fal_client.upload_file(path)` renvoie une URL CDN utilisable comme input. Pas besoin d'héberger ailleurs.
- **Long polling** : `fal_client.subscribe(model, arguments=..., with_logs=True, on_queue_update=cb)` bloque jusqu'à la fin. `fal_client.submit(...)` pour async.
- **Dashboard requêtes** : https://fal.ai/dashboard (les requêtes apparaissent là, pas sur `/requests`).

## Sortie type des modèles

Le format de retour varie. **Toujours fouiller plusieurs clés** :
```python
def first_url(result, *keys):
    if not isinstance(result, dict): return None
    for k in keys:
        v = result.get(k)
        if isinstance(v, str) and v.startswith("http"): return v
        if isinstance(v, dict) and isinstance(v.get("url"), str): return v["url"]
    return None

# Exemples : video URL → result["video"]["url"]
#            audio URL → result["audio"]["url"] ou result["audio_url"]
#            embedding → souvent result["voice_url"] ou result["speaker_embedding_url"]
```

---

## Endpoints VIDEO — Kling

### `fal-ai/kling-video/o3/standard/image-to-video` (= Omni Standard)
Notre modèle principal pour ce projet (multi-shot ou simple start/end).

**Prix** : $0.084/s sans audio · **$0.126/s avec audio** · $0.154/s avec voice control.

**Inputs validés** :
| Champ | Type | Requis | Notes |
|---|---|---|---|
| `image_url` | string (URL) | ✅ | Frame de départ. |
| `end_image_url` | string (URL) | non | Frame de fin. **EXCLUSIF avec `multi_prompt`** (erreur 422 sinon). |
| `prompt` | string | ✅ (hors multi_prompt) | Description scène + ce qui est dit. |
| `duration` | string (`"1"`...`"15"`) | non | ⚠️ **STRING**, pas int. |
| `aspect_ratio` | string | non | `"9:16"`, `"16:9"`, `"1:1"`. |
| `generate_audio` | bool | non | True = audio natif Kling. |
| `multi_prompt` | array | non | Voir section dédiée. |
| `shot_type` | string | **requis avec multi_prompt** | `"customize"` typiquement. |
| `elements` | array | non | Personnages réutilisables. Voir section. |
| `reference_image_urls` | array[string] | non | Style/refs, accessibles `@Image1`, `@Image2` dans le prompt. |

**Multi-shot** :
```python
"multi_prompt": [
    {"index": 1, "duration": "2", "prompt": "..."},
    {"index": 2, "duration": "3", "prompt": "..."},
    {"index": 3, "duration": "5", "prompt": "..."},
],
"shot_type": "customize",
```
- Max 6 plans.
- `duration` reste **string**.
- `multi_prompt` ne marche pas avec `end_image_url`.

**Elements** (perso/objet récurrent) :
```python
"elements": [{"frontal_image_url": "<url>"}],
# référencer dans prompts : "@Element1 ..."
```

**Reference images** :
```python
"reference_image_urls": [google_url, bunua_url],
# référencer : "@Image1", "@Image2"
```
⚠️ **Limite générative** : `reference_image_urls` = **inspiration de style**, pas pixel-perfect.
Pour un écran d'UI à respecter à la lettre, le modèle hallucine du gibberish.
**Solution** : passer l'image en `image_url` ou `end_image_url` (ancrage strict), pas en référence.

### `fal-ai/kling-video/v3/standard/image-to-video` & `v3/pro`
Variantes non-Omni. Standard $0.126/s audio. Pro $0.336/s audio.
Multi-shot moins documenté → préférer `o3/standard` pour le multi-shot.

### `fal-ai/kling-video/v3/4k/image-to-video`
Pro 4K, très cher. Ignorer pour de l'UGC mobile.

---

## Endpoint VOICE — Kling create-voice

### `fal-ai/kling-video/create-voice`
Audio → `voice_id` à utiliser comme `<<<voice_1>>>` dans un prompt **Kling vidéo**.

```python
result = fal_client.subscribe("fal-ai/kling-video/create-voice", {
    "voice_url": "<url audio 5-30s, wav/mp3>",
})
voice_id = result["voice_id"]  # ex: "829877809978941442"
```

⚠️⚠️⚠️ **LIMITATION CRITIQUE confirmée** :
> *"Voice binding is only supported for video elements, not image elements."*

Sur `image-to-video` **avec des images** (pas un élément vidéo), passer `voice_ids` ou `<<<voice_1>>>` dans le prompt **N'EST PAS APPLIQUÉ** — le voice_id est silencieusement ignoré et Kling génère une voix narrateur indépendante.

**Workaround** : utiliser Qwen3-TTS (ci-dessous) puis mux ffmpeg.

---

## Endpoints TTS — Qwen3-TTS

### `fal-ai/qwen-3-tts/clone-voice/1.7b` (audio → empreinte)
Prend un échantillon audio (3-30s, single voice, propre). Sort une **empreinte safetensors** (URL) à passer au TTS.

```python
result = fal_client.subscribe("fal-ai/qwen-3-tts/clone-voice/1.7b", {
    "audio_url": "<url wav/mp3>",
})
# Sortie réelle vérifiée :
# {"speaker_embedding": {"url": "...safetensors", "content_type": "...", ...}}
embed_url = result["speaker_embedding"]["url"]
```

Variantes : `0.6b` (plus rapide, moins qualité).

### `fal-ai/qwen-3-tts/text-to-speech/1.7b` (texte + empreinte → MP3)
```python
result = fal_client.subscribe("fal-ai/qwen-3-tts/text-to-speech/1.7b", {
    "text": "narration ici…",
    "speaker_voice_embedding_file_url": embed_url,  # nom EXACT vérifié
    # optionnel : "reference_text": "<même texte que l'audio cloné>"
})
audio_url = first_url(result, "audio", "audio_url")
```
⚠️ Le champ s'appelle `speaker_voice_embedding_file_url` (et non speaker_embedding_url).
Alternative : `voice` (voix prédéfinie) au lieu de l'embedding.

### `fal-ai/qwen-3-tts/voice-design/1.7b`
Crée une voix à partir d'une description. ⚠️ **Exige DEUX champs** : `prompt`
(la description de la voix) **ET** `text` (une phrase d'exemple à dire). Passer un
seul → 422 `Field required`. Sortie : audio (et/ou embedding) ; si seulement un
audio, le **cloner** (clone-voice) pour obtenir une empreinte réutilisable.
```python
fal_client.subscribe(M_DESIGN, {"prompt": "<description voix>", "text": "<phrase exemple>"})
```

---

## Endpoint OPEN-SOURCE auto-hébergeable — Wan 2.2 S2V

### `fal-ai/wan/v2.2-14b/speech-to-video` (audio-driven talking avatar)
Image + audio → avatar qui parle. **Le lip-sync est piloté par l'audio fourni**
→ contrôle 100% de la voix (donner notre TTS Qwen3). Modèle **open source** (poids sur
HuggingFace `Wan-AI/Wan2.2-S2V-14B`) → candidat pour pipeline local sur RTX 4090.

**Prix fal** : ~$0.15/s (580p) · ~$0.20/s (720p). Jusqu'à 10 min en 480p.

```python
result = fal_client.subscribe("fal-ai/wan/v2.2-14b/speech-to-video", {
    "image_url": "<url avatar>",
    "audio_url": "<url audio qui pilote le lip-sync>",
    "prompt": "<description scène/action>",  # ⚠️ REQUIS (422 'Field required' sinon)
    "resolution": "580p",   # ou "720p"
})
video_url = result["video"]["url"]
```

⚠️⚠️ **VERDICT projet : Wan S2V ÉCARTÉ.** Testé sur notre avatar → **lip-sync décroché**
(pas synchro, moins naturel que Kling vidéo+voix). Et **lent sur fal** (>10 min,
305s d'inférence observés). Pour la vidéo parlante : **Kling vidéo+voix sur Replicate**
(hook/CTA) puis **voix clonée** sur la transition. Garder Wan seulement comme piste
si on trouve un modèle de lip-sync nettement meilleur (ex: lipsync dédié).

Aussi sur Replicate : `wan-video/wan-2.2-s2v` (inputs `image_url`, `audio_url`, `resolution`).

---

## Limitations à connaître

| Limitation | Effet | Workaround |
|---|---|---|
| `reference_image_urls` hallucine les UI | Texte d'écran inventé | Mettre l'image en `image_url`/`end_image_url`, pas en référence. |
| `<<<voice_1>>>` ignoré sur image-to-video | Voix différente du clone | Qwen3-TTS + ffmpeg mux. |
| `multi_prompt` + `end_image_url` exclusifs | 422 | Choisir l'un ou l'autre. |
| `duration` doit être string | 422 | `"5"` pas `5`. |
| Network bloqué dans certains environnements | 403 | Lancer en local. |

---

## Pipeline du projet (état actuel)

1. **Avatar** image (Higgsfield CLI `nano_banana_2`) → `out/images/avatar.png`
2. **Avatar v2** pose différente (image-to-image Higgsfield)
3. **Hook** parlé : `kwaivgi/kling-v3-video` sur Replicate, avatar v1 → `out/clips/hook.mp4`
4. **CTA** parlé : idem sur Replicate, avatar v2 → `out/clips/cta.mp4`
5. **Transition** : pipeline 5 étapes (voir `scripts/generate_transition_fal.py`)
   - clone voix hook+CTA via Qwen3
   - TTS narration avec voix clonée
   - vidéo silencieuse Google→Bunua via Kling
   - mux audio+vidéo via ffmpeg
   → `out/clips/transition.mp4`
6. **Montage final** : `bash scripts/assemble_video.sh` → `out/bunua_ugc_final.mp4`

## Coûts observés

| Action | Coût |
|---|---|
| Hook ou CTA (Kling v3 Replicate, 5s, audio) | ~$1.68 |
| Transition silencieuse (Kling Omni Std, 10s, no audio) | ~$0.84 |
| Voice clone Qwen3 | quelques cents |
| TTS narration Qwen3 (~50 chars) | quelques cents |
| **Total pipeline transition (Qwen3+Kling)** | **~$0.90** |
| Multi-shot complet (Kling Omni Std, 10s, audio) | ~$1.26 |

## Convention de nommage du repo

- Inputs PNG → `out/images/`
- Clips Kling utilisés au montage → `out/clips/{hook,transition,cta}.mp4`
- Variantes horodatées → `out/archive/`
- Cache voix (embedding URL, sample WAV) → `out/voice/`
- Vidéo finale assemblée → `out/bunua_ugc_final.mp4`

## Anti-patterns à éviter

- ❌ Régénérer un clip sans timestamp dans le nom → écrasement de l'existant.
- ❌ Hardcoder un endpoint sans avoir vérifié son schéma ici d'abord.
- ❌ Promettre "voix identique" sans utiliser le pipeline Qwen3 (voir limitation).
- ❌ Mettre un screenshot UI dans `reference_image_urls` en espérant qu'il soit pixel-perfect.
- ❌ Passer `duration: 5` (int) à un endpoint Kling.
