#!/usr/bin/env python3
"""EXPORT CHECK -- does the STL on disk match the model that was validated?

>>> A GENERATOR CAN PASS EVERY CHECK AND SHIP A STALE FILE. gen_front_plate.py
>>> kept its own `base` pointing at the script directory. When solids moved into
>>> models/, every other generator followed and that one did not -- so it went on
>>> writing 3d-print/front-module.stl while models/front-module.stl sat there
>>> THREE HOURS OLD. The run said "wrote 19046 triangles"; the file everyone else
>>> was reading had 19032 and a volume 0.6 cm^3 out. Every check passed. The
>>> validation was of a solid in memory that never reached the disk.
>>>
>>> So: re-run each generator, then read back what it actually wrote and compare
>>> it against the model. This is the last link in the chain and it was the one
>>> nobody was watching.

    python3 verify_exports.py      # ends in ALL EXPORTS MATCH, or a problem count
"""
import os
import pathlib
import struct
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
MODELS = HERE / "models"

GENERATORS = {
    "gen_front_plate.py":  "front-module.stl",
    "gen_led_carrier.py":  "led-carrier.stl",
    "gen_dome.py":         "dome.stl",
    "gen_bottom_plate.py": "bottom-plate.stl",
    "gen_knob.py":         "knob.stl",
    "gen_tray.py":         "matrix-tray.stl",
}

problems = []


def stl_faces(path):
    d = path.read_bytes()
    n = struct.unpack("<I", d[80:84])[0]
    return n, (len(d) - 84) // 50


print(f"{'generator':22s} {'reported':>9s} {'in models/':>11s}")
for gen, stl in GENERATORS.items():
    out = subprocess.run([sys.executable, str(HERE / gen)], cwd=HERE,
                         capture_output=True, text=True)
    said = None
    for line in out.stdout.split("\n"):
        if "triangles" in line:
            for tok in line.split():
                if tok.isdigit():
                    said = int(tok)
                    break
        if said:
            break
    path = MODELS / stl
    if not path.exists():
        problems.append(f"{gen}: {stl} is not in models/ at all")
        print(f"{gen:22s} {str(said):>9s} {'MISSING':>11s}")
        continue
    hdr, bysize = stl_faces(path)
    print(f"{gen:22s} {str(said):>9s} {hdr:>11d}")
    if hdr != bysize:
        problems.append(f"{gen}: {stl} header says {hdr} faces, file holds {bysize}")
    if said is not None and said != hdr:
        problems.append(f"{gen}: reported {said} triangles but models/{stl} "
                        f"holds {hdr} -- it is writing somewhere else")

# nothing should be exporting solids outside models/
for stray in HERE.glob("*.stl"):
    problems.append(f"stray solid outside models/: {stray.name} "
                    f"(a generator is writing to the wrong directory)")

print("")
if problems:
    for p in problems:
        print(f"  FAIL  {p}")
    print(f"\n*** {len(problems)} PROBLEM(S) ***")
    sys.exit(1)
print("ALL EXPORTS MATCH")
