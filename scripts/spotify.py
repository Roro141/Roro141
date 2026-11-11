#!/usr/bin/env python3
"""
Spotify "now playing" discman card -> assets/spotify.svg for the profile README.

Shows the song playing right now; when nothing is playing, the last song played.
The SVG only changes when the song (or playing/paused state) changes, so the
GitHub Action only commits when there's something new.

Needs three repo secrets (see scripts/spotify_auth.py to get the refresh token):
  SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN

Usage:
  python scripts/spotify.py          # live, from the secrets above
  python scripts/spotify.py --demo   # render a sample card, no Spotify needed
"""
import argparse, base64, json, os, sys, urllib.error, urllib.parse, urllib.request
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "spotify.svg"

TOKEN_URL = "https://accounts.spotify.com/api/token"
NOW_URL = "https://api.spotify.com/v1/me/player/currently-playing"
RECENT_URL = "https://api.spotify.com/v1/me/player/recently-played?limit=1"

# palette, pulled from the pond wallpaper
CREAM, PINK, PINK_DK, ROSE, SAGE, SAGE_LT, GREEN, GREEN_DK, BLUE = (
    "#FBF4E2", "#F4B8C8", "#A8406A", "#E58AA8", "#B9CF9A", "#DDEBC8", "#5E8A52", "#3F6336", "#C9D6F4")


# ---------- spotify ----------
def http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=20) as r:
        body = r.read()
        return r.status, (json.loads(body) if body else None)


def access_token(cid, secret, refresh):
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    data = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": refresh}).encode()
    _, j = http(TOKEN_URL, data, {"Authorization": f"Basic {auth}",
                                  "Content-Type": "application/x-www-form-urlencoded"})
    return j["access_token"]


def track_info(item):
    album = item.get("album") or {}
    imgs = album.get("images") or []
    # middle size (~300px) keeps the label crisp without bloating the svg
    img = imgs[1]["url"] if len(imgs) > 1 else (imgs[0]["url"] if imgs else None)
    return {
        "title": item.get("name", "unknown"),
        "artist": ", ".join(a["name"] for a in item.get("artists", [])) or "unknown",
        "image": img,
    }


def fetch():
    cid = os.environ.get("SPOTIFY_CLIENT_ID")
    secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    refresh = os.environ.get("SPOTIFY_REFRESH_TOKEN")
    if not (cid and secret and refresh):
        return {"state": "setup"}

    tok = access_token(cid, secret, refresh)
    h = {"Authorization": f"Bearer {tok}"}

    status, now = http(NOW_URL, headers=h)
    if status == 200 and now and now.get("item") and now.get("currently_playing_type") == "track":
        info = track_info(now["item"])
        info["state"] = "playing" if now.get("is_playing") else "paused"
        return info

    _, recent = http(RECENT_URL, headers=h)
    items = (recent or {}).get("items") or []
    if items:
        info = track_info(items[0]["track"])
        info["state"] = "recent"
        return info
    return {"state": "idle"}


def image_data_uri(url):
    # GitHub renders README svgs as images, which can't load outside urls,
    # so the album art is embedded
    if not url:
        return None
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return "data:image/jpeg;base64," + base64.b64encode(r.read()).decode()
    except (urllib.error.URLError, TimeoutError):
        return None


# ---------- svg ----------
def clip(s, n):
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def render(info, art):
    state = info["state"]
    playing = state == "playing"
    label = {
        "playing": "♪ now playing",
        "paused": "❚❚ paused",
        "recent": "✿ last played",
        "idle": "✿ nothing yet",
        "setup": "✿ almost ready",
    }[state]
    title = info.get("title") or ("connect spotify secrets" if state == "setup" else "press play ♡")
    artist = info.get("artist") or ("see scripts/spotify_auth.py" if state == "setup" else "spotify is quiet")
    title, artist = escape(clip(title, 30)), escape(clip(artist, 38))

    spin = "animation: spin 3.6s linear infinite;" if playing else ""
    eq = "animation: eq 0.9s ease-in-out infinite alternate;" if playing else "transform: scaleY(0.25);"
    label_fill = PINK_DK if playing else GREEN_DK

    disc_label = (
        f'<image href="{art}" x="54" y="54" width="52" height="52" clip-path="url(#lbl)" preserveAspectRatio="xMidYMid slice"/>'
        if art else f'<circle cx="80" cy="80" r="26" fill="{PINK}"/>'
    )

    bars = "".join(
        f'<rect class="eq" x="{407 + i * 13}" y="104" width="8" height="26" rx="3" fill="{SAGE_LT}" style="animation-delay:{d}s"/>'
        for i, d in enumerate([0, -0.4, -0.15, -0.7, -0.3, -0.55])
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="520" height="164" viewBox="0 0 520 164" role="img" aria-label="Spotify: {label.split(' ', 1)[1]}: {title} by {artist}">
<style>
@keyframes spin {{ to {{ transform: rotate(360deg) }} }}
@keyframes eq {{ from {{ transform: scaleY(0.2) }} to {{ transform: scaleY(1) }} }}
.disc {{ transform-origin: 80px 80px; {spin} }}
.eq {{ transform-box: fill-box; transform-origin: bottom; {eq} }}
text {{ font-family: ui-rounded, 'SF Pro Rounded', 'Nunito', 'Segoe UI', system-ui, sans-serif; }}
.lcd {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; }}
</style>
<defs>
  <radialGradient id="cd" cx="50%" cy="50%" r="50%">
    <stop offset="0" stop-color="#FFFFFF"/><stop offset="0.4" stop-color="#F9D6E2"/>
    <stop offset="0.65" stop-color="{BLUE}"/><stop offset="0.85" stop-color="{SAGE_LT}"/>
    <stop offset="1" stop-color="{PINK}"/>
  </radialGradient>
  <clipPath id="lbl"><circle cx="80" cy="80" r="26"/></clipPath>
</defs>
<rect x="4" y="10" width="512" height="148" rx="30" fill="{SAGE}" stroke="{GREEN_DK}" stroke-width="4"/>
<rect x="430" y="2" width="72" height="20" rx="2" fill="{PINK}" opacity="0.85" transform="rotate(-6 466 12)"/>
<circle cx="80" cy="84" r="64" fill="{CREAM}" stroke="{GREEN_DK}" stroke-width="4"/>
<g transform="translate(0 4)">
  <g class="disc">
    <circle cx="80" cy="80" r="54" fill="url(#cd)" stroke="{ROSE}" stroke-width="2"/>
    <path d="M80 80 L80 26 A54 54 0 0 1 118 42 Z" fill="#FFFFFF" opacity="0.55"/>
    <path d="M80 80 L80 134 A54 54 0 0 1 42 118 Z" fill="#FFFFFF" opacity="0.3"/>
    {disc_label}
    <circle cx="80" cy="80" r="26" fill="none" stroke="{PINK_DK}" stroke-width="2.5"/>
    <circle cx="80" cy="80" r="5" fill="{CREAM}" stroke="{GREEN_DK}" stroke-width="1.5"/>
  </g>
</g>
<rect x="164" y="26" width="132" height="24" rx="12" fill="{CREAM}" stroke="{label_fill}" stroke-width="2"/>
<text x="230" y="43" text-anchor="middle" font-size="13" font-weight="600" letter-spacing="1" fill="{label_fill}">{label}</text>
<text x="166" y="78" font-size="21" font-weight="700" fill="{GREEN_DK}">{title}</text>
<text x="166" y="100" font-size="15" font-weight="500" fill="{PINK_DK}">{artist}</text>
<rect x="164" y="112" width="214" height="30" rx="8" fill="{GREEN_DK}"/>
<text class="lcd" x="176" y="132" font-size="13" fill="{SAGE_LT}">POND·MAN ES-01  ♡ spotify</text>
<rect x="384" y="100" width="120" height="44" rx="10" fill="{GREEN_DK}"/>
{bars}
</svg>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="render a sample card")
    args = ap.parse_args()

    if args.demo:
        info, art = {"state": "playing", "title": "Sample Song Title", "artist": "Sample Artist"}, None
    else:
        try:
            info = fetch()
        except (urllib.error.URLError, KeyError, TimeoutError) as e:
            print(f"spotify unreachable, keeping the current card: {e}", file=sys.stderr)
            return
        art = image_data_uri(info.get("image"))

    OUT.parent.mkdir(exist_ok=True)
    svg = render(info, art)
    if OUT.exists() and OUT.read_text() == svg:
        print("no change")
        return
    OUT.write_text(svg)
    print(f"wrote {OUT.relative_to(ROOT)} ({info['state']})")


if __name__ == "__main__":
    main()
