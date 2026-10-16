"""Build results/report.html: one card per loop with the original audio, the MIDI rendered
per drum (so each drum can be soloed against the original), and a lane view of every hit.

    drum2midi/.venv/bin/python tools/make_report.py

The page is a single file with the audio embedded, so it opens from disk with no server.
It contains the source loops, so keep it local; don't publish it.
"""

import base64
import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pretty_midi
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
LOOPS = Path(os.environ.get("LOOPS_DIR", ROOT / "private-assets" / "loops"))
SOUNDFONT = ROOT / "drum2midi" / "tools" / "MuseScore_General.sf3"
LANES = ["KICK", "SNARE", "HATS", "CRASH", "RIDE", "TOMS", "COWBELL"]
PACKS = {
    "SO_HU2": "Breaktapes Vol 2 (Sean Hutchinson)",
    "OLIVER": "Oliver Power Tools Decades: 80's",
    "SC_MBB": "Inspired By Motown: Beats & Breaks",
    "DD_NS": "Drumdrops Northern Soul",
    "B&BB": "Drumdrops Backbeats & Breakbeats",
    "TS_DARREN_KING": "Darren King Iconic Signature",
    "TS_IR": "Indie Rocker",
    "TS_WIP": "Wild Indie Pop",
    "TS_AMD": "Americana Drums",
}
# GM note -> (lane, short label shown on the hit)
NOTE_INFO = {
    35: ("KICK", ""), 36: ("KICK", ""),
    37: ("SNARE", "x"), 38: ("SNARE", ""), 39: ("SNARE", "clap"), 40: ("SNARE", ""),
    42: ("HATS", ""), 44: ("HATS", "ped"), 46: ("HATS", "open"),
    49: ("CRASH", ""), 52: ("CRASH", ""), 55: ("CRASH", ""), 57: ("CRASH", ""),
    51: ("RIDE", ""), 53: ("RIDE", "bell"), 59: ("RIDE", ""),
    41: ("TOMS", "lo"), 43: ("TOMS", "lo"), 45: ("TOMS", "mid"),
    47: ("TOMS", "mid"), 48: ("TOMS", "hi"), 50: ("TOMS", "hi"),
    56: ("COWBELL", ""),
}


def mp3_b64(wav: Path, bitrate: str, mono: bool) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "a.mp3"
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(wav)]
        if mono:
            cmd += ["-ac", "1"]
        cmd += ["-b:a", bitrate, str(out)]
        subprocess.run(cmd, check=True)
        return base64.b64encode(out.read_bytes()).decode()


def render_lane(midi: Path) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "lane.wav"
        subprocess.run(["fluidsynth", "-ni", "-g", "0.8", "-F", str(wav), "-r", "44100",
                        str(SOUNDFONT), str(midi)], check=True, capture_output=True)
        return mp3_b64(wav, "64k", mono=True)


def peaks(wav: Path, bins: int = 900) -> list:
    audio, _ = sf.read(str(wav), always_2d=True)
    mono = np.abs(audio).max(axis=1)
    edges = np.linspace(0, len(mono), bins + 1).astype(int)
    vals = [float(mono[a:b].max()) if b > a else 0.0 for a, b in zip(edges[:-1], edges[1:])]
    top = max(vals) or 1.0
    return [round(v / top, 3) for v in vals]


def pack_for(name: str) -> str:
    for prefix, pack in sorted(PACKS.items(), key=lambda kv: -len(kv[0])):
        if name.startswith(prefix):
            return pack
    return ""


def main() -> int:
    timings = {}
    with open(RESULTS / "timings.csv") as f:
        for row in csv.DictReader(f):
            timings[row["loop"]] = row

    loops = []
    for wav in sorted(LOOPS.glob("*.wav")):
        name = wav.stem
        d = RESULTS / name
        t = timings.get(name, {})
        entry = {"name": name, "pack": pack_for(name), "tempo": t.get("tempo") or None,
                 "seconds": int(t["seconds"]) if t.get("seconds") else None,
                 "status": t.get("status", "missing")}
        print(f"{name}: {entry['status']}", file=sys.stderr)
        if entry["status"] != "ok":
            loops.append(entry)
            continue

        info = sf.info(str(wav))
        entry["duration"] = info.duration
        entry["peaks"] = peaks(wav)
        entry["original"] = mp3_b64(wav, "96k", mono=False)

        pm = pretty_midi.PrettyMIDI(str(d / "ALL.mid"))
        hits = []
        for inst in pm.instruments:
            for n in inst.notes:
                lane, label = NOTE_INFO.get(n.pitch, (None, str(n.pitch)))
                hits.append({"t": round(n.start, 4), "lane": lane or "OTHER",
                             "label": label, "vel": n.velocity, "pitch": n.pitch})
        hits.sort(key=lambda h: h["t"])
        entry["hits"] = hits
        entry["counts"] = json.loads((d / "counts.json").read_text())
        if (d / "fixes.json").exists():
            entry["fixes"] = json.loads((d / "fixes.json").read_text())
        entry["lanes"] = {lane: render_lane(d / "midi" / f"{lane}.mid")
                          for lane in LANES if (d / "midi" / f"{lane}.mid").exists()}
        loops.append(entry)

    template = (Path(__file__).parent / "report_template.html").read_text()
    html = template.replace("/*__DATA__*/null", json.dumps(loops))
    out = RESULTS / "report.html"
    out.write_text(html)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
