---
name: higgsfield
description: Référence pratique Higgsfield (génération d'images/avatars) pour ce projet UGC. Lire AVANT tout appel Higgsfield pour éviter les erreurs coûteuses.
when-to-use: Génération d'avatar/image via Higgsfield, choix de modèle, ou erreur "Model not found". Lire en premier avant de coder ou débugger un appel Higgsfield.
---

# Référence Higgsfield — projet UGC Bunua

## ⚠️ LE PIÈGE QUI A COÛTÉ DU TEMPS : SDK Python cassé → utiliser la CLI

Sur ce compte, **`higgsfield_client.subscribe(...)` renvoie "Model not found" pour
TOUS les modèles** (noms courts ET format long `org/modèle/version/tâche`). N'insiste
pas avec le SDK Python : **pilote la CLI `higgsfield`** (qui, elle, fonctionne).

```python
# ✅ CE QUI MARCHE : subprocess sur la CLI
cmd = ["higgsfield", "generate", "create", model,        # model = nom COURT
       "--prompt", PROMPT, "--aspect_ratio", "9:16",
       "--resolution", "2k", "--wait", "--json"]
proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
# --wait bloque et imprime l'URL résultat ; --json = sortie machine.
# Parser : json.loads(stdout) puis chercher l'URL, sinon regex https?://... (préférer .png/.jpg)
```

- **Auth CLI** : `higgsfield auth login` (une fois). La CLI doit être authentifiée
  (vérifier avec `higgsfield model list`). Le `.env` HF_KEY sert au SDK, pas à la CLI.
- **Noms de modèles = noms COURTS** de `higgsfield model list` (PAS le format long).

## Modèles image utiles (noms courts CLI, cf. `higgsfield model list`)

| Nom court | Modèle | Usage |
|---|---|---|
| `nano_banana_2` | Nano Banana Pro | Photoréaliste — **utilisé pour l'avatar host** |
| `seedream_v4_5` / `seedream_v5_lite` | Seedream | Photoréaliste, alternatives |
| `flux_2` | FLUX.2 | Alternative |
| `gpt_image_2`, `grok_image`, `openai_hazel` | divers | Autres options image |

Modèles **vidéo** dispo aussi (veo3, kling2_6, kling3_0, wan2_6/2_7, seedance…) mais
pour la vidéo parlante on passe par **Replicate** (voir skill `replicate`).

## Flags `higgsfield generate create`
`--prompt` · `--aspect_ratio` (9:16, 16:9, 3:4) · `--resolution` (2k, 1080p) ·
`--quality` · `--wait` (bloque + imprime l'URL) · `--wait-timeout` (déf 10m) · `--json`.

## Convention projet
- Avatar → `out/images/avatar.png` **+ on persiste l'URL CDN source** dans
  `out/images/avatar.png.url.txt` → permet aux étapes Replicate/Kling de passer
  l'image PAR URL (récup côté serveur, pas d'upload → pas de timeout).
- L'URL CDN Higgsfield (cloudfront) peut expirer → si un 403 survient plus tard,
  régénérer ou réhéberger l'image.

## Anti-patterns
- ❌ Utiliser `higgsfield_client.subscribe()` (cassé ici) → CLI.
- ❌ Passer le format `org/modèle/version/tâche` à la CLI → elle veut les noms courts.
- ❌ Régénérer l'avatar pour "réparer" un souci d'upload → ça change le visage. Persister l'URL à la place.
