import hashlib
import hmac
import json
import sys
import urllib.error
import urllib.request

secret = sys.argv[1] if len(sys.argv) > 1 else "dev-secret-change-later"
body = json.dumps({"hello": "world"}).encode()
signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

req = urllib.request.Request(
    "http://127.0.0.1:8000/webhook",
    data=body,
    headers={
        "Content-Type": "application/json",
        "X-Hub-Signature-256": signature,
    },
)
try:
    print(urllib.request.urlopen(req).read().decode())
except urllib.error.HTTPError as e:
    print(e.code, e.read().decode())