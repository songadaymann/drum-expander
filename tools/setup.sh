#!/usr/bin/env bash
# Fetch drum2midi and the ADTOF port it uses, at the commits this repo was tested with, then
# build its Python environment. Everything lands in drum2midi/, which git ignores.
#
# Needs git, Python 3.12 (uv is used if present), ffmpeg, and fluidsynth for the report:
#   brew install ffmpeg fluid-synth
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
D2M="$ROOT/drum2midi"
DRUM2MIDI_COMMIT=ef2a36c062341ab0ea585874259ea396a94ae362
ADTOF_COMMIT=85c192e78f716ea0b111cc8a5ee4a8f6a3a4f8a9

if [ ! -f "$D2M/drum2midi.py" ]; then
    git clone https://github.com/miraer/drum2midi.git "$D2M"
    git -C "$D2M" checkout -q "$DRUM2MIDI_COMMIT"
fi
if [ ! -d "$D2M/ADTOF-pytorch" ]; then
    git clone https://github.com/xavriley/ADTOF-pytorch.git "$D2M/ADTOF-pytorch"
    git -C "$D2M/ADTOF-pytorch" checkout -q "$ADTOF_COMMIT"
fi

# The environment and model downloads come to about 3 GB; keep them out of Dropbox sync.
xattr -w com.dropbox.ignored 1 "$D2M" 2>/dev/null || true

cd "$D2M"
if [ ! -x .venv/bin/python ]; then
    if command -v uv >/dev/null; then uv venv --seed --python 3.12 .venv
    else python3.12 -m venv .venv; fi
fi
.venv/bin/python setup_env.py
# audio-separator imports audioread, which drum2midi's requirements leave out.
.venv/bin/python -m pip install audioread
