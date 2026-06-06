#!/usr/bin/env bash
# Range out/ en sous-dossiers : images/, clips/, voice/, archive/.
# Idempotent : peut être relancé sans casse, déplace seulement ce qui n'est pas
# déjà à sa place.
#
# Usage : bash scripts/cleanup_out.sh
set -euo pipefail

cd "$(dirname "$0")/../out" 2>/dev/null || { echo "❌ out/ introuvable"; exit 1; }

mkdir -p images clips voice archive

mv_if() { [[ -f "$1" ]] && { mv "$1" "$2"; echo "  → $1 → $2"; } || true; }

echo "📁 Tri en cours…"

# --- Images / avatars (versionnés)
mv_if "bunua_avatar_bakery_v2.png" "images/avatar.png"
mv_if "bunua_avatar_bakery.png" "images/avatar_v1.png"
mv_if "google_profile.png" "images/google_profile.png"
mv_if "bunua_site.png" "images/bunua_site.png"

# --- Clips actifs (les dernières versions, utilisées au montage)
mv_if "bunua_clip_hook.mp4" "clips/hook.mp4"
mv_if "bunua_clip_cta.mp4" "clips/cta.mp4"
mv_if "bunua_clip_transition.mp4" "clips/transition.mp4"

# --- Cache de voix clonée
mv_if "voice_id.txt" "voice/voice_id.txt"
mv_if "voice_sample.wav" "voice/voice_sample.wav"

# --- Archive : essais horodatés / tests
for f in bunua_clip_multishot_*.mp4 bunua_clip_transition_2*.mp4 \
         bunua_clip_cta_*.mp4 bunua_clip_hook_*.mp4 \
         test_fal_*.mp4; do
  [[ -f "$f" ]] && { mv "$f" "archive/"; echo "  → $f → archive/"; }
done

# --- Fichiers temporaires de montage : suppression
rm -f subtitles.srt _concat.txt _merged.mp4 _n_*.mp4 2>/dev/null || true

# --- Petit pense-bête à la racine
cat > README.txt <<'EOF'
Structure :
  images/   PNG sources : avatar + captures écran
  clips/    Les 3 clips IA utilisés au montage (hook/transition/cta)
  voice/    Cache du clonage de voix (voice_id, échantillon audio)
  archive/  Anciens essais (régénérations, tests)

  bunua_ugc_final.mp4   La vidéo finale assemblée.
EOF

echo ""
echo "✅ out/ réorganisé."
echo ""
ls -la
