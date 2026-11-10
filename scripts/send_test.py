import argparse
import hashlib
import hmac
import json
import urllib.error
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("--secret", default="dev-secret-change-later")
parser.add_argument("--event", default="pull_request")
parser.add_argument("--repo", default="me/demo")
parser.add_argument("--pr", type=int, default=1)
args = parser.parse_args()

body = json.dumps(
    {"action": "opened", "number": args.pr, "repository": {"full_name": args.repo}}
).encode()
signature = "sha256=" + hmac.new(args.secret.encode(), body, hashlib.sha256).hexdigest()

req = urllib.request.Request(
    "http://127.0.0.1:8000/webhook",
    data=body,
    headers={
        "Content-Type": "application/json",
        "X-Hub-Signature-256": signature,
        "X-GitHub-Event": args.event,
    },
)
try:
    print(urllib.request.urlopen(req).read().decode())
except urllib.error.HTTPError as e:
    print(e.code, e.read().decode())
