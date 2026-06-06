#!/usr/bin/env bash
# Assemble la vidéo UGC Bunua finale (9:16, ~20s) en concaténant UNIQUEMENT
# les 3 clips IA générés (pas de Ken Burns, pas de captures statiques).
#
# Entrées attendues dans out/ :
#   - bunua_clip_hook.mp4         (avatar, ~5s, audio natif Kling)
#   - bunua_clip_transition.mp4   (transition parlante, ~10s, audio natif Kling)
#   - bunua_clip_cta.mp4          (avatar, ~5s, audio natif Kling)
#   - subtitles.srt               (optionnel : copié depuis assets/)
#
# Sortie : out/bunua_ugc_final.mp4
#
# Prérequis : ffmpeg (brew install ffmpeg)
set -euo pipefail

OUT_DIR="out"
FINAL="$OUT_DIR/bunua_ugc_final.mp4"

W=1080; H=1920; FPS=30

check() { [[ -f "$1" ]] || { echo "❌ Manque : $1"; exit 1; }; }

check "$OUT_DIR/bunua_clip_hook.mp4"
check "$OUT_DIR/bunua_clip_transition.mp4"
check "$OUT_DIR/bunua_clip_cta.mp4"

echo "🎬 Normalisation des 3 clips (${W}x${H}@${FPS}fps, audio 48k stéréo)…"

norm_clip() {
  local in=$1 out=$2
  ffmpeg -y -loglevel error -i "$in" \
    -vf "scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:black,fps=${FPS}" \
    -c:v libx264 -pix_fmt yuv420p -preset veryfast -crf 20 \
    -c:a aac -ar 48000 -ac 2 -b:a 192k \
    "$out"
}

norm_clip "$OUT_DIR/bunua_clip_hook.mp4" "$OUT_DIR/_n_hook.mp4"
norm_clip "$OUT_DIR/bunua_clip_transition.mp4" "$OUT_DIR/_n_transition.mp4"
norm_clip "$OUT_DIR/bunua_clip_cta.mp4" "$OUT_DIR/_n_cta.mp4"

# Concaténation.
CONCAT="$OUT_DIR/_concat.txt"
{
  echo "file '_n_hook.mp4'"
  echo "file '_n_transition.mp4'"
  echo "file '_n_cta.mp4'"
} > "$CONCAT"

echo "🧩 Concaténation…"
ffmpeg -y -loglevel error -f concat -safe 0 -i "$CONCAT" -c copy "$OUT_DIR/_merged.mp4"

# Sous-titres (optionnel).
[[ -f "assets/subtitles.srt" && ! -f "$OUT_DIR/subtitles.srt" ]] && cp assets/subtitles.srt "$OUT_DIR/subtitles.srt"
if [[ -f "$OUT_DIR/subtitles.srt" ]]; then
  echo "💬 Incrustation des sous-titres…"
  ffmpeg -y -loglevel error -i "$OUT_DIR/_merged.mp4" \
    -vf "subtitles=$OUT_DIR/subtitles.srt:force_style='Fontname=Arial Black,Fontsize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=120'" \
    -c:a copy "$FINAL"
else
  cp "$OUT_DIR/_merged.mp4" "$FINAL"
  echo "ℹ️  Pas de subtitles.srt — vidéo copiée telle quelle."
fi

rm -f "$OUT_DIR"/_n_*.mp4 "$OUT_DIR/_merged.mp4" "$CONCAT"

echo "✅ Vidéo finale : $FINAL"
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$FINAL" | awk '{printf "⏱  Durée : %.1fs\n", $1}'
