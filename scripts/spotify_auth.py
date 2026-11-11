#!/usr/bin/env python3
"""
One-time helper: get the Spotify refresh token for the now-playing card.

1. Make an app at https://developer.spotify.com/dashboard
   - Redirect URI:  http://127.0.0.1:8888/callback
   - API:           Web API
2. Run this on your own computer:   python3 scripts/spotify_auth.py
3. Paste the client ID and secret, log in to Spotify in the browser tab it opens.
4. It prints your refresh token. Add all three as repo secrets
   (Settings -> Secrets and variables -> Actions):
     SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN
"""
import base64, getpass, http.server, json, secrets, urllib.parse, urllib.request, webbrowser

REDIRECT = "http://127.0.0.1:8888/callback"
SCOPES = "user-read-currently-playing user-read-recently-played"

cid = input("Spotify client ID: ").strip()
secret = getpass.getpass("Spotify client secret (hidden): ").strip()
state = secrets.token_urlsafe(16)
code_box = {}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        ok = q.get("state", [""])[0] == state and "code" in q
        if ok:
            code_box["code"] = q["code"][0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        msg = "all set ♡ you can close this tab" if ok else "something went wrong, try again"
        self.wfile.write(f"<body style='font-family:sans-serif;background:#FBF4E2;color:#3F6336;"
                         f"display:grid;place-items:center;height:100vh'><h1>{msg}</h1></body>".encode())

    def log_message(self, *a):
        pass


url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
    "client_id": cid, "response_type": "code", "redirect_uri": REDIRECT,
    "scope": SCOPES, "state": state,
})
print("\nOpening Spotify login… if nothing opens, paste this into your browser:\n" + url + "\n")
webbrowser.open(url)

server = http.server.HTTPServer(("127.0.0.1", 8888), Handler)
while "code" not in code_box:
    server.handle_request()

auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
data = urllib.parse.urlencode({"grant_type": "authorization_code", "code": code_box["code"],
                               "redirect_uri": REDIRECT}).encode()
req = urllib.request.Request("https://accounts.spotify.com/api/token", data,
                             {"Authorization": f"Basic {auth}",
                              "Content-Type": "application/x-www-form-urlencoded"})
tok = json.loads(urllib.request.urlopen(req).read())
print("\nSPOTIFY_REFRESH_TOKEN =\n" + tok["refresh_token"] + "\n")
print("Add it, plus your client ID and secret, as repo secrets. Keep it private!")
