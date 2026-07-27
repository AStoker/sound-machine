# Dual CharliePlex matrix snap-in tray

`matrix-tray.stl` — a mount that holds **two butted Adafruit IS31FL3731 16×9
CharliePlex matrices *and* their two driver backpacks** as one solid unit, with
a **flat front face** (for mounting flush against cloth) and all retention on
the back. No screws, no heat-set inserts — it snaps together.

Generated with `manifold3d`; validated **watertight, 2-manifold, genus-288**
(the 288 light windows) — imports into OrcaSlicer with no repair.

Board geometry is from Adafruit's EAGLE files (LED matrix + STEMMA backpack), so
outlines, LED positions, and hole positions are exact, not estimated.

## How it holds together

Stack, front → back: `cloth │ front face │ matrices │ gap │ backpacks │`

- **Flat front:** 1.5 mm face (`FACE_T`) with one Ø2.0 light window per LED
  (288 total). The matrices sit right behind it, LEDs pointing into the windows.
  Kept thin on purpose — a deep face turns each window into a light pipe and
  kills off-axis visibility (Ø2.0 × 1.5 mm ≈ ±34° half-angle). Raise toward
  ~2 mm for more per-LED isolation / a stiffer face.
- **Matrices:** *located* (not retained) by **4 plain alignment posts** through
  each matrix's two diagonal Ø2.0 holes — the only holes that line up. The posts
  have a small chamfered lead-in tip and **no barb** (barbs are hard to print
  cleanly on FDM). The matrices are held forward by the clamped stack, not by
  the posts.
- **The gap** between matrix and backpack is set by *your own* inter-board
  header pins — the tray just spans it (parameter `STACK_GAP`).
- **Backpacks:** retained by **4 cantilever snap fingers** on the long walls.
  Each finger tip is a **triangular hook**: a shallow lead-in ramp the board
  rides over, then a 45° retaining facet that clicks behind the backpack's back
  face and pulls the whole stack forward against the front. 45° keeps the
  overhang FDM-printable; the angled facet gives more hold-down than a round bump.
- **Wires:** notches in both end walls, **18 mm wide to clear both STEMMA QT
  ports** on each backpack.

Everything is captured between the flat front and the rear snaps, so the stack
can't fall apart and the wires aren't stressed.

## Print & assemble

1. Import `matrix-tray.stl` into OrcaSlicer. Print **front-face-down** on the
   bed — gives the smoothest flat face against the cloth, and the posts/fingers
   print upward with no supports.
2. Push each **matrix** in from the back until its two holes snap onto the
   posts and it seats against the front face.
3. Push each **backpack** in until the snap fingers click behind it.

## ⚠️ Measure these before printing (top of `gen_tray.py`)

The design is exact for the boards, but three things depend on *your* build:

| Param | Default | What to check |
|---|---|---|
| `STACK_GAP` | 5.0 mm | **The important one.** Clear gap between matrix back and backpack front (your header-pin height). If this is wrong the snaps won't clamp. |
| `PCB_T` / `BP_T` | 1.6 mm | PCB thicknesses (calipers). |
| `LED_D` | 2.0 mm | Window Ø. Must clear the LED package so the matrix seats flat — measure an LED; enlarge if they don't nest into the tunnels. |

Also confirm: **two backpacks** (one per matrix)? And which wall the connectors
exit — I notched both ends; tell me if a side wall needs a slot instead.

Snap features can't be simulated for fit — **test-print one corner** (or the
whole thing) and tune if needed: `LIP_REACH` (how far the hook grabs),
`RAMP_RUN` (insertion ease), `FINGER_W`/`SLOT_W` (finger stiffness). The matrix
posts are `POST_D` (loosen if they bind in the Ø2.0 holes).

## Regenerating

```sh
python3 -m venv venv
venv/bin/pip install manifold3d trimesh matplotlib scipy
venv/bin/python gen_tray.py       # writes matrix-tray.stl (+ section preview)
```

All dimensions are parameters at the top of `gen_tray.py`.
