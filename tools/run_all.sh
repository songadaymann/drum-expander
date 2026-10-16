#!/usr/bin/env bash
# Convert every loop in $LOOPS_DIR (default private-assets/loops/) with tools/expand.py (drum2midi plus our fixes), split into one MIDI per drum, and render
# the MIDI back to audio for listening. Results land in results/<loop name>/.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
D2M="$ROOT/drum2midi"
PY="${PY:-$D2M/.venv/bin/python}"
LOOPS="${LOOPS_DIR:-$ROOT/private-assets/loops}"
OUT="$ROOT/results"
mkdir -p "$OUT"
echo "loop,tempo,seconds,status" > "$OUT/timings.csv"

for wav in "$LOOPS"/*.wav; do
    name="$(basename "$wav" .wav)"
    dir="$OUT/$name"
    mkdir -p "$dir"
    # Splice names carry the tempo, e.g. OLIVER_120_drum_loop -> 120. A plugin gets it from the host.
    tempo="$(echo "$name" | grep -oE '_[0-9]{2,3}_' | head -1 | tr -d _)"
    tempo_arg=()
    [ -n "$tempo" ] && tempo_arg=(--tempo "$tempo")

    echo "== $name (tempo ${tempo:-auto})"
    start=$(date +%s)
    if "$PY" "$ROOT/tools/expand.py" "$wav" "$dir" "${tempo_arg[@]}" > "$dir/fixes.txt" 2>&1; then
        status=ok
    else
        status=failed
    fi
    secs=$(( $(date +%s) - start ))
    echo "$name,${tempo:-},$secs,$status" >> "$OUT/timings.csv"
    echo "   $status in ${secs}s"
    [ "$status" = ok ] || continue

    "$PY" "$ROOT/tools/split_midi.py" "$dir/ALL.mid" "$dir/midi" > "$dir/counts.json"
    cp "$dir/ALL.mid" "$dir/midi/ALL.mid"
    (cd "$D2M" && "$PY" render_midi.py "$dir/ALL.mid" -o "$dir/render.wav") >> "$dir/log.txt" 2>&1
    (cd "$D2M" && "$PY" render_midi.py "$dir/ALL.mid" --against "$wav" -o "$dir/ab.wav") >> "$dir/log.txt" 2>&1
    cat "$dir/counts.json"
done
