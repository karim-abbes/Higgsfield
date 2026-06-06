#!/usr/bin/env bash
# Anime l'avatar et le fait PARLER (lip-sync + voix) via Veo 3 (image -> vidéo).
# Veo génère ~8s : 1 clip par beat. On change juste $LINE pour chaque beat.
#
# Prérequis :
#   - CLI authentifié (higgsfield auth login)
#   - L'avatar sauvegardé en local : out/bunua_avatar_bakery.png
#
# Usage :
#   bash scripts/generate_talking_cli.sh
#
# ⚠️ Veo 3 consomme plus de crédits que l'image. On valide le Hook avant d'en faire 5.
set -euo pipefail

MODEL="veo3"
IMAGE="out/images/avatar.png"

# Réplique du beat courant (Hook par défaut). Voir brief/higgsfield-prompts.md (Étape B).
LINE="POV: you run a local business... but you still don't have a website."

PROMPT="9:16 vertical selfie UGC video. The same female bakery owner from the image holds \
her phone at arm's length, walking slowly through her warm bakery, talking directly to \
camera with friendly, slightly excited energy. Handheld natural motion. She says: '${LINE}' \
Authentic creator vibe, natural lighting, real human voice, no on-screen text, no music."

higgsfield generate create "$MODEL" \
  --image "$IMAGE" \
  --prompt "$PROMPT" \
  --wait
