#!/usr/bin/env bash
# Assemble la vidéo UGC Bunua finale (9:16, ~20s) en concaténant UNIQUEMENT
# les 3 clips IA générés (pas de Ken Burns, pas de captures statiques).
#
# Entrées attendues :
#   - out/clips/hook.mp4         (avatar, ~5s, audio natif Kling)
#   - out/clips/transition.mp4   (transition parlante, ~10s, voix clonée)
#   - out/clips/cta.mp4          (avatar, ~5s, audio natif Kling)
#   - assets/subtitles.srt       (optionnel)
#
# Sortie : out/bunua_ugc_final.mp4
#
# Prérequis : ffmpeg (brew install ffmpeg)
set -euo pipefail

CLIPS_DIR="out/clips"
TMP_DIR="out/.tmp_assemble"
FINAL="out/bunua_ugc_final.mp4"

W=1080; H=1920; FPS=30

check() { [[ -f "$1" ]] || { echo "❌ Manque : $1"; exit 1; }; }

check "$CLIPS_DIR/hook.mp4"
check "$CLIPS_DIR/transition.mp4"
check "$CLIPS_DIR/cta.mp4"

mkdir -p "$TMP_DIR"

echo "🎬 Normalisation des 3 clips (${W}x${H}@${FPS}fps, audio 48k stéréo)…"

norm_clip() {
  local in=$1 out=$2
  ffmpeg -y -loglevel error -i "$in" \
    -vf "scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:black,fps=${FPS}" \
    -c:v libx264 -pix_fmt yuv420p -preset veryfast -crf 20 \
    -c:a aac -ar 48000 -ac 2 -b:a 192k \
    "$out"
}

norm_clip "$CLIPS_DIR/hook.mp4" "$TMP_DIR/n_hook.mp4"
norm_clip "$CLIPS_DIR/transition.mp4" "$TMP_DIR/n_transition.mp4"
norm_clip "$CLIPS_DIR/cta.mp4" "$TMP_DIR/n_cta.mp4"

# Concaténation.
CONCAT="$TMP_DIR/concat.txt"
{
  echo "file 'n_hook.mp4'"
  echo "file 'n_transition.mp4'"
  echo "file 'n_cta.mp4'"
} > "$CONCAT"

echo "🧩 Concaténation…"
ffmpeg -y -loglevel error -f concat -safe 0 -i "$CONCAT" -c copy "$TMP_DIR/merged.mp4"

# Sous-titres (optionnel).
if [[ -f "assets/subtitles.srt" ]]; then
  cp assets/subtitles.srt "$TMP_DIR/subtitles.srt"
  echo "💬 Incrustation des sous-titres…"
  ffmpeg -y -loglevel error -i "$TMP_DIR/merged.mp4" \
    -vf "subtitles=$TMP_DIR/subtitles.srt:force_style='Fontname=Arial Black,Fontsize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=120'" \
    -c:a copy "$FINAL"
else
  cp "$TMP_DIR/merged.mp4" "$FINAL"
  echo "ℹ️  Pas de assets/subtitles.srt — vidéo copiée telle quelle."
fi

rm -rf "$TMP_DIR"

echo "✅ Vidéo finale : $FINAL"
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$FINAL" | awk '{printf "⏱  Durée : %.1fs\n", $1}'
