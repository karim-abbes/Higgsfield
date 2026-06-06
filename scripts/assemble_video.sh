#!/usr/bin/env bash
# Assemble la vidéo UGC Bunua finale (9:16, ~22s) à partir des éléments générés.
#
# Entrées attendues dans out/ :
#   - bunua_clip_hook.mp4         (avatar, ~5s, audio natif Kling)
#   - google_profile.png          (capture fiche Google — boulangerie)
#   - bunua_clip_transition.mp4   (transition avant/après Kling, ~5s, muet)
#   - bunua_site.png              (capture site bunua généré)
#   - bunua_clip_cta.mp4          (avatar, ~5s, audio natif Kling)
#   - subtitles.srt               (optionnel : copié depuis assets/subtitles.srt)
#
# Sortie : out/bunua_ugc_final.mp4
#
# Prérequis : ffmpeg (brew install ffmpeg)
#
# Usage :
#   bash scripts/assemble_video.sh
set -euo pipefail

OUT_DIR="out"
FINAL="$OUT_DIR/bunua_ugc_final.mp4"

# Cible : 9:16, 1080x1920, 30fps.
W=1080; H=1920; FPS=30

# Durées des plans captures (en s). Le coût IA est nul ici.
DUR_GOOGLE=3
DUR_SITE=3

check() { [[ -f "$1" ]] || { echo "❌ Manque : $1"; exit 1; }; }

check "$OUT_DIR/bunua_clip_hook.mp4"
check "$OUT_DIR/bunua_clip_cta.mp4"
check "$OUT_DIR/google_profile.png"
check "$OUT_DIR/bunua_site.png"

# Transition Kling optionnelle (sinon transition simple crossfade au montage).
HAS_TRANSITION=0
if [[ -f "$OUT_DIR/bunua_clip_transition.mp4" ]]; then
  HAS_TRANSITION=1
fi

echo "🎬 Préparation des plans 9:16 ${W}x${H}@${FPS}fps…"

# 1) Normaliser les clips IA (scale + pad + fps + audio 48k stéréo).
norm_clip() {
  local in=$1 out=$2
  ffmpeg -y -loglevel error -i "$in" \
    -vf "scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:black,fps=${FPS}" \
    -c:v libx264 -pix_fmt yuv420p -preset veryfast -crf 20 \
    -c:a aac -ar 48000 -ac 2 -b:a 192k \
    "$out"
}

norm_clip "$OUT_DIR/bunua_clip_hook.mp4" "$OUT_DIR/_n_hook.mp4"
norm_clip "$OUT_DIR/bunua_clip_cta.mp4" "$OUT_DIR/_n_cta.mp4"
[[ $HAS_TRANSITION -eq 1 ]] && norm_clip "$OUT_DIR/bunua_clip_transition.mp4" "$OUT_DIR/_n_transition.mp4"

# 2) Ken Burns sur les captures (zoom lent + piste audio silencieuse).
kenburns() {
  local img=$1 out=$2 dur=$3
  local frames=$(( dur * FPS ))
  ffmpeg -y -loglevel error -loop 1 -t "$dur" -i "$img" -f lavfi -t "$dur" -i anullsrc=channel_layout=stereo:sample_rate=48000 \
    -vf "scale=8000:-1,zoompan=z='min(zoom+0.0015,1.15)':d=${frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=${W}x${H}:fps=${FPS}" \
    -c:v libx264 -pix_fmt yuv420p -preset veryfast -crf 20 \
    -c:a aac -ar 48000 -ac 2 -b:a 192k \
    -shortest "$out"
}

kenburns "$OUT_DIR/google_profile.png" "$OUT_DIR/_n_google.mp4" $DUR_GOOGLE
kenburns "$OUT_DIR/bunua_site.png" "$OUT_DIR/_n_site.mp4" $DUR_SITE

# 3) Concaténation dans l'ordre du brief.
CONCAT="$OUT_DIR/_concat.txt"
{
  echo "file '_n_hook.mp4'"
  echo "file '_n_google.mp4'"
  if [[ $HAS_TRANSITION -eq 1 ]]; then
    echo "file '_n_transition.mp4'"
  fi
  echo "file '_n_site.mp4'"
  echo "file '_n_cta.mp4'"
} > "$CONCAT"

echo "🧩 Concaténation…"
ffmpeg -y -loglevel error -f concat -safe 0 -i "$CONCAT" -c copy "$OUT_DIR/_merged.mp4"

# 4) Sous-titres (optionnel) : si subtitles.srt présent, on les brûle.
[[ -f "assets/subtitles.srt" && ! -f "$OUT_DIR/subtitles.srt" ]] && cp assets/subtitles.srt "$OUT_DIR/subtitles.srt"
if [[ -f "$OUT_DIR/subtitles.srt" ]]; then
  echo "💬 Incrustation des sous-titres…"
  ffmpeg -y -loglevel error -i "$OUT_DIR/_merged.mp4" \
    -vf "subtitles=$OUT_DIR/subtitles.srt:force_style='Fontname=Arial Black,Fontsize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=120'" \
    -c:a copy "$FINAL"
else
  cp "$OUT_DIR/_merged.mp4" "$FINAL"
  echo "ℹ️  Pas de subtitles.srt — fichier copié tel quel. Ajoute des sous-titres dans CapCut au besoin."
fi

# 5) Nettoyage des temporaires.
rm -f "$OUT_DIR"/_n_*.mp4 "$OUT_DIR/_merged.mp4" "$CONCAT"

echo "✅ Vidéo finale : $FINAL"
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$FINAL" | awk '{printf "⏱  Durée : %.1fs\n", $1}'
