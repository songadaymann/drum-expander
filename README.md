# drum-expander

Drop in a drum loop and get MIDI back: one track each for kick, snare, hats, crash, ride and toms, with velocities that follow how hard each hit was played. Right now it's a command-line prototype built on [drum2midi](https://github.com/miraer/drum2midi). The goal is a plugin that works in any DAW: drag a loop in, drag six MIDI tracks out.

**Live:** nothing hosted yet. This is a local prototype.

## Run it locally

macOS or Linux, with Python 3.12 ([uv](https://github.com/astral-sh/uv) recommended), git, ffmpeg and FluidSynth.

```bash
brew install ffmpeg fluid-synth
./tools/setup.sh
```

Setup clones drum2midi into `drum2midi/` (git ignores it) and builds its Python environment. The first conversion also downloads the drum separation model, about 400 MB.

One loop:

```bash
drum2midi/.venv/bin/python tools/expand.py my_loop.wav out/my_loop --tempo 120
drum2midi/.venv/bin/python tools/split_midi.py out/my_loop/ALL.mid out/my_loop/midi
```

That writes `ALL.mid` (General MIDI drums), `midi/KICK.mid`, `SNARE.mid`, `HATS.mid`, `CRASH.mid`, `RIDE.mid` and `TOMS.mid`, the separated audio stems, and `fixes.json`.

A folder of loops, plus a listening report:

```bash
mkdir -p private-assets/loops          # put .wav loops here
./tools/run_all.sh                     # a tempo in the file name, like _120_, is used
drum2midi/.venv/bin/python tools/make_report.py   # writes results/report.html
```

The report lets you play each loop with any combination of its MIDI drums on top, so you can check one drum at a time. It embeds the source audio, so keep it local.

## How it works

1. **drum2midi** finds each hit with [ADTOF](https://github.com/MZehren/ADTOF) and splits the kit into stems with the MDX23C DrumSep model.
2. **`tools/expand.py`** fixes three things that go wrong on loops:
   - **The first beat.** ADTOF's peak picker compared the first frame with copies of itself, so a hit at 0 ms never registered. We treat the time before the loop as silence. Padding the audio instead changed what the model heard elsewhere in the loop.
   - **Open vs closed hats.** drum2midi called a hat open if it was still ringing 80–250 ms later. At 120–130 BPM the next hat lands inside that window. We stop listening just before the next hat.
   - **Velocity.** Each hit's velocity comes from its peak in its own stem, relative to that drum's loudest hits, through the General MIDI curve (gain in dB = 40·log10(velocity/127)). A kick or snare more than 30 dB under its drum's loudest hits is treated as bleed and dropped.
   - **Cowbell.** Neither model has a cowbell class, so the separator leaves it out of every stem and the transcriber calls some of its hits toms. We look in what's left after subtracting all six stems from the mix for repeating hits with one clear pitch (400–1500 Hz) and no low end. We write them as cowbell (GM note 56) and drop the toms that were really the bell.
3. **`tools/split_midi.py`** writes one MIDI file per drum, plus `COWBELL.mid` when there is one.

Claps are still filed as snare. When a clap is layered on the snare, nothing in the attack separates the two: acoustic snares are just as spiky. A general sound-event model (PANNs, trained on AudioSet) didn't pick up claps or cowbell inside a loop either.

## Model licenses: read before reusing

The code in this repo is MIT. drum2midi's code is MIT too, but the trained models it downloads are not open:

- ADTOF weights: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/), non-commercial.
- MDX23C DrumSep weights: no license stated.

That's fine for trying this out. Those models can't ship in an open or commercial plugin. The plan is to train our own on [E-GMD](https://magenta.tensorflow.org/datasets/e-gmd) and [StemGMD](https://zenodo.org/records/7860223), both CC BY 4.0. That would also make conversion fast enough for a plugin; today it takes 12–20 seconds per loop.

## Roadmap

- A plugin (VST3/AU) that takes a dropped file or captures the loop as the DAW plays, and gives you one drag handle per drum.
- Our own small transcription model, trained only on openly licensed data. It would cover claps, tambourine, shaker and other percussion as well as the kit, trained on synthetic loops where those parts are layered on purpose.

## License

Code: [MIT](LICENSE). Samples and models: see [ASSETS.md](ASSETS.md).

Made by [Jonathan Mann](https://jonathanmann.net) (Song A Day).
