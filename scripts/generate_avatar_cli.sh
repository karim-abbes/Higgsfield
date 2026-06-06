#!/usr/bin/env bash
# Génère l'avatar UGC Bunua (boulangère, 9:16) via le CLI officiel Higgsfield.
#
# Prérequis :
#   npm install -g @higgsfield/cli
#   higgsfield auth login
#
# Usage :
#   bash scripts/generate_avatar_cli.sh
#
# Astuce : voir les flags exacts d'un modèle avec
#   higgsfield generate create nano_banana_2 --help
set -euo pipefail

MODEL="nano_banana_2"   # Nano Banana Pro (photoréaliste). Alt: text2image_soul_v2

PROMPT="Vertical 9:16 UGC selfie photo, authentic iPhone front-camera look. A friendly \
30-year-old female bakery owner holding the phone at arm's length, filming herself inside \
a warm artisan bakery. Soft morning window light, slight handheld feel, genuine relaxed \
smile, looking into the lens. Wearing a flour-dusted apron over a simple top. Realistic \
skin texture and pores, no studio polish, candid and real. Background: pastry display case \
with bread and croissants, wooden counter, softly blurred. Shallow depth of field."

higgsfield generate create "$MODEL" \
  --prompt "$PROMPT" \
  --aspect_ratio 9:16 \
  --resolution 2k \
  --wait
