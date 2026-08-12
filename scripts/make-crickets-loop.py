#!/usr/bin/env python3
"""Rebuild sounds/Crickets.mp3 as a seamless loop from sounds/Crickets-original.wav.

WHY THIS EXISTS

InspectorJ's source recording opens with a ~65 ms fade-in and closes with a
~85 ms fade-out. That is correct for a clip played once and wrong for a bed
played on `repeat_one`: the two fades meet at the loop point and put a ~150 ms
hole in the sound once a minute. On a machine whose whole job is to be
unnoticeable, that hole is the most noticeable thing it does.

Trimming the fades off would leave a step discontinuity instead. The fix is a
crossfade loop: the tail is folded back under the head, so the file's last
sample is followed by material that genuinely preceded its first.

    for i <  L:   y[i] = x[i]*sin(t) + x[M+i]*cos(t),  t = (pi/2)(i+.5)/L
    for i >= L:   y[i] = x[i]

sin/cos rather than a linear fade because the two sides are uncorrelated noise:
equal-*power* holds RMS flat, where equal-gain would dip 3 dB in the middle.
The construction also disposes of both fades for free - the head fade sits
under w_in ~ 0 and the tail fade under w_out ~ 0, so each is attenuated by
25 dB or more exactly where it would have been audible.

M is picked so that M % 1152 == 576 (1152 = MPEG1 Layer III samples per frame),
which keeps the encoder's trailing padding small. It is not load-bearing:
micro_mp3 on the device reads the Xing/Info header's delay/padding fields and
trims the codec's priming samples itself. Keeping that header IS load-bearing -
without it the seam grows ~25 ms of decoder warm-up silence.

USAGE
    ./scripts/make-crickets-loop.py            # rebuild sounds/Crickets.mp3
    ./scripts/make-crickets-loop.py --verify   # analyse only, write nothing

Needs ffmpeg on PATH and numpy. The encode chain (mono downmix, 48 kHz,
+13 dB, 96 kbps CBR) reproduces how the flashed file was originally made; see
packages/settings.yaml section 11 for why each of those numbers is what it is.
"""

import argparse
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

SR = 48_000
FRAME = 1152          # MPEG1 Layer III samples per frame
ENC_DELAY = 576       # encoder delay the Xing/Info header will report
CROSSFADE_S = 2.0     # long enough to blend the ~2 dB LF level difference
GAIN_DB = 13.0        # matches the level the rest of the config is tuned against
BITRATE = "96k"

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "sounds" / "Crickets-original.wav"
TARGET = ROOT / "sounds" / "Crickets.mp3"


def decode_mono_48k(path: Path) -> np.ndarray:
    """ffmpeg's own downmix and resampler, so the result matches the chain that
    produced the file this replaces."""
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "mono.wav"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(path),
             "-ac", "1", "-ar", str(SR), "-c:a", "pcm_f32le", str(wav)],
            check=True,
        )
        return read_wav_f32(wav)


def read_wav_f32(path: Path) -> np.ndarray:
    data = path.read_bytes()
    pos, pcm = 12, None
    while pos < len(data):
        cid = data[pos:pos + 4]
        size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        if cid == b"data":
            pcm = data[pos + 8:pos + 8 + size]
        pos += 8 + size + (size & 1)
    if pcm is None:
        raise ValueError(f"no data chunk in {path}")
    return np.frombuffer(pcm, dtype="<f4").astype(np.float64)


def write_wav_f32(path: Path, x: np.ndarray) -> None:
    body = x.astype("<f4").tobytes()
    header = (b"RIFF" + struct.pack("<I", 36 + len(body)) + b"WAVEfmt " +
              struct.pack("<IHHIIHH", 16, 3, 1, SR, SR * 4, 4, 32) +
              b"data" + struct.pack("<I", len(body)))
    path.write_bytes(header + body)


def crossfade_loop(x: np.ndarray, crossfade_s: float) -> tuple[np.ndarray, int]:
    length = int(crossfade_s * SR)
    m = len(x) - length
    m -= (m - ENC_DELAY) % FRAME          # m % FRAME == ENC_DELAY
    if m + length > len(x):
        raise ValueError("source too short for this crossfade")
    t = (np.pi / 2) * (np.arange(length) + 0.5) / length
    y = x[:m].copy()
    y[:length] = x[:length] * np.sin(t) + x[m:m + length] * np.cos(t)
    return y, length


def envelope_db(y: np.ndarray, window_s: float = 0.005) -> tuple[np.ndarray, float]:
    w = int(window_s * SR)
    n = len(y) // w
    env = np.sqrt((y[:n * w].reshape(n, w) ** 2).mean(1))
    return env, float(np.median(env))


def report_seam(y: np.ndarray, label: str) -> None:
    """Judge the loop point against the file's own natural variation. An
    absolute threshold would be meaningless here - crickets are peaky, so plenty
    of ordinary 5 ms windows sit several dB below the median."""
    env, med = envelope_db(y)
    p2, p98 = np.percentile(env, [2, 98])
    k = 30                                     # +/- 150 ms around the wrap
    near = 20 * np.log10(np.concatenate([env[-k:], env[:k]]) / med)
    print(f"\n[{label}]  {len(y)} samples ({len(y) / SR:.3f} s)")
    print(f"  worst 5 ms window within 150 ms of the loop point : {near.min():+.1f} dB")
    print(f"  the file's own 2nd / 98th percentile window       : "
          f"{20 * np.log10(p2 / med):+.1f} / {20 * np.log10(p98 / med):+.1f} dB")
    verdict = "inside normal variation" if near.min() >= 20 * np.log10(p2 / med) - 0.5 \
        else "AUDIBLE DIP"
    print(f"  -> {verdict}")
    print(f"  RMS {20 * np.log10(np.sqrt((y ** 2).mean())):+.2f} dBFS   "
          f"peak {20 * np.log10(np.abs(y).max()):+.2f} dBFS")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true",
                    help="analyse and report, but do not write the mp3")
    ap.add_argument("--crossfade", type=float, default=CROSSFADE_S,
                    help=f"crossfade length in seconds (default {CROSSFADE_S})")
    args = ap.parse_args()

    if not SOURCE.exists():
        print(f"error: {SOURCE} not found", file=sys.stderr)
        return 1

    x = decode_mono_48k(SOURCE)
    print(f"source : {SOURCE.name}, {len(x)} samples ({len(x) / SR:.3f} s) at 48 kHz mono")
    report_seam(x, "SOURCE, butt-spliced (what repeat_one does today)")

    y, length = crossfade_loop(x, args.crossfade)
    print(f"\ncrossfade {args.crossfade:g} s -> loop of {len(y)} samples "
          f"({len(y) / SR:.3f} s), {len(y) % FRAME=}")
    report_seam(y, f"CROSSFADE LOOP, {args.crossfade:g} s")

    y = y * (10 ** (GAIN_DB / 20))
    peak_db = 20 * np.log10(np.abs(y).max())
    print(f"\nafter {GAIN_DB:+g} dB: peak {peak_db:+.2f} dBFS", end="")
    if peak_db > -2.0:
        print("  <-- WARNING: eats the headroom the mixer and TTS reply need")
    else:
        print("  (headroom for the mixer and a TTS reply preserved)")

    if args.verify:
        print("\n--verify: nothing written")
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "loop.wav"
        write_wav_f32(wav, y)
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav),
             "-c:a", "libmp3lame", "-b:a", BITRATE, "-ac", "1", "-ar", str(SR),
             "-metadata", "title=25.7.16", "-metadata", "artist=InspectorJ",
             "-metadata", "comment=seamless crossfade loop - see scripts/make-crickets-loop.py",
             "-id3v2_version", "3", "-write_xing", "1", str(TARGET)],
            check=True,
        )
    print(f"\nwrote {TARGET.relative_to(ROOT)} ({TARGET.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
