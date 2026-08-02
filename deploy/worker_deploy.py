#!/usr/bin/env python3
"""Deploy assistant/worker.js to Cloudflare Workers via the Cloudflare API.

Stdlib only. Runs inside the deploy-worker GitHub Actions workflow, which
maps repository secrets into the environment, so no credential ever leaves
the secret stores.

Required env:
  CLOUDFLARE_API_TOKEN   token from the "Edit Cloudflare Workers" template
  SLACK_BOT_TOKEN        forwarded into the worker as a secret
  SLACK_SIGNING_SECRET   forwarded into the worker as a secret
  FIREWORKS_API_KEY      forwarded into the worker as a secret
Optional env (forwarded when present):
  ANTHROPIC_API_KEY      live deployment status in answers
  GH_DISPATCH_TOKEN      instant apply: workflow dispatch from the worker

Prints the public worker URL on success.
"""

import json
import os
import sys
import urllib.error
import urllib.request
import uuid

CF = "https://api.cloudflare.com/client/v4"
SCRIPT_NAME = "forsocialsss-assistant"
WORKER_SOURCE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assistant", "worker.js",
)

FORWARD_SECRETS = [
    "SLACK_BOT_TOKEN",
    "SLACK_SIGNING_SECRET",
    "FIREWORKS_API_KEY",
    "ANTHROPIC_API_KEY",
    "GH_DISPATCH_TOKEN",
]


def die(msg):
    print(f"worker_deploy.py: error: {msg}", file=sys.stderr)
    sys.exit(1)


def cf(method, path, body=None, raw_body=None, content_type=None):
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        die("CLOUDFLARE_API_TOKEN is not set")
    if raw_body is not None:
        data = raw_body
    elif body is not None:
        data = json.dumps(body).encode()
        content_type = "application/json"
    else:
        data = None
    req = urllib.request.Request(CF + path, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if content_type:
        req.add_header("content-type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        die(f"{method} {path} -> HTTP {e.code}:\n{detail[:1200]}")


def account_id():
    resp = cf("GET", "/accounts")
    accounts = resp.get("result") or []
    if not accounts:
        die("the API token cannot list any Cloudflare accounts; recreate it "
            "from the 'Edit Cloudflare Workers' template")
    return accounts[0]["id"]


def upload_script(acct):
    with open(WORKER_SOURCE, "rb") as f:
        source = f.read()
    boundary = uuid.uuid4().hex
    metadata = json.dumps({
        "main_module": "worker.js",
        "compatibility_date": "2026-01-01",
    }).encode()
    parts = []
    parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="metadata"\r\n'
        f"Content-Type: application/json\r\n\r\n".encode() + metadata + b"\r\n"
    )
    parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="worker.js"; filename="worker.js"\r\n'
        f"Content-Type: application/javascript+module\r\n\r\n".encode()
        + source + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    cf("PUT", f"/accounts/{acct}/workers/scripts/{SCRIPT_NAME}",
       raw_body=body,
       content_type=f"multipart/form-data; boundary={boundary}")
    print(f"script: uploaded {SCRIPT_NAME}")


def set_secrets(acct):
    set_names, missing = [], []
    for name in FORWARD_SECRETS:
        value = os.environ.get(name, "").strip()
        if not value:
            missing.append(name)
            continue
        cf("PUT", f"/accounts/{acct}/workers/scripts/{SCRIPT_NAME}/secrets",
           body={"name": name, "text": value, "type": "secret_text"})
        set_names.append(name)
    print(f"secrets: set {', '.join(set_names)}")
    required_missing = [m for m in missing
                        if m in ("SLACK_BOT_TOKEN", "SLACK_SIGNING_SECRET",
                                 "FIREWORKS_API_KEY")]
    if required_missing:
        die(f"required worker secrets missing from the environment: "
            f"{', '.join(required_missing)}")
    for m in missing:
        print(f"secrets: optional {m} not provided, feature degraded")


def ensure_subdomain(acct):
    resp = cf("GET", f"/accounts/{acct}/workers/subdomain")
    sub = (resp.get("result") or {}).get("subdomain")
    if not sub:
        # New accounts have no workers.dev subdomain yet; register one from
        # the account id, which is guaranteed unique.
        candidate = f"fs-{acct[:12]}".lower()
        resp = cf("PUT", f"/accounts/{acct}/workers/subdomain",
                  body={"subdomain": candidate})
        sub = (resp.get("result") or {}).get("subdomain") or candidate
        print(f"subdomain: registered {sub}.workers.dev")
    cf("POST", f"/accounts/{acct}/workers/scripts/{SCRIPT_NAME}/subdomain",
       body={"enabled": True, "previews_enabled": False})
    return sub


def main():
    acct = account_id()
    print(f"account: {acct}")
    upload_script(acct)
    set_secrets(acct)
    sub = ensure_subdomain(acct)
    url = f"https://{SCRIPT_NAME}.{sub}.workers.dev"
    print()
    print(f"worker deployed: {url}")
    print("next: set this URL as the Slack app's Event Subscriptions "
          "Request URL and subscribe to the message.im bot event")


if __name__ == "__main__":
    main()
