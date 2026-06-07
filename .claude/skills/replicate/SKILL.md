---
name: replicate
description: Référence pratique Replicate (Kling vidéo parlante, lip-sync) pour ce projet UGC. Lire AVANT tout appel Replicate pour éviter les erreurs coûteuses.
when-to-use: Génération de clips parlants (hook/CTA) via Kling sur Replicate, ou tout appel replicate.run. Lire en premier avant de coder/débugger.
---

# Référence Replicate — projet UGC Bunua

## Pourquoi Replicate
Paiement à l'usage, pas de mur "Pro plan", et **plus fiable/prévisible que fal**
pour la vidéo (fal a montré >10 min d'attente sur Wan). Auth : `REPLICATE_API_TOKEN`
(replicate.com/account/api-tokens) dans `.env`. **Charger le `.env`** dans le script.

## Modèle clips parlants : `kwaivgi/kling-v3-video`
Avatar (image) → vidéo parlante, **voix générée nativement par Kling** (~$0.14/s, audio).
C'est l'approche RETENUE pour hook/CTA (plus naturel/synchro que l'audio externe).

```python
out = replicate.run("kwaivgi/kling-v3-video", input={
    "prompt": build_prompt(line),   # décrit la scène + "He says: '<réplique>'"
    "start_image": image_input(),   # ⚠️ ANCRE l'identité (le visage de l'avatar)
    "duration": 5,                  # int
    "aspect_ratio": "9:16",
    "generate_audio": True,
})
url = str(out[0] if isinstance(out, list) else out)
```

## ⚠️⚠️ PIÈGES QUI ONT COÛTÉ DE L'ARGENT

1. **Le bon champ image = `start_image`** (il ancre le visage). Le champ `image`
   est accepté par le schéma mais **ignore l'avatar → fabrique un faux visage**.
   → Ne JAMAIS faire de fallback `start_image` → `image` : ça produit en silence
   un clip avec une autre tête (argent perdu). `start_image` uniquement + retries.

2. **Passer l'image PAR URL, pas en upload.** Uploader un fichier local (open(f))
   peut timeout ("The read operation timed out") → le clip échoue ou part en fallback.
   → Donner une **URL** : Replicate la récupère côté serveur, pas d'upload, pas de timeout.
   Le projet persiste l'URL de l'avatar dans `out/images/avatar.png.url.txt`
   (cf. skill `higgsfield`) ; `image_input()` la lit en priorité.

3. **`generate_audio=True`** sinon vidéo muette. La voix Kling sert ensuite de
   source pour le **clonage** (Qwen3) → voix off de la transition (skill `fal-ai`).

## Architecture vidéo retenue (rappel)
- **hook / CTA** = `kwaivgi/kling-v3-video` (vidéo + voix Kling), avatar via `start_image` URL.
- **transition fiche→site** = vidéo muette + **voix clonée** (Qwen3) muxée (fal).
- ❌ Wan S2V (audio externe → avatar parlant) **écarté** : lip-sync décroché (cf. `fal-ai`).

## Texte des répliques
Lu depuis le **script JSON** de l'épisode (`render_script.py`) via `--script`,
PAS hardcodé. Le beat `hook`/`cta` fournit le `text` exact.

## Anti-patterns
- ❌ Fallback de champ image (`start_image`→`image`) → faux visage, argent perdu.
- ❌ Uploader l'image locale au lieu d'une URL → timeouts.
- ❌ Oublier de charger `.env` → "Manque REPLICATE_API_TOKEN".
- ❌ `duration` en string → c'est un **int** ici (≠ Kling sur fal qui veut une string).
