#!/usr/bin/env bash
# Final pass: adds temporal film grain (luma only) to the Remotion render and
# muxes the master mix straight from the WAV (avoids a second lossy encode).
# Usage: scripts/finish.sh out/MH370_raw.mp4 out/MH370_final.mp4
set -euo pipefail
ffmpeg -y -loglevel error -i "$1" -i public/audio/mix.wav \
  -map 0:v:0 -map 1:a:0 \
  -vf "noise=c0s=9:c0f=t+u" \
  -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -profile:v high -r 30 -movflags +faststart \
  -c:a aac -b:a 256k -ar 48000 -shortest \
  "$2"
