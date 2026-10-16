"""Turn a drum loop into General MIDI, using drum2midi for detection and our own rules for
the parts it gets wrong on loops.

    drum2midi/.venv/bin/python tools/expand.py loop.wav out_dir/ [--tempo 120]

Writes out_dir/ALL.mid, out_dir/stems/*.wav, out_dir/fixes.json and out_dir/log.txt.

What this changes on top of drum2midi:
  * Downbeat: ADTOF's peak picker pads its moving average and local-max windows with copies
    of the first frame, so a hit at 0 ms looks like no change and is dropped. We pad with
    silence instead. (Padding the audio itself shifts the model's recurrent state and
    changed what it heard elsewhere in the loop, so only the peak picker is touched.)
  * Open vs closed hats: drum2midi listens for ringing 80-250 ms after each hat, which at
    130 BPM eighths already contains the next hat. We stop listening before the next hat.
  * Velocity: taken from each hit's peak in its own stem relative to that drum's loudest
    hits, through the General MIDI curve (gain dB = 40*log10(vel/127)), so a hit 10 dB down
    lands near 71 instead of ~120. A kick or snare more than 30 dB under its drum's loudest
    hits is bleed, not a hit, and is dropped.
"""

import argparse
import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path

import librosa
import numpy as np
import pretty_midi
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
D2M = ROOT / "drum2midi"
sys.path.insert(0, str(D2M))
import drum2midi as d2m  # noqa: E402
from adtof_pytorch import post_processing as adtof_pp  # noqa: E402

SR = 44100
NOTE_LEN = 0.06
FALSE_HIT_DB = -30.0      # this far under the drum's loudest hits = bleed
FALSE_HIT_LANES = {"KICK", "SNARE"}  # the only stems clean enough to overrule the transcriber
OPEN_RATIO = 0.30         # tail/attack RMS above this (about -10.5 dB) = still ringing
LANE_STEM = {"KICK": "kick", "SNARE": "snare", "HATS": "hihat", "TOMS": "toms",
             "RIDE": "ride", "CRASH": "cymbals"}
LANE_OF = {35: "KICK", 36: "KICK", 37: "SNARE", 38: "SNARE", 39: "SNARE", 40: "SNARE",
           42: "HATS", 44: "HATS", 46: "HATS", 49: "CRASH", 52: "CRASH", 55: "CRASH",
           57: "CRASH", 51: "RIDE", 53: "RIDE", 59: "RIDE",
           41: "TOMS", 43: "TOMS", 45: "TOMS", 47: "TOMS", 48: "TOMS", 50: "TOMS"}


# --- downbeat fix: ADTOF's peak picker, with silence before the first frame ---------------

def _pad_silent_start(x, left, right):
    return np.concatenate([np.zeros(left, dtype=x.dtype), np.pad(x, (0, right), mode="edge")])


def _moving_average(self, x, win_left, win_right):
    if win_left <= 0 and win_right <= 0:
        return x
    kernel = np.ones(win_left + 1 + win_right, dtype=np.float32) / (win_left + 1 + win_right)
    padded = _pad_silent_start(x, win_left, win_right)
    return np.convolve(padded, kernel, mode="valid").astype(np.float32, copy=False)


def _local_maxima(self, x, w_left, w_right):
    if w_left <= 0 and w_right <= 0:
        return x
    padded = _pad_silent_start(x, w_left, w_right)
    return np.stack([padded[k:k + len(x)] for k in range(w_left + 1 + w_right)]).max(axis=0)


adtof_pp.NotePeakPickingProcessor._moving_average = _moving_average
adtof_pp.NotePeakPickingProcessor._local_maxima = _local_maxima


# --- measurements ----------------------------------------------------------------------

def mono(x):
    return x.mean(axis=1) if x.ndim > 1 else x


def peak_db(sig, t, pre=0.005, post=0.03):
    a, b = max(0, int((t - pre) * SR)), min(len(sig), int((t + post) * SR))
    return 20 * np.log10(np.abs(sig[a:b]).max() + 1e-9) if b > a else -180.0


def rms(sig, a, b):
    seg = sig[max(0, int(a * SR)):min(len(sig), int(b * SR))]
    return float(np.sqrt(np.mean(seg ** 2))) if seg.size else 0.0


def hat_is_open(stem, t, next_hat, loudest_attack):
    """drum2midi's test (tail RMS 80-250 ms vs attack 0-50 ms), but the tail stops 15 ms
    before the next hat, which would otherwise read as this one still ringing."""
    end = min(t + 0.25, next_hat - 0.015)
    start = min(t + 0.08, end - 0.03)
    if start < t + 0.04:
        return False      # next hat comes too soon to hear a ring; closed is the safe call
    attack = rms(stem, t, t + 0.05)
    tail = rms(stem, start, end)
    return tail > OPEN_RATIO * attack and tail > 0.15 * loudest_attack


def run_drum2midi(loop: Path, raw_mid: Path, stems_dir: Path, tempo, log: Path) -> int:
    """drum2midi's own CLI, in this process so the peak-picker fix above applies."""
    argv = ["drum2midi.py", str(loop), "-o", str(raw_mid), "--keep-stems", str(stems_dir),
            "--note-len", str(NOTE_LEN)]
    if tempo:
        argv += ["--tempo", str(tempo)]
    saved_argv, saved_cwd = sys.argv, os.getcwd()
    sys.argv = argv
    os.chdir(D2M)
    try:
        with open(log, "w") as f, contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            return d2m.main()
    finally:
        sys.argv = saved_argv
        os.chdir(saved_cwd)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("loop", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--tempo", type=float, default=None)
    args = ap.parse_args()
    loop = args.loop.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    duration = sf.info(str(loop)).duration

    with tempfile.TemporaryDirectory(prefix="expand_") as tmp:
        raw_mid = Path(tmp) / "raw.mid"
        if run_drum2midi(loop, raw_mid, out / "stems", args.tempo, out / "log.txt"):
            return 1
        raw = pretty_midi.PrettyMIDI(str(raw_mid))
    tempo = args.tempo or float(raw.get_tempo_changes()[1][0])
    events = sorted((n.start, n.pitch, n.velocity) for i in raw.instruments for n in i.notes)

    stems = {}
    for lane, name in LANE_STEM.items():
        f = out / "stems" / f"{name}.wav"
        if f.exists():
            stems[lane] = mono(sf.read(str(f))[0])
    mix = librosa.load(str(loop), sr=SR, mono=True)[0]
    mix_rms = rms(mix, 0, len(mix) / SR)

    # Hats: re-decide open (46) vs closed (42); pedal (44) stays as drum2midi called it.
    hats_before = {42: 0, 46: 0}
    hats_after = {42: 0, 46: 0}
    hat_stem = stems.get("HATS")
    if hat_stem is not None:
        hat_times = sorted(e[0] for e in events if e[1] in (42, 44, 46))
        loudest = max((rms(hat_stem, t, t + 0.05) for t in hat_times), default=0.0)
        fixed = []
        for t, p, v in events:
            if p in (42, 46):
                hats_before[p] += 1
                nxt = next((o for o in hat_times if o > t + 0.02), duration + 1.0)
                p = 46 if hat_is_open(hat_stem, t, nxt, loudest) else 42
                hats_after[p] += 1
            fixed.append((t, p, v))
        events = fixed

    # Velocity from loudness in the drum's own stem; the mix when the stem came out empty.
    by_lane = {}
    for i, (t, p, v) in enumerate(events):
        by_lane.setdefault(LANE_OF.get(p, "OTHER"), []).append(i)
    vel = {}
    drop = set()
    dropped = []
    source = {}
    for lane, idx in by_lane.items():
        stem = stems.get(lane)
        usable = (stem is not None and mix_rms > 0
                  and 20 * np.log10(rms(stem, 0, len(stem) / SR) / mix_rms + 1e-12) > -55)
        sig = stem if usable else mix
        source[lane] = "stem" if usable else "mix"
        levels = np.array([peak_db(sig, events[i][0]) for i in idx])
        ref = np.percentile(levels, 95) if len(levels) >= 8 else levels.max()
        for i, lv in zip(idx, levels):
            rel = min(0.0, lv - ref)
            if usable and lane in FALSE_HIT_LANES and rel < FALSE_HIT_DB:
                drop.add(i)
                dropped.append({"t": round(events[i][0], 3), "lane": lane,
                                "db_under": round(-rel, 1)})
                continue
            vel[i] = int(np.clip(round(127 * 10 ** (rel / 40)), 8, 127))

    final = [(t, p, vel.get(i, v)) for i, (t, p, v) in enumerate(events) if i not in drop]
    d2m.write_midi(final, out / "ALL.mid", tempo, NOTE_LEN, None, duration=duration)

    report = {
        "tempo": tempo,
        "first_hit_ms": round(final[0][0] * 1000, 1) if final else None,
        "hats_drum2midi": {"closed": hats_before[42], "open": hats_before[46]},
        "hats_now": {"closed": hats_after[42], "open": hats_after[46]},
        "dropped_as_bleed": dropped,
        "velocity_source": source,
    }
    (out / "fixes.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ("first_hit_ms", "hats_drum2midi", "hats_now")}
                     | {"dropped": len(dropped)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
