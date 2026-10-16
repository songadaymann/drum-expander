"""Split a General MIDI drum file into one .mid per drum: KICK, SNARE, HATS, CRASH, RIDE, TOMS.

    python split_midi.py combined.mid out_dir/

Each output keeps the source's tempo, resolution and timing; only notes for other drums
are dropped. Prints a JSON summary of hit counts per drum.
"""

import json
import sys
from pathlib import Path

import mido

GROUPS = {
    "KICK": {35, 36},
    "SNARE": {37, 38, 39, 40},  # side stick, snare, clap, electric snare
    "HATS": {42, 44, 46},
    "CRASH": {49, 52, 55, 57},
    "RIDE": {51, 53, 59},
    "TOMS": {41, 43, 45, 47, 48, 50},
}


def keep_only(src: mido.MidiFile, notes: set) -> mido.MidiFile:
    out = mido.MidiFile(type=src.type, ticks_per_beat=src.ticks_per_beat)
    for track in src.tracks:
        new = mido.MidiTrack()
        carry = 0  # delta time of dropped messages moves onto the next kept one
        for msg in track:
            if msg.type in ("note_on", "note_off") and msg.note not in notes:
                carry += msg.time
                continue
            new.append(msg.copy(time=msg.time + carry))
            carry = 0
        out.tracks.append(new)
    return out


def main() -> int:
    src_path, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    src = mido.MidiFile(src_path)

    counts = {}
    for name, notes in GROUPS.items():
        hits = sum(1 for t in src.tracks for m in t
                   if m.type == "note_on" and m.velocity > 0 and m.note in notes)
        counts[name] = hits
        if hits:
            keep_only(src, notes).save(out_dir / f"{name}.mid")

    known = set().union(*GROUPS.values())
    counts["other"] = sum(1 for t in src.tracks for m in t
                          if m.type == "note_on" and m.velocity > 0 and m.note not in known)
    print(json.dumps(counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
