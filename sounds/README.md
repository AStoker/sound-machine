# The flashed audio

Every sound in this folder is an **ambience**: something that runs until the
machine is told to stop, not a clip that ends. `components/ambience_player` decodes
these files straight into a mixer source and rewinds at end-of-file, so a loop
costs a read pointer going back to zero.

That decode path has **no resampler in it**, which is what makes the loop free
and also why the format below is a hard requirement rather than a preference.

- **Firmware side:** `packages/hw/audio_chain.yaml` declares the files;
  `packages/behavior/sound.yaml` offers them in the Sound select.
- **Why it is not a `media_player`:** `components/ambience_player/ambience_player.h`,
  and `FUTURE-DEVELOPMENT.md` T3–T5.
- **The URLs** these are fetched from at build time are in
  `packages/settings.yaml` §11 — the file is downloaded, not read from this
  folder, when the config is pulled onto Home Assistant as a remote package.

## The format

A file that does not match is refused at its first frame and logged. That is
deliberate: the alternative is what a mismatch used to do, which was play at the
wrong speed and the wrong pitch for a whole pass before anyone noticed.

| Requirement | Why |
| --- | --- |
| **MP3** | The only decoder linked in. Not WAV, not FLAC, not Opus. |
| **Mono** | The mixer source is one channel. Stereo is refused, and on a dual-mono file it was only ever doubling the size for nothing. |
| **48 000 Hz** | The mixer's rate. 44.1 kHz is refused. |
| **Xing/Info header** | Keep the VBR header ffmpeg writes by default. `ambience_player` reads its delay/padding fields to trim the codec's priming samples, and that is what makes the wrap sample-exact. Without it every loop grows ~25 ms of silence. |
| **Peak ≤ −2.4 dBFS** | Headroom for the mixer to add a TTS reply on top without clipping. Watch this across a **resample** especially: 44.1 → 48 kHz turns intersample peaks into real ones, which is how La La spent a while clipping 1064 samples at +1.65 dBFS. |
| **Level within a few dB of the others** | So swapping sounds does not need the volume knob touched. The ambiences sit at roughly −17 to −18 dBFS RMS today. |

The recipe, for a file that is **already a good loop**:

```sh
ffmpeg -i in.mp3 -ac 1 -ar 48000 -af "volume=-XdB" -b:a 128k out.mp3
```

Check the decoded peak before trusting `-X`. If the file is *not* a good loop —
if it opens or closes with a fade — see Crickets below.

## How big can a file be?

Flashed audio is compiled **into the app image**, so it competes with the
firmware for one app partition: `0x3C0000` = 3.75 MB, of which the firmware
itself is ~2.4 MB. Both files below plus everything else currently leaves
~780 KB free. `esphome compile` prints the real number ("Smallest app partition
is … N bytes free") — check it after adding one.

## The files

### La La — 48 s, mono 48 kHz 128 kbps (~770 KB)

A composed piece rather than a true ambience: it opens from silence and closes on
a deliberate ~1 s fade, so its loop point is a fade-out into a fade-in rather
than a seam. **That is the music, and it is left alone** — crossfading it would
overlap two different bars (measured 7.1 onsets/second; this is plucked guitar,
not a pad).

It was 44.1 kHz dual-mono, which cost double the bytes for an identical second
channel (L/R correlation 1.0000) and clipped 1064 samples at +1.65 dBFS once
resampled to 48 kHz. Now mono at the same bitrate — so roughly twice the bits per
channel for the same size — and attenuated 4.25 dB to peak −3.06 dBFS.

### Crickets — 59 s, mono 48 kHz 96 kbps (~710 KB)

**This file is a crossfade loop, and that is not recoverable by re-encoding.**

The source recording opened with a 65 ms fade-in and closed with an 85 ms
fade-out, and those two fades met at the loop point — a ~150 ms hole in the
ambience once a minute, which is the loudest thing a sound meant to be
unnoticeable can do. Its last 2 s are now equal-power crossfaded under its first
2 s (sin/cos, which holds RMS flat for uncorrelated noise where a linear fade
would dip 3 dB). That fills the hole and blends out the ~2 dB low-frequency step
that was also across the seam; measured, the wrap is now a shallower dip than an
ordinary moment in the recording. The 2 s that used to be the fades are gone —
hence 59 s, not 61 s.

It is +13 dB from source, which puts it within a few dB of the noise generator at
the same volume setting, while keeping peaks 2.4 dB below full scale.

> **Do not rebuild it by re-encoding an earlier `Crickets.mp3`, and do not trim
> it** — both silently restore the hole. Rebuild it with
> `./scripts/make-crickets-loop.py`, which goes back to
> `sounds/originals/Crickets-original.wav` and owns the whole chain: crossfade,
> then downmix, resample, +13 dB, encode, in that order. `--verify` reports the
> loop point without writing anything.

## Adding one

1. Put the encoded file here and commit it.
2. Add a `*_source` substitution in `packages/settings.yaml` §11, defaulting to
   its raw GitHub URL (a local `file:` path would not resolve on Home Assistant).
3. Add an `audio_file:` entry and a `name:`/`file:` pair under `ambience_player:` in
   `packages/hw/audio_chain.yaml`.
4. Add that **same name** as an option in the Sound select in
   `packages/behavior/sound.yaml`.

There is no new api verb: `ambience_play` takes the name.
