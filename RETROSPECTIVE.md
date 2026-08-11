# RETROSPECTIVE — building v1

**Prototype 1 is built.** Designed, printed, wired, assembled, in service on the
bedside table. This document is what building it taught, distilled from the
session journals and design notes that were kept during development.

It is **history, not current state.** For what the machine is, read
[`HARDWARE.md`](HARDWARE.md); for how the firmware is arranged,
[`CLAUDE.md`](CLAUDE.md); for what is still to do,
[`FUTURE-DEVELOPMENT.md`](FUTURE-DEVELOPMENT.md).

> The full session-by-session build journal (~1400 lines) and the superseded
> pre-print checklists are **not** on `main`. They live on the **v1 release
> branch**, which is the point of that branch — the raw material is preserved in
> git, and `main` carries only the conclusions.

---

# 1. The one lesson

Almost every bug recorded during the enclosure build was **a check that passed
for the wrong reason.** Not a missing check — a passing one. The geometry was
covered by hundreds of assertions and the parts were still wrong, because *an
assertion written around the answer you expect will confirm that answer
regardless of what the part does.*

The failure modes below all instance it. They are worth reading as a list because
they recur, and because almost none of them are specific to CAD.

### The check measured a quantity that could not fail

`chk("ToF hole pitch fits its own board", TOF_PCB_D - TOF_HOLE_P)` — with a corner
inset, that comparison is *arithmetically incapable* of going negative. Same
shape: `(MTX_INSET - MTX_GUTTER_D) - MTX_FACADE_MIN` reported `ok 0.00` from the
moment `MTX_INSET` was defined as the sum of those two terms. It was subtracting a
number from itself.

> **Tell:** a check reporting exactly `0.00`, or the same round margin, every run.
> Derive a value and then assert on it and you have written a tautology.
>
> **Fix:** assert against the *built artifact*, not the formula. Walk the solid
> and find where material actually stops.

### The check measured the right thing on the wrong axis

Every clearance table worked **in plan** (x against y), because that is where
crowding usually is. This is a shallow box with parts hung off both faces —
speakers off the front, battery off the back. They overlapped in x *and* in y;
**depth was the only thing keeping them apart, and nothing looked at depth.** The
model claimed 11.5 mm of clear air while the speakers were 3 mm inside the
battery. Found by hand, on the bench, by fitting it.

Same class: the crescent solver measured horizontally (chord) and vertically
(apex) on an **ellipse**, where the binding case is diagonal — so a pixel 0.58 mm
outside the diffuser read as clear on every check.

### The tolerance absorbed the defect

`check_assembly` reported 27.2 mm³ of dome-inside-plate and **passed**, because the
threshold was `overlap < 50.0 mm³`. That tolerance existed for a real reason: two
touching parts produce many zero-volume coplanar fragments, and a raw "any
intersection" test screams on every run.

> **Narrower than "tolerances are bad":** a tolerance sized to absorb one
> phenomenon will absorb anything else the same size. Apply it to a quantity only
> that phenomenon can produce. Contact is flat — many pieces, none with volume. A
> collision is one lump *with* volume. Judge the largest piece.

### The check read the wrong variable, or the wrong frame

A gutter probe read `body` instead of `part_body`. Those differ by the STL export
shift `(-3.6, -4.0)`, so it measured sideways into solid lip and cheerfully
reported full clearance — while a probe three lines above, using the right one,
said the gutter was open. **Two measurements of the same point disagreeing is the
only reason it was noticed.**

### A default masqueraded as a measurement

`check_stability.py` reported a scary 85 gf to lift the front feet by pressing
"the front-panel button at z = 100". There is no front-panel button. The height
came from `getattr(g, "SW_Y", 100.0)` firing its fallback silently, because the
real constant is `SW_WALL_Y`. The script had invented its own load case.

> `getattr(obj, name, default)` on a constant you believe exists is a silent
> rename detector that never fires.

### The check was never running at all

The dome's entire mesh validation — watertightness, connected-body count, board
envelopes — sat inside `except ImportError: say("validate skipped: no trimesh")`
wrapped around ~180 lines. trimesh was installed and fine. **scipy** was missing,
which `trimesh.split()` needs. Every run printed "no trimesh" and skipped
everything; removing the blanket handler immediately surfaced a *second* missing
dependency, rtree.

> **A blanket `except ImportError` around a large block does not just report the
> wrong cause — it silently skips work nobody chose to skip.** A missing
> dependency is a failure, not a shrug.

### The check validated something that never reached disk

`gen_front_plate.py` kept its own `base` pointing at the script directory. When
solids moved to `models/`, every other generator followed and that one did not. It
wrote `front-module.stl` beside the code while `models/front-module.stl` sat three
hours stale. **Every check passed the whole time** — all validating a solid in
memory that was never the file anyone would print. `verify_exports.py` exists
because of this: it re-runs each generator, reads back what was written, compares.

> Checks existed for geometry, for prose, and for drawings. The last link — model
> to file — was the one nobody watched, and the only one where being wrong means
> printing the wrong part.

### The check encoded a decision that later turned out wrong

An assertion demanded "exactly 2 separate tabs per side wall". Printed rear-wall
down, two separate shelves leave an unsupportable island between them; one
continuous rail is strictly better and needs no support at all. The check had to
be rewritten to assert the opposite.

> A check is not automatically right because it is automated. It is an opinion
> with a test attached.

---

# 2. Lessons that outlived the part

**Interference lives in the gap between parts.** The dome checked its own
features. The front module checked its own. Nothing put two parts in the same
space, so a mirrored bottom plate went unnoticed for weeks and the front module
reached 19 mm into the dome's interior unchallenged.

**Comparing coordinates from two frames is not a comparison — and take the
determinant.** The bottom plate was a mirror image, defended twice with a table of
"evidence" showing matching coordinates. The table read 45.0 from one part and
45.0 from the other without noticing **one was a depth and the other a height**.
The implied mapping `(x,y,z) → (x,z,y)` has determinant −1: a reflection, not
something you can do to a printed part. An axis swap looks exactly like a rotation
until you take the determinant.

**A negative result carries no expiry date.** "No viable position on the rear
wall" was believed for weeks. The search had run against the *old* vent stacks and
the *old* amp depth and was never re-run after either moved. Re-run, it found
67,151 positions. Nothing about a cached negative announces that its inputs moved.

**Stop checking one pair at a time.** Three separate bugs on the bottom plate had
the identical shape: A was checked against B and C, and nobody compared it to D.
The plate now enumerates every feature with a footprint — 22 features, 165 pairs —
so a new feature is checked against everything else for free. (It also has to know
about z: a planar check on a part with features on both faces reports collisions
that do not exist, and **a check that cries wolf is worse than no check, because
you start ignoring it.**)

**Look for the vendor's board file before reaching for the calipers.** Three times
a published number beat a measured or inferred one. The encoder, ToF and BH1750
each carried an invented *two*-hole pitch marked `(?) MEASURE`; all three have
**four** holes and all three vendors publish the Eagle file saying so. Fixing it
exposed two collisions the old model could not see — bosses 0.59 mm apart, and a
10.7° tilt on the ToF.

**The bosses are the binding constraint, not the board.** 0.59 mm between two Ø6
posts is not an intersection, so the "bosses do not intersect" check passed it —
and 0.59 mm of filament between two posts prints as one blob.

**Prose has no checks.** Every rework left documents describing a machine that no
longer existed; the 258-wide split enclosure was still documented as current three
revisions after it stopped being built. `3d-print/check_docs.py` exists for this
and is still live — it allows history explicitly, so a stale-value rule only fires
outside a line that marks itself historical ("used to", "no longer", …). Keep
using those markers.

**Measure the thing that has to fit, not the thing you are thinking about.** Every
early crescent layout measured the **LED body**. What has to fit the cavity is the
**ribbon** — a cut segment of n pixels is `n × pitch`, not `(n−1) ×`, because the
cut lines sit half a pitch outboard of the end LEDs. That cost three pixels
(48 → 45) until the rows were allowed to butt at 10.4 mm pitch, which recovered
them without the 6 mm of extra height raising `CROWN_K` would have cost.

**An argument for skipping something is only as good as the case it was made
about.** The note arguing the crown flat was unnecessary had measured the
**encoder** — centred on the apex, flat either way. The ToF is off the apex and
without the flat would have tilted 10.7°, aiming half its FoV cone into the side
of its own pinhole.

---

# 3. Physical facts worth not rediscovering

- **A snap-fit's free length is squared.** Peak strain is `1.5·t·y/L²`. The matrix
  clip was 2.2 thick, had to move 1.2, and was rooted 2.2 mm below its hook:
  **82 % strain against ~2 % for PLA.** It would have shattered, not flexed — and
  every check in that file was about *clearance*, which a clip that cannot bend
  passes perfectly. Rerooted to grip the whole stack: 9.3 mm beam, 1.39 %.
- **The component size is not the hole size.** Calipered dimensions were being cut
  as the openings themselves. A printed hole comes out under size anyway
  (elephant's foot, first-layer squish, perimeter compensation), so nominal is the
  worst case, not the average. `PANEL_FIT = 1.0` separates measurement from
  opening.
- **Mesh degeneracy has three reliable causes**, each producing a valid solid and
  a broken exported surface: unioning parts that share a face exactly; tangency (a
  buttress exactly as wide as the boss it meets); and coplanar caps. The fix is
  always the same — overlap into material by a fraction of a millimetre rather
  than meeting it exactly. **Union order decides which side of a coincident plane
  a fragment lands on**, so adding unrelated geometry elsewhere can make a latent
  one appear.
- **`connected bodies == 1` does not catch a floating tip** — a cone tapering to a
  point in mid-air is still joined to the shaft above it.
- **Print orientation reassigns the axes.** Printed rear-wall-down, the vertical
  axis is *depth* and +z is *down*. Gussets ramped in the wrong axis, cylinders
  extruded along the wrong axis, and a stability script reading raw z as depth all
  trace to this.
- **Transient current is not average current.** The brownout that still constrains
  this machine happens at ~3.7 A of a 5 A budget. Headroom on paper says nothing
  about the step. See [`FUTURE-DEVELOPMENT.md`](FUTURE-DEVELOPMENT.md) H1.

---

# 4. What changed from the original design, and why

Design-phase notes and early conversation memory disagreed with the code often
enough that the drift was tracked deliberately. Every row here is **settled** —
this table exists so a dead idea can be recognised if it resurfaces.

| Topic | Originally | Built as | Why |
|---|---|---|---|
| **Depth** | 64 mm | **79 mm** | The speakers were inside the battery. Nothing checked the depth axis. |
| **Body width** | 258 mm, front module split for the bed | **202 mm, both parts whole** | Fits a 220 bed without splitting. |
| **Crescent shape** | half **circle**, diffuser R117 over an R96 LED field with a 21 mm unlit fade band | half **ellipse** 89 × 62.7 (`CROWN_K` 0.74), **the LED field IS the diffuser** | No fade band needed once the field and the diffuser coincide. |
| **Crescent pixels** | 45 | **48**, rows `{10,10,9,8,7,4}` | Rows butt at 10.4 mm pitch instead of a 1 mm gap — recovers 3 px without +6 mm of height. |
| **LED strip** | SK6812 **144/m** via an **XL6009 boost converter** | SK6812 **60/m, 6 cut segments**, straight off the UPS 5 V rail | No boost converter required. |
| **Battery** | open — LiPo + USB-C candidate, Qi2 already dropped | **Waveshare UPS 3S** (3× 18650), INA219 monitoring | Also made the machine *harder* to tip: mass low down buys more restoring moment than its rearward COM shift costs. |
| **Charge input** | USB-C | **DC barrel jack, 12.6 V 2 A** | The only USB-C on the build is the XIAO's internal flashing port. |
| **Printed parts** | 4 (dome, front module, bottom plate, knob) | **7** — plus an LED carrier and a laser-cut notched acrylic diffuser | The strip needed a controlled standoff across a 185 mm span. |
| **MCU** | XIAO ESP32-S3 **Plus** | Either; standard **XIAO ESP32-S3 confirmed drop-in** | `board: esp32-s3-devkitc-1`, 8 MB flash. |
| **ToF sensor** | part of the sensor stack, for a touchless *wake* gesture | **kept, smaller role** — pre-lights the knob NeoPixel only | Touchless wake was never implemented. See FUTURE F5. |
| **SHT40 temp/hum** | in the planned sensor stack | **removed** | Dropped from the design entirely. |
| **Front ends** | HA + web server + a standalone PWA | **HA + embedded web server** | The PWA was removed. |
| **Media storage** | SD card | **flashed to ESP or streamed from HA** | ESPHome's speaker/mixer pipeline has no SD media source. |
| **Matrix mounting** | press-in backpack scheme | **clips gripping the whole stack** | The press-in scheme was never built; the first clip design was unbuildable in PLA (see §3). |

**Working principles from that era that held up:** search project history before
reasoning from memory on this hardware; the **tested D4/D5 audio-I2C mapping is
the source of truth**, not schematic-derived guesses; bench-first before
soldering.
