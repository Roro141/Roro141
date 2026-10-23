#!/usr/bin/env python3
"""
3D ASCII monitor -> animated SVG for a GitHub profile README.


Usage:
  python scripts/render.py              
  python scripts/render.py --offline    # skip the API, use config fallback
"""
import argparse, json, math, os, sys, urllib.request
from html import escape
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent

# ---------- canvas ----------
W, H = 76, 27            # character grid
KX, KY = 109, 49         # projection scale: 1 text cell = 1 char when facing forward
CAM = 5.0                # camera distance
RAMP = ".,-~:;=!*#$@"
LIGHT = (-0.35, 0.6, -0.72)

# ---------- screen text grid ----------
COLS, ROWS = 40, 11
SX0, SX1, SY0, SY1 = -0.9, 0.9, 0.1, 1.2   # screen rect on the monitor face


def norm(v):
    m = math.sqrt(sum(c * c for c in v))
    return tuple(c / m for c in v)


L = norm(LIGHT)


# ---------- geometry ----------
def build_points():
    pts = []

    def face(o, u, v, n, step, tag=None):
        nu = max(1, math.ceil(math.hypot(*u) / step))
        nv = max(1, math.ceil(math.hypot(*v) / step))
        for i in range(nu + 1):
            a = i / nu
            for j in range(nv + 1):
                b = j / nv
                p = tuple(o[k] + u[k] * a + v[k] * b for k in range(3))
                pts.append(tag(p, n) if tag else (p, n, False))

    def box(x0, x1, y0, y1, z0, z1, step=0.022, front_tag=None):
        dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
        face((x0, y0, z0), (dx, 0, 0), (0, dy, 0), (0, 0, -1), 0.009 if front_tag else step, front_tag)
        face((x0, y0, z1), (dx, 0, 0), (0, dy, 0), (0, 0, 1), step)
        face((x0, y0, z0), (0, 0, dz), (0, dy, 0), (-1, 0, 0), step)
        face((x1, y0, z0), (0, 0, dz), (0, dy, 0), (1, 0, 0), step)
        face((x0, y0, z0), (dx, 0, 0), (0, 0, dz), (0, -1, 0), step)
        face((x0, y1, z0), (dx, 0, 0), (0, 0, dz), (0, 1, 0), step)

    def screen_tag(p, n):
        x, y = p[0], p[1]
        if SX0 < x < SX1 and SY0 < y < SY1:
            return (p, n, True)
        return (p, n, False)

    box(-1, 1, 0, 1.3, -0.1, 0.1, front_tag=screen_tag)    # monitor
    box(-0.1, 0.1, -0.36, 0, 0.02, 0.12)                  # neck
    box(-0.55, 0.55, -0.43, -0.36, -0.3, 0.32)             # base
    return pts


# ---------- one frame ----------
def transform(p, ca, sa, cb, sb):
    """tilt back around X first, then turn around the vertical axis,
    so horizontal edges (and text rows) stay horizontal while it sways"""
    x, y, z = p
    y -= 0.45
    y1 = y * cb - z * sb
    z1 = y * sb + z * cb
    return x * ca + z1 * sa, y1, -x * sa + z1 * ca


def render_frame(pts, yaw, pitch, screen):
    ca, sa = math.cos(yaw), math.sin(yaw)
    cb, sb = math.cos(pitch), math.sin(pitch)
    buf = [" "] * (W * H)
    kind = [0] * (W * H)          # 0 = body, 1 = screen text
    zb = [0.0] * (W * H)
    scr = [False] * (W * H)       # pixel shows the screen surface
    front_visible = False
    for p, (nx, ny, nz), on_screen in pts:
        x1, y2, z2 = transform(p, ca, sa, cb, sb)
        nx1, ny2, nz2 = transform((nx, ny + 0.45, nz), ca, sa, cb, sb)  # rotate normal (undo y shift)
        zz = z2 + CAM
        if nx1 * x1 + ny2 * y2 + nz2 * zz >= 0:      # backface cull
            continue
        ooz = 1 / zz
        X = round(W / 2 + 0.25 + KX * x1 * ooz)
        Y = round(H / 2 - KY * y2 * ooz)
        if not (0 <= X < W and 0 <= Y < H):
            continue
        k = X + W * Y
        if ooz <= zb[k]:
            continue
        zb[k] = ooz
        if on_screen:
            buf[k], scr[k], front_visible = " ", True, True
        else:
            lum = nx1 * L[0] + ny2 * L[1] + nz2 * L[2]
            i = max(0, min(len(RAMP) - 1, round((lum + 1) / 2 * 9)))
            buf[k], scr[k] = RAMP[i], False

    # screen text: project each character cell's centre so letters stay crisp,
    # then nudge positions so rows and columns never collide (no dropped chars)
    if front_visible:
        def proj(c, r):
            xc = SX0 + (c + 0.5) * (SX1 - SX0) / COLS
            yc = SY1 - (r + 0.5) * (SY1 - SY0) / ROWS
            x1, y2, z2 = transform((xc, yc, -0.1), ca, sa, cb, sb)
            zz = z2 + CAM
            return W / 2 + 0.25 + KX * x1 / zz, H / 2 + 0.25 - KY * y2 / zz

        prev_row_y = -1
        for r, line in enumerate(screen[:ROWS]):
            ry = round(proj(COLS / 2, r)[1])
            ry_fixed = max(ry, prev_row_y + 1)
            prev_row_y = ry_fixed
            prev_x = -1
            for c, ch in enumerate(line[:COLS]):
                fx, fy = proj(c, r)
                X = max(round(fx), prev_x + 1)
                prev_x = X
                Y = ry_fixed            # keep each text line on one row
                if ch == " ":
                    continue
                if 0 <= X < W and 0 <= Y < H and scr[X + W * Y]:
                    buf[X + W * Y], kind[X + W * Y] = ch, 1
    return buf, kind


# ---------- screen content over time ----------
def screen_lines(cfg, project, desc):
    lines = [
        "",
        f" $ whoami",
        f" > {cfg['name']}",
        f"   {cfg['role']}",
        "",
        " $ cat now.txt",
        " > currently building:",
        f"   {project}",
    ]
    if desc:
        lines.append(f"   {desc}")
    return [s[:COLS] for s in lines]


def typed(lines, n, cursor_on):
    out, rem, done = [], n, False
    for s in lines:
        if rem >= len(s):
            out.append(s)
            rem -= len(s)
        else:
            out.append(s[:rem] + ("█" if cursor_on else ""))
            done = True
            break
        if rem == 0 and not done:
            pass
    if not done:  # finished typing: blinking prompt on the next line
        out.append(" $ " + ("█" if cursor_on else ""))
    return out


# ---------- SVG ----------
def to_svg(frames, theme, duration):
    fs, lh = 13, 15.6
    cw = fs * 0.6
    pad = 10
    # crop to the area any frame actually draws in, so there's no empty margin
    rows = [r for r in range(H) if any("".join(b[r * W:(r + 1) * W]).strip() for b, _ in frames)]
    cols = [c for c in range(W) if any(b[r * W + c] != " " for b, _ in frames for r in range(H))]
    m = 4
    vx = pad + cols[0] * cw - m
    vy = pad + rows[0] * lh - m
    width = round((cols[-1] - cols[0] + 1) * cw + 2 * m)
    height = round((rows[-1] - rows[0] + 1) * lh + 2 * m)
    n = len(frames)
    pct = 100 / n
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="{vx:.1f} {vy:.1f} {width} {height}" xml:space="preserve" role="img" aria-label="Rotating 3D ASCII computer">',
        "<style>",
        f"text{{font:{fs}px ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace;"
        f"white-space:pre;fill:{theme['body']}}}",
        f".s{{fill:{theme['screen']}}}",
        f".f{{visibility:hidden;animation:k {duration}s linear infinite}}",
        f"@keyframes k{{0%{{visibility:visible}}{pct:.4f}%,100%{{visibility:hidden}}}}",
        "@media (prefers-reduced-motion:reduce){.f{animation:none}.f0{visibility:visible}}",
        "</style>",
    ]
    for i, (buf, kind) in enumerate(frames):
        delay = i * duration / n - duration
        out.append(f'<g class="f f{i}" style="animation-delay:{delay:.3f}s">')
        for r in range(H):
            row = buf[r * W:(r + 1) * W]
            kr = kind[r * W:(r + 1) * W]
            if not "".join(row).strip():
                continue
            # trim trailing spaces; keep leading for alignment
            end = len("".join(row).rstrip())
            parts, cur, curk = [], "", None
            for ch, k in zip(row[:end], kr[:end]):
                if k != curk and cur:
                    parts.append((cur, curk))
                    cur = ""
                curk = k
                cur += ch
            if cur:
                parts.append((cur, curk))
            body = "".join(
                f'<tspan class="s">{escape(t)}</tspan>' if k else escape(t) for t, k in parts
            )
            y = pad + (r + 0.8) * lh
            out.append(f'<text x="{pad}" y="{y:.1f}">{body}</text>')
        out.append("</g>")
    out.append("</svg>")
    return "\n".join(out)


# ---------- data ----------
def latest_project(cfg):
    user = cfg["github_user"]
    url = f"https://api.github.com/users/{user}/repos?sort=pushed&per_page=30"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=20) as r:
        repos = json.load(r)
    skip = {s.lower() for s in cfg.get("exclude_repos", [])} | {user.lower()}
    for repo in repos:
        if repo["fork"] or repo["archived"] or repo["name"].lower() in skip:
            continue
        name = cfg.get("display_names", {}).get(repo["name"], repo["name"])
        return name, repo.get("description") or ""
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    cfg = yaml.safe_load((ROOT / "config.yml").read_text())
    project, desc = cfg.get("pin_project") or "", cfg.get("pin_description") or ""
    if not project and not args.offline:
        try:
            found = latest_project(cfg)
            if found:
                project, desc = found
        except Exception as e:
            print(f"GitHub API failed ({e}); using fallback", file=sys.stderr)
    if not project:
        project, desc = cfg["fallback_project"], cfg.get("fallback_description", "")

    lines = screen_lines(cfg, project, desc)
    total = sum(len(s) for s in lines)

    fps, seconds = cfg.get("fps", 12), cfg.get("loop_seconds", 9)
    nframes = fps * seconds
    type_frames = int(nframes * 0.6)
    sway = math.radians(cfg.get("sway_degrees", 32))
    pts = build_points()

    frames = []
    for f in range(nframes):
        t = f / nframes
        yaw = sway * math.sin(2 * math.pi * t) ** 3   # cubed: lingers facing forward
        pitch = 0.15
        n = min(total, int(total * f / type_frames))
        cursor = (f // (fps // 2)) % 2 == 0
        frames.append(render_frame(pts, yaw, pitch, typed(lines, n, cursor)))

    out = ROOT / "assets"
    out.mkdir(exist_ok=True)
    for mode in ("dark", "light"):
        svg = to_svg(frames, cfg["colors"][mode], seconds)
        (out / f"monitor-{mode}.svg").write_text(svg)
        print(f"assets/monitor-{mode}.svg  {len(svg) // 1024} KB  ({nframes} frames)  project={project!r}")


if __name__ == "__main__":
    main()
