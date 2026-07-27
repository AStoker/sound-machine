#!/usr/bin/env python3
"""Shared SVG drawing primitives for the Sound Machine enclosure sheets.

Pure geometry/annotation helpers -- no knowledge of the part. Used by
gen_drawing.py (shell), gen_internals.py (internals + fixings) and
gen_wiring.py (sensor chain).
"""
# --------------------------------------------------------------- primitives
def n(v):
    return f"{v:.3f}".rstrip("0").rstrip(".")


def dt(v):
    """Dimension text: integer when whole, else one decimal."""
    return f"{v:.0f}" if abs(v - round(v)) < 0.05 else f"{v:.1f}"


def rrect(x, y, w, h, rtl, rtr=None, rbr=None, rbl=None):
    """Rounded rect path, y-down, clockwise."""
    rtr = rtl if rtr is None else rtr
    rbr = rtl if rbr is None else rbr
    rbl = rtl if rbl is None else rbl
    return (f"M{n(x+rtl)},{n(y)} H{n(x+w-rtr)} A{n(rtr)},{n(rtr)} 0 0 1 {n(x+w)},{n(y+rtr)} "
            f"V{n(y+h-rbr)} A{n(rbr)},{n(rbr)} 0 0 1 {n(x+w-rbr)},{n(y+h)} "
            f"H{n(x+rbl)} A{n(rbl)},{n(rbl)} 0 0 1 {n(x)},{n(y+h-rbl)} "
            f"V{n(y+rtl)} A{n(rtl)},{n(rtl)} 0 0 1 {n(x+rtl)},{n(y)} Z")


def path(d, cls="obj"):
    return f'<path class="{cls}" d="{d}"/>'


def rect(x, y, w, h, cls="obj", r=0.0):
    if r:
        return path(rrect(x, y, w, h, r), cls)
    return f'<rect class="{cls}" x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}"/>'


def circ(cx, cy, d, cls="obj"):
    return f'<circle class="{cls}" cx="{n(cx)}" cy="{n(cy)}" r="{n(d/2)}"/>'


def line(x1, y1, x2, y2, cls="obj"):
    return f'<line class="{cls}" x1="{n(x1)}" y1="{n(y1)}" x2="{n(x2)}" y2="{n(y2)}"/>'


def semi(cx, cy, r, cls="obj"):
    """Semicircle, flat side down, sitting on y=cy."""
    return path(f"M{n(cx-r)},{n(cy)} A{n(r)},{n(r)} 0 0 1 {n(cx+r)},{n(cy)} Z", cls)


def txt(x, y, s, cls="note", anchor="start", rot=None):
    tr = f' transform="rotate({rot} {n(x)} {n(y)})"' if rot is not None else ""
    return (f'<text class="{cls}" x="{n(x)}" y="{n(y)}" '
            f'text-anchor="{anchor}"{tr}>{s}</text>')


def g(gid, body, tx=0.0, ty=0.0, cls=None):
    t = f' transform="translate({n(tx)},{n(ty)})"' if (tx or ty) else ""
    c = f' class="{cls}"' if cls else ""
    return f'<g id="{gid}"{c}{t}>\n' + "\n".join(b for b in body if b) + "\n</g>"


# -------------------------------------------------------------- dimensions
ARR = 'marker-start="url(#arw)" marker-end="url(#arw)"'


def dim_h(x1, x2, y, s=None, ext=None):
    """Horizontal dimension. `ext` = y of the feature edge to run witness lines from."""
    o = []
    if ext is not None:
        off = 2.0 if y > ext else -2.0
        for x in (x1, x2):
            o.append(line(x, ext, x, y + off, "ext"))
    o.append(f'<line class="dim" x1="{n(x1)}" y1="{n(y)}" x2="{n(x2)}" y2="{n(y)}" {ARR}/>')
    o.append(txt((x1+x2)/2, y - 1.4, s or dt(abs(x2-x1)), "dtx", "middle"))
    return "".join(o)


def dim_h_out(x1, x2, y, s=None, ext=None, side=1):
    """Short horizontal dim: arrows point inward from outside, text offset."""
    o = []
    if ext is not None:
        off = 2.0 if y > ext else -2.0
        for x in (x1, x2):
            o.append(line(x, ext, x, y + off, "ext"))
    o.append(f'<line class="dim" x1="{n(x1-7)}" y1="{n(y)}" x2="{n(x1)}" y2="{n(y)}" marker-start="url(#arw)"/>')
    o.append(f'<line class="dim" x1="{n(x2)}" y1="{n(y)}" x2="{n(x2+7)}" y2="{n(y)}" marker-end="url(#arw)"/>')
    o.append(line(x1, y, x2, y, "dim"))
    tx_ = x2 + 8.5 if side > 0 else x1 - 8.5
    o.append(txt(tx_, y + 1.2, s or dt(abs(x2-x1)), "dtx", "start" if side > 0 else "end"))
    return "".join(o)


def dim_v(y1, y2, x, s=None, ext=None):
    """Vertical dimension. `ext` = x of the feature edge."""
    o = []
    if ext is not None:
        off = 2.0 if x > ext else -2.0
        for y in (y1, y2):
            o.append(line(ext, y, x + off, y, "ext"))
    o.append(f'<line class="dim" x1="{n(x)}" y1="{n(y1)}" x2="{n(x)}" y2="{n(y2)}" {ARR}/>')
    o.append(txt(x - 1.4, (y1+y2)/2, s or dt(abs(y2-y1)), "dtx", "middle", rot=-90))
    return "".join(o)


def dim_v_out(y1, y2, x, s=None, ext=None):
    o = []
    if ext is not None:
        off = 2.0 if x > ext else -2.0
        for y in (y1, y2):
            o.append(line(ext, y, x + off, y, "ext"))
    o.append(f'<line class="dim" x1="{n(x)}" y1="{n(y1-7)}" x2="{n(x)}" y2="{n(y1)}" marker-start="url(#arw)"/>')
    o.append(f'<line class="dim" x1="{n(x)}" y1="{n(y2)}" x2="{n(x)}" y2="{n(y2+7)}" marker-end="url(#arw)"/>')
    o.append(line(x, y1, x, y2, "dim"))
    o.append(txt(x - 1.4, y2 + 9.0, s or dt(abs(y2-y1)), "dtx", "middle", rot=-90))
    return "".join(o)


def leader(x, y, dx, dy, s, anchor="start", shoulder=6.0):
    """Leader: arrow at (x,y), dogleg to (x+dx, y+dy), horizontal shoulder, text."""
    ex, ey = x + dx, y + dy
    sx = ex + (shoulder if anchor == "start" else -shoulder)
    return ("".join([
        f'<line class="dim" x1="{n(x)}" y1="{n(y)}" x2="{n(ex)}" y2="{n(ey)}" marker-start="url(#arw)"/>',
        line(ex, ey, sx, ey, "dim"),
        txt(sx + (1.2 if anchor == "start" else -1.2), ey + 1.1, s, "dtx", anchor),
    ]))


def cl_h(x1, x2, y):
    return line(x1, y, x2, y, "ctr")


def cl_v(x, y1, y2):
    return line(x, y1, x, y2, "ctr")


def balloon(x, y, num, tx_, ty_):
    """Numbered balloon at (tx_,ty_) with a leader to (x,y)."""
    return "".join([
        f'<line class="dim" x1="{n(x)}" y1="{n(y)}" x2="{n(tx_)}" y2="{n(ty_)}" marker-start="url(#arw)"/>',
        f'<circle class="bal" cx="{n(tx_)}" cy="{n(ty_)}" r="4.6"/>',
        txt(tx_, ty_ + 1.6, str(num), "balt", "middle"),
    ])


def traj(x1, y1, x2, y2):
    return line(x1, y1, x2, y2, "traj")




def svg_header(sw, sh):
    """Opening <svg> + marker/style defs. Every sheet shares this chrome."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
            f'width="{n(sw)}mm" height="{n(sh)}mm" '
            f'viewBox="0 0 {n(sw)} {n(sh)}">'
            + f"""<defs>
<marker id="arw" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="3.4"
        markerHeight="3.4" orient="auto-start-reverse" markerUnits="userSpaceOnUse">
  <path d="M0,1.4 L10,5 L0,8.6 z" fill="#1b1b1b"/>
</marker>
<style>
  text {{ font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; fill:#1b1b1b; }}
  .obj  {{ fill:none; stroke:#1b1b1b; stroke-width:0.55; }}
  .hid  {{ fill:none; stroke:#7a7a7a; stroke-width:0.35; stroke-dasharray:2.6 1.6; }}
  .phan {{ fill:none; stroke:#9a9a9a; stroke-width:0.32; stroke-dasharray:7 1.6 1.2 1.6; }}
  .led  {{ fill:none; stroke:#9a9a9a; stroke-width:0.3; }}
  .ctr  {{ fill:none; stroke:#b03a3a; stroke-width:0.3;  stroke-dasharray:9 1.8 1.6 1.8; }}
  .dim  {{ fill:none; stroke:#1b1b1b; stroke-width:0.3; }}
  .ext  {{ fill:none; stroke:#1b1b1b; stroke-width:0.25; }}
  .traj {{ fill:none; stroke:#4a6fa5; stroke-width:0.35; stroke-dasharray:5 2; }}
  .bal  {{ fill:#ffffff; stroke:#1b1b1b; stroke-width:0.45; }}
  .dtx  {{ font-size:3.1px; }}
  .balt {{ font-size:4.4px; font-weight:600; }}
  .note {{ font-size:3.4px; }}
  .lbl  {{ font-size:4.6px; font-weight:600; letter-spacing:0.6px; }}
  .blk  {{ font-size:6.4px; font-weight:700; letter-spacing:1.4px; fill:#4a6fa5; }}
  .ttl  {{ font-size:9px;   font-weight:700; letter-spacing:1px; }}
  .sub  {{ font-size:4.4px; fill:#555; }}
  .frame{{ fill:none; stroke:#1b1b1b; stroke-width:0.5; }}
  .tb   {{ fill:none; stroke:#1b1b1b; stroke-width:0.35; }}
</style>
</defs>
<rect x="0" y="0" width="{n(sw)}" height="{n(sh)}" fill="#ffffff"/>""")


def sheet_frame(sw, sh, margin):
    return (f'<rect class="frame" x="{n(margin)}" y="{n(margin)}" '
            f'width="{n(sw-2*margin)}" height="{n(sh-2*margin)}"/>')


def title_block(x, y, w, h, title, subtitle, rows, sheet_no):
    """rows: list of (left, right) strings, one per band."""
    o = [f'<rect class="tb" x="0" y="0" width="{n(w)}" height="{n(h)}"/>',
         line(0, 26, w, 26, "tb"),
         txt(6, 12, title, "ttl"), txt(6, 20, subtitle, "sub")]
    band = (h - 26) / max(len(rows), 1)
    for i, (l, r) in enumerate(rows):
        yb = 26 + i * band
        if i:
            o.append(line(0, yb, w, yb, "tb"))
        o.append(line(w*0.5, yb, w*0.5, yb + band, "tb"))
        o.append(txt(6, yb + band*0.62, l, "note"))
        o.append(txt(w*0.5 + 6, yb + band*0.62, r, "note"))
    return g("TITLE-BLOCK", o, x, y)


def legend(items, title="LEGEND", col_w=None, row_h=8.0, pad=5.0):
    """Boxed, numbered key. `items` is a list of strings in balloon order, or of
    (number, text) pairs when the numbering is not 1..n. Every numbered balloon
    on a sheet must resolve here -- a bare number on a drawing is useless."""
    rows = [(str(i + 1), t) if isinstance(t, str) else (str(t[0]), t[1])
            for i, t in enumerate(items)]
    w = col_w or (max(len(t) for _, t in rows) * 1.62 + 22)
    h = pad + 9 + len(rows) * row_h + pad
    o = [f'<rect class="tb" x="0" y="0" width="{n(w)}" height="{n(h)}"/>',
         txt(pad, pad + 6, title, "lbl")]
    for i, (num, text) in enumerate(rows):
        cy = pad + 9 + i * row_h + row_h * 0.62
        o.append(f'<circle class="bal" cx="{n(pad + 4.6)}" cy="{n(cy - 1.5)}" r="3.6"/>')
        o.append(txt(pad + 4.6, cy, num, "dtx", "middle"))
        o.append(txt(pad + 12, cy, text, "note"))
    return o
