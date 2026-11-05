import hashlib
import hmac
import json
import sys
import urllib.error
import urllib.request

secret = sys.argv[1] if len(sys.argv) > 1 else "dev-secret-change-later"
event = sys.argv[2] if len(sys.argv) > 2 else "pull_request"

body = json.dumps(
    {"action": "opened", "number": 1, "repository": {"full_name": "me/demo"}}
).encode()
signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

req = urllib.request.Request(
    "http://127.0.0.1:8000/webhook",
    data=body,
    headers={
        "Content-Type": "application/json",
        "X-Hub-Signature-256": signature,
        "X-GitHub-Event": event,
    },
)
try:
    print(urllib.request.urlopen(req).read().decode())
except urllib.error.HTTPError as e:
    print(e.code, e.read().decode())