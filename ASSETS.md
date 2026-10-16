# Assets

The code in this repository is covered by [LICENSE](LICENSE). This file covers everything that isn't code: where each asset came from, what you may do with it, and how to get the ones that aren't included.

## 1. Ours: included and open

Nothing yet. Any art, audio or demo loops Jonathan Mann makes for this project will be licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) and listed here. Credit "Jonathan Mann (Song A Day)".

## 2. Free third-party: included under their own licenses

Nothing included. The third-party code this project runs on, [drum2midi](https://github.com/miraer/drum2midi) (MIT) and [ADTOF-pytorch](https://github.com/xavriley/ADTOF-pytorch), is cloned by `tools/setup.sh` into the ignored `drum2midi/` folder.

## 3. Licensed (paid or restricted): not included

These are the test loops: 11 drum loops from 9 Splice packs. The Splice license lets you use the sounds in new music. It does not let you redistribute them as samples or loops, modified or not ([Splice Sounds licensing FAQ](https://intercom.help/splice-b7a2d5b83f2e/en/articles/8652642-splice-sounds-licensing-faq)). They stay in Jonathan's private copy. To test, put any drum loops of your own in `private-assets/loops/`.

Everything in `results/` is derived from these loops (stems, MIDI, renders and the report, which embeds the audio). It stays out of the repo too.

| Expected path | Pack | Where to get it | Terms |
| --- | --- | --- | --- |
| `private-assets/loops/SO_HU2_*` | Breaktapes Vol 2 with Sean Hutchinson (Splice Originals) | https://splice.com/sounds/packs/splice-originals/breaktapes-vol-2-with-sean-hutchinson | Splice license: use in music, no redistribution |
| `private-assets/loops/OLIVER_*` | Oliver: Power Tools Decades - 80's (Splice) | https://splice.com/sounds/packs/splice/oliver-power-tools-decades-80s | Splice license: use in music, no redistribution |
| `private-assets/loops/SC_MBB_*` | Inspired By Motown - Beats & Breaks (Sonic Collective) | https://splice.com/sounds/packs/sonic-collective/inspired-by-motown-beats-breaks | Splice license: use in music, no redistribution |
| `private-assets/loops/DD_NS_*` | Northern Soul (Drumdrops) | https://splice.com/sounds/packs/drumdrops/drumdrops-northern-soul | Splice license: use in music, no redistribution |
| `private-assets/loops/B&BB_*` | Backbeats, Breakbeats & Effects (Drumdrops) | https://splice.com/sounds/packs/drumdrops/back-and-breakbeats | Splice license: use in music, no redistribution |
| `private-assets/loops/TS_DARREN_KING_*` | Darren King: Iconic Signature (That Sound) | https://splice.com/sounds/packs/that-sound/darren-king-iconic-signature | Splice license: use in music, no redistribution |
| `private-assets/loops/TS_IR_*` | Indie Rocker (That Sound) | https://splice.com/sounds/packs/that-sound/indie-rocker | Splice license: use in music, no redistribution |
| `private-assets/loops/TS_WIP_*` | Wild Indie Pop (That Sound) | https://splice.com/sounds/packs/that-sound/wild-indie-pop | Splice license: use in music, no redistribution |
| `private-assets/loops/TS_AMD_*` | Americana Drums (That Sound) | https://splice.com/sounds/packs/that-sound/americana-drums | Splice license: use in music, no redistribution |

### Models: downloaded at setup or first run, never committed

| Model | Where it comes from | License |
| --- | --- | --- |
| ADTOF drum transcription weights | [ADTOF](https://github.com/MZehren/ADTOF), via ADTOF-pytorch | CC BY-NC-SA 4.0 (non-commercial) |
| MDX23C DrumSep separation weights | Released by jarredou and aufr33, downloaded by audio-separator | None stated |
| drum2midi velocity and pedal-hat models | Bundled with drum2midi, trained on the Groove MIDI Dataset | MIT |

None of these models can go into a released plugin. See "Model licenses" in the [README](README.md).

## 4. Not ours and not licensed: never in the repo

Nothing so far.

## Never commit

Ripped songs or videos, press, stock, or Getty photos, photos or likenesses of real people, other NFT collections' art, screenshots of commercial software, the source files of paid asset packs, voice models with noncommercial terms, and personal data.
