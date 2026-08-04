#!/usr/bin/env python3
"""SHEET 3 of 3 -- sensor chain, power and wire routing.

Everything on this sheet comes from HARDWARE.md: the I2C address map, the pin
map, the bus tuning, and the amplifier cautions. It is a WIRING sheet, not a
schematic -- it says what connects to what, in what physical order, and where
each board actually sits inside the enclosure.

Three blocks:
  * I2C DAISY CHAIN  -- one shared bus, in the order the STEMMA QT cables run
  * DIRECT GPIO      -- the four I2S lines, the LED data line, the touch pad
  * POWER            -- barrel jack -> UPS 3S -> 5 V rail -> loads

    python3 gen_wiring.py
    rsvg-convert -b white -z 2 enclosure-wiring.svg -o enclosure-wiring.png
"""
import os

from drawlib import *
from enclosure_geom import *

SHEET_W, SHEET_H = 1189.0, 650.0
MARGIN = 15.0

BW, BH_, GAPX, GAPY = 96.0, 30.0, 122.0, 56.0     # device box grid

# The chain, in PHYSICAL routing order -- start at the Flex (floor, right
# rear), across the floor, up the rear wall, over the crown, down into the
# front module. Keeping it in this order is what keeps the cable short.
#   (label, address, where it lives, status)
# >>> THE TWO THAT MOVE ARE DERIVED, NOT RETYPED. This table had the RTC on the
# >>> rear wall while it was on the bottom plate, and STILL has to be told the amp
# >>> is on the floor -- it said "rear wall, above the UPS" long after the amp
# >>> moved down. A hand-typed location is a copy of a fact, and copies rot: the
# >>> RTC's said-vs-actual disagreed for the whole time it was on the plate, which
# >>> is precisely why its standoffs were unrecognisable.
_RTC_WHERE = (f"bottom plate ({RTC_X:g},{RTC_DEPTH:g})" if RTC_ON_FLOOR
              else f"rear wall ({RTC_WALL_X:g},{RTC_WALL_Y:g}), above the Flex")
_AMP_WHERE = f"bottom plate, floor (x={AMP_X:g}, depth={AMP_DEPTH:g})"
CHAIN = [
    ("DS3231 RTC",      "0x68", _RTC_WHERE,                 "live"),
    ("INA219",          "0x41?", "on the UPS 3S board",     "addr unconfirmed"),
    ("TPA2016 amp",     "0x58", _AMP_WHERE,                 "live"),
    ("BH1750 lux",      "0x23", "rear wall, light pipe",    "live"),
    ("seesaw encoder",  "0x36", "crown, under the knob",    "live"),
    ("VL53L0X ToF",     "0x29", "crown, right of the knob", "live"),
    ("IS31FL3731 #1",   "0x74", "front module, left panel", "live"),
    ("IS31FL3731 #2",   "0x75", "front module, right panel", "ADDR jumper moved"),
]

GPIO = [
    ("GPIO5  / D4", "I2C SDA", "shared bus - every device below"),
    ("GPIO6  / D5", "I2C SCL", "shared bus - 100 kHz, 1 ms timeout"),
    ("GPIO1  / D0", "SK6812 data", f"{CRES_PX} px crescent, front module"),
    ("GPIO4  / D3", "touch L + R", "TOUCH4 - BOTH shoulder pads, one net"),
    ("GPIO2  / D1", "(reserved)", "TOUCH2 - free, to split the pads later"),
    ("GPIO7  / D8", "I2S WS", "ReSpeaker Flex (fixed)"),
    ("GPIO8  / D9", "I2S BCLK", "ReSpeaker Flex (fixed)"),
    ("GPIO43 / D6", "I2S mic DIN", "ReSpeaker Flex (fixed)"),
    ("GPIO44 / D7", "I2S spk DOUT", "ReSpeaker Flex (fixed)"),
]


def box(x, y, w, h, title, sub="", note="", cls="obj"):
    o = [rect(x, y, w, h, cls, 1.5), txt(x + 4, y + 8.5, title, "lbl")]
    if sub:
        o.append(txt(x + w - 4, y + 8.5, sub, "dtx", "end"))
    if note:
        o.append(txt(x + 4, y + 16.5, note, "note"))
    return o


def hlink(x0, x1, y, label=""):
    o = [f'<line class="dim" x1="{n(x0)}" y1="{n(y)}" x2="{n(x1)}" y2="{n(y)}" '
         f'marker-end="url(#arw)"/>']
    if label:
        o.append(txt((x0 + x1)/2, y - 2, label, "dtx", "middle"))
    return o


def vlink(x, y0, y1, label=""):
    o = [f'<line class="dim" x1="{n(x)}" y1="{n(y0)}" x2="{n(x)}" y2="{n(y1)}" '
         f'marker-end="url(#arw)"/>']
    if label:
        o.append(txt(x + 2, (y0 + y1)/2, label, "dtx"))
    return o


# ------------------------------------------------------------ I2C chain
def i2c_block():
    o = [txt(0, -26, "I2C DAISY CHAIN", "blk"),
         txt(0, -16, "one shared bus on GPIO5/6 - STEMMA QT, in physical "
                     "routing order", "lbl")]
    # source: XIAO -> Flex
    o += box(0, 0, BW, BH_, "XIAO ESP32-S3", "", "D4 SDA / D5 SCL")
    o += hlink(BW, BW + 26, BH_/2, "hdrs")
    o += box(BW + 26, 0, BW, BH_ + 10, "ReSpeaker Flex", "",
             "AIC3104  0x18")
    o.append(txt(BW + 30, 34.5, "XVF3800  0x2C", "note"))
    o.append(txt(BW + 30, BH_ + 18, "timing-sensitive - see note b", "dtx"))
    o += hlink(2*BW + 26, 2*BW + 52, BH_/2, "QT")

    # the chain snakes: 3 across, then down, then 3 back, etc.
    per_row = 3
    x0 = 2*BW + 52
    for i, (name, addr, loc, status) in enumerate(CHAIN):
        row, col = divmod(i, per_row)
        col = col if row % 2 == 0 else (per_row - 1 - col)
        x = x0 + col * GAPX
        y = row * GAPY
        cls = "hid" if "PLANNED" in status else "obj"
        o += box(x, y, BW, BH_, name, addr, loc, cls)
        if status not in ("live",):
            o.append(txt(x + 4, y + 24, status, "dtx"))
        # link to the next
        if i < len(CHAIN) - 1:
            nrow, ncol = divmod(i + 1, per_row)
            ncol = ncol if nrow % 2 == 0 else (per_row - 1 - ncol)
            nx = x0 + ncol * GAPX
            ny = nrow * GAPY
            if nrow == row:
                if nx > x:
                    o += hlink(x + BW, nx, y + BH_/2)
                else:
                    o += hlink(x, nx + BW, y + BH_/2)
            else:
                o += vlink(x + BW/2, y + BH_, ny)
    return o


# ---------------------------------------------------------- direct GPIO
def gpio_block():
    o = [txt(0, -26, "DIRECT GPIO", "blk"),
         txt(0, -16, "everything that is not on the I2C bus", "lbl")]
    for i, (pin, fn, dest) in enumerate(GPIO):
        y = i * 11
        o.append(txt(0, y, pin, "lbl"))
        o.append(txt(58, y, fn, "note"))
        o.append(txt(130, y, dest, "note"))
        o.append(line(0, y + 2.4, 300, y + 2.4, "ext"))
    return o


# --------------------------------------------------------------- power
def power_block():
    o = [txt(0, -26, "POWER", "blk"),
         txt(0, -16, "one 5 V / 5 A rail off the UPS", "lbl")]
    o += box(0, 0, 84, 24, "DC barrel jack", "", "rear wall, centred")
    o += hlink(84, 110, 12)
    o += box(110, 0, 84, 24, "UPS 3S", "", "3x 18650, upright")
    o += hlink(194, 220, 12, "5V")
    o += box(220, 0, 84, 24, "5 V / 5 A rail", "", "")
    loads = [("SK6812 crescent", "~1.9 A capped"),
             ("TPA2016 + 2x 4R", "~1.3 A"),
             ("Flex + XIAO + sensors", "~0.5 A")]
    for i, (name, amps) in enumerate(loads):
        y = 44 + i * 26
        o += vlink(262, 24 if i == 0 else y - 26 + 24, y) if i == 0 else []
        o += box(220, y, 128, 22, name, amps, "")
        o.append(line(262, 24 + (i * 26), 262, y, "dim"))
    o.append(txt(0, 130, f"budget  ~3.7 A of 5 A  (crescent hard-capped at 65% "
                         "white in firmware)", "note"))
    return o


# ------------------------------------------------- where each board sits
def location_block():
    """Front outline + side outline with the chain numbers on them."""
    o = [txt(0, -26, "WHERE THEY SIT", "blk"),
         txt(0, -16, "numbers match the chain above", "lbl")]
    sc = 0.62
    fo = [path(d_profile(0, R_BOT), "obj"),
          # semi_e, NOT semi: the crown is a flattened half-ELLIPSE (CROWN_K).
          # This drew a true semicircle of radius CRES_R, which made the
          # crescent on this sheet 26 mm taller than the one on sheets 1 and 2.
          semi_e(W/2, fy(CRES_Y), CRES_R, CRES_RY, "hid"),
          rect(W/2-CLK_W/2, fy(CLK_Y+CLK_H/2), CLK_W, CLK_H, "hid", 1)]
    for sx in (SPK_X, W-SPK_X):
        fo.append(rect(sx-SPK_BODY_W/2, fy(SPK_Y1), SPK_BODY_W, SPK_BODY_H, "hid", 2))
    for mx in mic_x():
        fo.append(circ(mx, fy(MIC_Y), MIC_PORT_D, "hid"))
    # balloons: matrices on the front module
    fo.append(balloon(W/2 - 30, fy(CLK_Y), 7, W/2 - 74, fy(CLK_Y) - 30))
    fo.append(balloon(W/2 + 30, fy(CLK_Y), 8, W/2 + 74, fy(CLK_Y) - 30))
    o.append(f'<g transform="scale({n(sc)})">' + "\n".join(fo) + '</g>')
    o.append(txt(W*sc/2, H*sc + 12, "FRONT (front module)", "lbl", "middle"))

    xs = W*sc + 40
    so = [path(rrect(0, 0, D, H, R_SIDE, R_SIDE, R_SIDE_B, R_SIDE_B), "obj"),
          rect(D - WALL - UPS_D, fy(BP_T + UPS_H), UPS_D, UPS_H, "hid"),
          rect(LIP_T, fy(H - REVEAL), FP_T, H - REVEAL - BP_T, "hid")]
    so.append(balloon(D - WALL, fy(AMP_WALL_Y), 3, D + 34, fy(AMP_WALL_Y) - 16))
    so.append(balloon(D - WALL, fy(LP_Y), 4, D + 34, fy(LP_Y) + 14))
    so.append(balloon(D - ENC_Y, fy(H) + 3, 5, D + 34, fy(H) - 22))
    so.append(balloon(D - TOF_Y, fy(H) + 3, 6, -30, fy(H) - 22))
    so.append(balloon(D - WALL - UPS_D/2, fy(BP_T + UPS_H/2), 2,
                      -30, fy(BP_T + UPS_H/2)))
    so.append(balloon(D - 14, fy(BP_T + 6), 1, -30, fy(BP_T + 20)))
    o.append(f'<g transform="translate({n(xs)},0) scale({n(sc)})">'
             + "\n".join(so) + '</g>')
    o.append(txt(xs + D*sc/2, H*sc + 12, "RIGHT SIDE", "lbl", "middle"))
    return o


# ------------------------------------------------------- sheet assembly
def build():
    o = [svg_header(SHEET_W, SHEET_H), sheet_frame(SHEET_W, SHEET_H, MARGIN)]
    o.append(g("I2C-CHAIN", i2c_block(), 60.0, 70.0))
    o.append(g("DIRECT-GPIO", gpio_block(), 60.0, 300.0))
    o.append(g("POWER", power_block(), 420.0, 300.0))
    o.append(g("LOCATIONS", location_block(), 790.0, 300.0))

    o.append(g("CHAIN-LEGEND", legend(
        [(i + 1, f"{name}   {addr}   {loc}") for i, (name, addr, loc, st)
         in enumerate(CHAIN)],
        "CHAIN KEY  -  balloons on WHERE THEY SIT"), 790.0, 130.0))

    L, ln = [], [0.0]

    def nl(s, cls="note", step=4.7):
        L.append(txt(0, ln[0], s, cls))
        ln[0] += step

    nl("NOTES  (all from HARDWARE.md - that file is authoritative)", "lbl", 6.6)
    nl("a   ONE shared I2C bus on GPIO5/D4 (SDA) and GPIO6/D5 (SCL). D4/D5 is "
       "the tested mapping - do NOT 'correct' it from the schematic.")
    nl("b   BUS RUNS AT 100 kHz WITH A 1 ms TIMEOUT, deliberately. The STEMMA "
       "chain's cable capacitance and pull-ups were starving the")
    nl("    timing-sensitive XVF3800; the slow edges tolerate it and the "
       "timeout lets the XVF3800 clock-stretch while its firmware boots.")
    nl("    Chain order on this sheet is chosen to keep the cable SHORT for "
       "that reason. If it is still flaky, drop toward 10 kHz.")
    nl("c   BRIDGE-TIED AMP OUTPUTS. Every TPA2016 output terminal swings; "
       "there is no output ground. Do NOT common the two speakers'")
    nl("    negative leads and do NOT tie any output to GND - either shorts "
       "half a bridge and can kill the amp.")
    nl("d   The TPA2016's AGC is deliberately OFF (compression 1:1). An active "
       "compressor downstream of the DAC makes the echo path")
    nl("    time-varying and breaks the XVF3800's AEC. It has no NVM, so the "
       "custom component rewrites its config at every boot.")
    nl("e   The second matrix needs its ADDR jumper moved off 0x74 (0x75 / "
       "0x76 / 0x77) and matrix_address_2 set to match.")
    nl("f   VL53L0X is drawn hidden: it is on the bus plan and in the address "
       "map but has NO ESPHome entity yet.")
    nl("g   INA219 address 0x41 is a PLACEHOLDER. Waveshare boards usually sit "
       "at 0x40-0x43; confirm against the boot I2C scan, and if the")
    nl("    readings are nonsense the part may be an INA226 (swap the platform "
       "in packages/hw/power.yaml).")
    nl("h   BOTH TOUCH PADS SHARE GPIO4/D3. Self-capacitance sensing measures "
       "the whole electrode net, so two pads on one net behave as")
    nl("    one electrode split in two - touching either half gives the same "
       "delta. One binary sensor, one threshold, no OR logic.")
    nl("    JOIN THE LEADS AT THE MCU, NOT ACROSS THE CROWN. Each lead drops "
       "down the inside of its own flank to the floor and they meet")
    nl("    at the XIAO. Same wire count either way, and it keeps a ~200 mm "
       "antenna out of the crown, where the SK6812 data line, the")
    nl("    I2S lines and the STEMMA chain all run. A wire taken straight "
       "across the crown would pick that up straight into the sensor.")
    nl("    Cost of sharing: baseline capacitance roughly doubles while the "
       "finger delta does not, so relative sensitivity drops (still")
    nl("    usable), and a side-to-side mismatch cannot be trimmed with "
       "per-pad thresholds. GPIO2/D1 (TOUCH2) is kept free as the escape")
    nl("    hatch - splitting to two channels is one wire at the MCU plus a "
       "few lines of YAML. Calibrate with esp32_touch: setup_mode: true.")
    nl("i   Matrix is TWO IS31FL3731 panels on the STEMMA chain, 0x74 and "
       "0x75 - move the second board's ADDR jumper off 0x74. Bring")
    nl("    one panel up first (matrix_panels: 1); the second address is "
       "never touched until then, so an unwired board is harmless.")
    o.append(g("NOTES", L, 60.0, 430.0))

    o.append(title_block(
        936.0, 520.0, 238.0, 90.0,
        "SOUND MACHINE - WIRING", "sensor chain / power / routing",
        [("SOURCE HARDWARE.md", "BUS"),
         ("UNITS mm   locations NTS", "one I2C bus, 100 kHz, 1 ms timeout"),
         ("GENERATED BY 3d-print/gen_wiring.py", "SHEET 3 of 3"),
         ("REFERENCE ONLY - not a released drawing", "REV A")], 3))

    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(base, "enclosure-wiring.svg")
    open(out, "w").write(build())
    print(f"wrote {out}")
    print(f"\nI2C chain ({len(CHAIN)} devices after the Flex), routing order:")
    print("  XIAO -> ReSpeaker Flex [AIC3104 0x18, XVF3800 0x2C]")
    for i, (name, addr, loc, status) in enumerate(CHAIN):
        print(f"  {i+1}. {name:<18} {addr:<6} {loc:<26} {status}")
    addrs = ["0x18", "0x2C"] + [c[1].rstrip("?") for c in CHAIN]
    dupes = {a for a in addrs if addrs.count(a) > 1}
    print(f"\n{len(addrs)} addresses, "
          + ("no collisions" if not dupes else f"COLLISION: {dupes}"))
