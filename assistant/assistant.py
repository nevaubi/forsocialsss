#!/usr/bin/env python3
"""Assistant agent for the forsocialsss system.

A second, separate agent: Kimi K3 on the Fireworks serverless endpoint,
talking to Firas over the same Slack bot DM. Structurally read-only in chat
mode (the workflow grants contents: read), with a single explicit write path:
a message starting with "apply:" dispatches the apply workflow, which lets
Kimi propose complete file changes and opens a pull request for Firas to
merge. It never pushes to main.

Modes:
  chat    Poll the DM for unhandled messages, answer them with full read
          context (repo state, run log, deployment status), mark handled.
          Messages that are heartbeat directives are left alone for the
          heartbeat agent. "apply: ..." messages dispatch the apply workflow.
  apply   Take an instruction, have Kimi emit complete replacement files,
          push a branch, open a PR, and report back in Slack.

Env (chat):  FIREWORKS_API_KEY, SLACK_BOT_TOKEN, ANTHROPIC_API_KEY,
             GITHUB_TOKEN (actions: write, to dispatch apply)
Env (apply): FIREWORKS_API_KEY, SLACK_BOT_TOKEN, GITHUB_TOKEN
             (contents: write, pull-requests: write)
Optional:    FIREWORKS_MODEL (default accounts/fireworks/models/kimi-k3)
             ASSISTANT_MAX_TOKENS (default 2000)
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

FIREWORKS_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
SLACK_URL = "https://slack.com/api/"
ANTHROPIC_URL = "https://api.anthropic.com"
GITHUB_URL = "https://api.github.com"

FIRAS_ID = "U0BM0RF8AHM"
REPO = "nevaubi/forsocialsss"
HANDLED_REACTION = "robot_face"
DEPLOYMENT_NAME = "linkedin-heartbeat"

# Exact-match or prefix directives owned by the heartbeat agent. The
# assistant must never answer these; the heartbeat reads them each cycle.
HEARTBEAT_EXACT = {"approve", "hold", "status", "retro now"}
HEARTBEAT_PREFIX = ("edit:", "kill:", "posted ")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CHAT_SYSTEM = """You are Firas Shaher's operations assistant for his autonomous LinkedIn content agent system. You are a separate model (Kimi K3) from the heartbeat agent that does the content work; your job is to keep Firas informed and answer his questions.

Voice: terse, grounded, direct. No em dashes ever. No hype, no exclamation points, no emoji unless he uses them first. Answer the question asked; do not pad.

You have read access to the full system state, provided below: the agent's constitution, current topics, draft queue, run log, lessons, recent commits, and the live deployment status. Ground every answer in that data. If the data does not contain the answer, say so plainly instead of guessing.

You are read-only. You cannot change files, trigger runs, or post anything. If Firas asks you to change something, tell him to send the same request prefixed with "apply:" and you will open a pull request for his review. If he asks about heartbeat directives (approve, edit:, kill:, hold, status, posted, retro now), remind him those go to the heartbeat agent in this same DM and are picked up on its next cycle.

Never reveal, print, or speculate about credentials or tokens."""

APPLY_SYSTEM = """You are preparing a file change for Firas Shaher's LinkedIn content agent repository, following his explicit instruction. You will be shown the repository file listing and the contents of relevant files.

Rules:
- Output ONLY a JSON object, no markdown fences, no commentary, with this exact shape: {"summary": "<one line describing the change>", "branch_hint": "<short-kebab-slug>", "files": [{"path": "<repo-relative path>", "content": "<complete new file content>"}]}
- Every file you include must contain its COMPLETE new content, not a diff or fragment. Unchanged files are omitted entirely.
- Respect the repository's own rules in CLAUDE.md: no em dashes anywhere, no fabricated data, and the hard rules section of CLAUDE.md may not be weakened.
- Touch the minimum set of files that fulfills the instruction.
- If the instruction is unsafe, contradicts CLAUDE.md hard rules, or is too ambiguous to execute, return {"summary": "REFUSED: <reason>", "branch_hint": "refused", "files": []}"""


def http(url, method="GET", body=None, headers=None, form=False):
    if form and body is not None:
        data = urllib.parse.urlencode(body).encode()
    elif body is not None:
        data = json.dumps(body).encode()
    else:
        data = None
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    if data is not None and not form:
        req.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"{method} {url} -> HTTP {e.code}: {detail[:500]}")


def slack(method, body):
    token = os.environ["SLACK_BOT_TOKEN"].strip()
    resp = http(SLACK_URL + method, "POST", body,
                {"Authorization": f"Bearer {token}"}, form=True)
    if not resp.get("ok"):
        raise RuntimeError(f"slack {method}: {resp.get('error')}")
    return resp


def kimi(system, messages, max_tokens=None):
    body = {
        "model": os.environ.get("FIREWORKS_MODEL",
                                "accounts/fireworks/models/kimi-k3"),
        "max_tokens": max_tokens or int(os.environ.get("ASSISTANT_MAX_TOKENS",
                                                       "2000")),
        "temperature": 0.4,
        "messages": [{"role": "system", "content": system}] + messages,
    }
    resp = http(FIREWORKS_URL, "POST", body,
                {"Authorization": f"Bearer {os.environ['FIREWORKS_API_KEY'].strip()}"})
    return resp["choices"][0]["message"]["content"]


def read_file(rel, max_chars=6000):
    path = os.path.join(REPO_ROOT, rel)
    if not os.path.exists(path):
        return f"(missing: {rel})"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    if len(text) > max_chars:
        return text[:max_chars] + f"\n...(truncated, {len(text)} chars total)"
    return text


def tail_file(rel, lines):
    text = read_file(rel, max_chars=200000)
    return "\n".join(text.splitlines()[-lines:])


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()


def deployment_status():
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return "(deployment status unavailable: no API key)"
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01",
               "anthropic-beta": "managed-agents-2026-04-01"}
    try:
        deps = http(ANTHROPIC_URL + "/v1/deployments?limit=100",
                    headers=headers).get("data", [])
        dep = next((d for d in deps if d.get("name") == DEPLOYMENT_NAME), None)
        if not dep:
            return "(deployment not found)"
        out = {
            "status": dep.get("status"),
            "schedule": (dep.get("schedule") or {}).get("expression"),
            "timezone": (dep.get("schedule") or {}).get("timezone"),
            "upcoming_runs": ((dep.get("schedule") or {})
                              .get("upcoming_runs_at") or [])[:2],
        }
        runs = http(
            ANTHROPIC_URL + f"/v1/deployment_runs?deployment_id={dep['id']}&limit=5",
            headers=headers).get("data", [])
        out["recent_runs"] = [
            {"at": r.get("created_at"),
             "error": (r.get("error") or {}).get("type")}
            for r in runs
        ]
        return json.dumps(out, indent=1)
    except Exception as e:
        return f"(deployment status error: {e})"


def build_context():
    parts = [
        ("Constitution (CLAUDE.md)", read_file("CLAUDE.md", 5000)),
        ("Strategy", read_file("identity/strategy.md", 3000)),
        ("Topic board", read_file("state/topics.json", 4000)),
        ("Watchlist", read_file("state/watchlist.json", 2000)),
        ("Draft queue", read_file("state/queue.json", 4000)),
        ("Posted history", read_file("state/posted.json", 2000)),
        ("Run log, last 15 lines", tail_file("state/run-log.jsonl", 15)),
        ("Lessons, tail", tail_file("state/lessons.md", 40)),
        ("Recent commits", git("log", "--oneline", "-10")),
        ("Live deployment status", deployment_status()),
    ]
    return "\n\n".join(f"## {title}\n{body}" for title, body in parts)


def is_heartbeat_directive(text):
    t = text.strip().lower()
    return t in HEARTBEAT_EXACT or any(t.startswith(p) for p in HEARTBEAT_PREFIX)


def dm_channel():
    try:
        return slack("conversations.open", {"users": FIRAS_ID})["channel"]["id"]
    except RuntimeError:
        # Fallback for tokens without im:write: find the existing DM.
        cursor = None
        while True:
            body = {"types": "im", "limit": 200}
            if cursor:
                body["cursor"] = cursor
            resp = slack("users.conversations", body)
            for ch in resp.get("channels", []):
                if ch.get("user") == FIRAS_ID:
                    return ch["id"]
            cursor = (resp.get("response_metadata") or {}).get("next_cursor")
            if not cursor:
                break
        raise RuntimeError(
            "could not resolve the DM channel; the Slack app needs scopes "
            "im:write and im:read (see README scope list)")


def chat():
    channel = dm_channel()
    history = slack("conversations.history",
                    {"channel": channel, "limit": 40})["messages"]
    now = time.time()
    pending = []
    for m in history:
        if m.get("user") != FIRAS_ID or m.get("subtype"):
            continue
        if now - float(m["ts"]) > 86400:
            continue
        reactions = {r["name"] for r in m.get("reactions", [])}
        if HANDLED_REACTION in reactions:
            continue
        if is_heartbeat_directive(m.get("text", "")):
            continue
        pending.append(m)
    if not pending:
        print("chat: nothing pending")
        return
    pending.sort(key=lambda m: float(m["ts"]))

    # Conversation memory: the last 12 messages of the DM, oldest first,
    # mapped to chat roles so Kimi keeps thread continuity.
    convo = []
    for m in sorted(history, key=lambda m: float(m["ts"]))[-12:]:
        text = (m.get("text") or "").strip()
        if not text:
            continue
        role = "user" if m.get("user") == FIRAS_ID else "assistant"
        convo.append({"role": role, "content": text[:2000]})

    for msg in pending:
        text = msg.get("text", "").strip()
        if text.lower().startswith("apply:"):
            instruction = text[len("apply:"):].strip()
            dispatch_apply(instruction, channel)
            slack("chat.postMessage", {
                "channel": channel,
                "text": "On it. Preparing a pull request for that change; "
                        "link lands here when it is open.",
                "thread_ts": msg["ts"],
            })
        else:
            context = build_context()
            messages = convo + [{
                "role": "user",
                "content": f"SYSTEM STATE SNAPSHOT (current):\n{context}\n\n"
                           f"FIRAS'S MESSAGE:\n{text}",
            }]
            reply = kimi(CHAT_SYSTEM, messages).strip()
            slack("chat.postMessage",
                  {"channel": channel, "text": reply[:39000],
                   "thread_ts": msg["ts"]})
        slack("reactions.add", {"channel": channel, "name": HANDLED_REACTION,
                                "timestamp": msg["ts"]})
        print(f"chat: handled message {msg['ts']}")


def dispatch_apply(instruction, channel):
    token = os.environ["GITHUB_TOKEN"].strip()
    http(
        f"{GITHUB_URL}/repos/{REPO}/actions/workflows/assistant-apply.yml/dispatches",
        "POST",
        {"ref": "main",
         "inputs": {"instruction": instruction[:1000], "channel": channel}},
        {"Authorization": f"Bearer {token}",
         "Accept": "application/vnd.github+json"},
    )


def apply_mode():
    instruction = os.environ.get("APPLY_INSTRUCTION", "").strip()
    channel = os.environ.get("APPLY_CHANNEL", "").strip()
    if not instruction:
        print("apply: no instruction provided")
        sys.exit(1)
    if not channel:
        channel = dm_channel()

    listing = git("ls-files")
    relevant = []
    for rel in listing.splitlines():
        if rel.startswith((".github/", "deploy/", "assistant/")):
            continue
        relevant.append(f"### {rel}\n{read_file(rel, 8000)}")
    prompt = (
        f"REPOSITORY FILE LISTING:\n{listing}\n\n"
        f"FILE CONTENTS:\n\n" + "\n\n".join(relevant) +
        f"\n\nINSTRUCTION FROM FIRAS:\n{instruction}"
    )
    raw = kimi(APPLY_SYSTEM, [{"role": "user", "content": prompt}],
               max_tokens=16000).strip()
    raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.M).strip()
    plan = json.loads(raw)

    if plan.get("summary", "").startswith("REFUSED") or not plan.get("files"):
        slack("chat.postMessage", {
            "channel": channel,
            "text": f"Could not prepare that change. {plan.get('summary', 'No files produced.')}",
        })
        return

    slug = re.sub(r"[^a-z0-9-]", "", plan.get("branch_hint", "change")
                  .lower().replace(" ", "-"))[:40] or "change"
    branch = f"assistant/{int(time.time())}-{slug}"
    git("checkout", "-b", branch)
    for f in plan["files"]:
        path = os.path.normpath(f["path"])
        if path.startswith("..") or os.path.isabs(path):
            raise RuntimeError(f"unsafe path in plan: {f['path']}")
        full = os.path.join(REPO_ROOT, path)
        os.makedirs(os.path.dirname(full) or REPO_ROOT, exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(f["content"])
        git("add", path)
    git("-c", "user.name=assistant", "-c", "user.email=assistant@forsocialsss",
        "commit", "-m", f"assistant: {plan['summary']}"[:120])
    git("push", "origin", branch)

    token = os.environ["GITHUB_TOKEN"].strip()
    pr = http(
        f"{GITHUB_URL}/repos/{REPO}/pulls", "POST",
        {"title": f"assistant: {plan['summary']}"[:120],
         "head": branch, "base": "main",
         "body": f"Opened by the assistant agent on Firas's explicit "
                 f"instruction:\n\n> {instruction}\n\n"
                 f"Files changed: {', '.join(f['path'] for f in plan['files'])}"},
        {"Authorization": f"Bearer {token}",
         "Accept": "application/vnd.github+json"},
    )
    slack("chat.postMessage", {
        "channel": channel,
        "text": f"Pull request ready for review: {pr['html_url']}\n"
                f"{plan['summary']}\nMerging it applies the change; the "
                f"heartbeat picks it up automatically on its next cycle.",
    })
    print(f"apply: opened {pr['html_url']}")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "chat"
    if mode == "chat":
        chat()
    elif mode == "apply":
        apply_mode()
    else:
        print(f"unknown mode {mode!r}")
        sys.exit(1)


if __name__ == "__main__":
    main()
