#!/usr/bin/env python3
"""Assistant agent for the forsocialsss system.

Kimi K3 on the Fireworks serverless endpoint, talking to Firas over the
Slack bot DM. No command syntax: every message goes through a router that
decides whether Firas is asking a question, instructing a change, undoing
one, or explicitly requesting a pull request.

- answer: grounded reply from full system state, read-only.
- change: Kimi rewrites the target files completely, the assistant commits
  straight to main and reports the commit. The heartbeat pulls main every
  cycle, so changes take effect on its next fire.
- revert: the most recent assistant commit on main is reverted.
- pr: only when Firas explicitly asks for a pull request, the apply
  workflow packages the change for review instead of pushing.

Safety is structural, not ceremonial: path traversal is blocked, the hard
rules section of CLAUDE.md cannot be silently removed, and any edit that
would gut most of a file is held until Firas confirms.

Modes (argv[1]): chat (poller), apply (PR workflow).
Env: FIREWORKS_API_KEY, SLACK_BOT_TOKEN, GH_STATE_TOKEN (direct pushes),
     GITHUB_TOKEN (apply dispatch and PR creation), ANTHROPIC_API_KEY
     (optional, live status), FIREWORKS_MODEL, ASSISTANT_MAX_TOKENS.
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
ASSISTANT_AUTHOR = "assistant@forsocialsss"

HEARTBEAT_EXACT = {"approve", "hold", "status", "retro now"}
HEARTBEAT_PREFIX = ("edit:", "kill:", "posted ")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ROUTER_SYSTEM = """You are Firas Shaher's operations assistant for his autonomous LinkedIn content agent system. You are a separate model (Kimi K3) from the heartbeat agent that does the content work. You keep Firas informed and, when he instructs it, you change the system directly.

Voice: terse, grounded, direct. No em dashes ever. No hype, no exclamation points, no emoji unless he uses them first.

You will receive the current system state and Firas's message. Respond with ONLY a JSON object, no markdown fences, in one of these shapes:

1. He is asking a question, chatting, or his instruction is too ambiguous to execute safely:
{"mode": "answer", "reply": "<your grounded answer, or one clarifying question>"}

2. He is clearly instructing you to change the system (settings, strategy, weights, sources, playbook, prompts, drafts, any repo file):
{"mode": "change", "summary": "<one line describing the change>", "reply": "<one or two lines telling him what you changed>", "files": [{"path": "<repo-relative path>", "content": "<COMPLETE new file content>"}]}

3. He is asking to undo, revert, or roll back the last change you made:
{"mode": "revert", "reply": "<one line confirming the revert>"}

4. He explicitly asks for a pull request or says he wants to review before it lands:
{"mode": "pr", "reply": "<one line saying the PR is being prepared>"}

Any of the four shapes may additionally carry "remember": ["<one-line durable fact>"] when Firas states something worth keeping across conversations: a preference, a standing instruction, a decision, or context about why a setting is what it is. Be sparing; remember durable facts only, never small talk, never transient state the repo already tracks. These lines are appended to state/assistant-memory.md, which you receive in every future exchange.

Rules for change mode:
- Every file must contain its COMPLETE new content. Unchanged files are omitted.
- Touch the minimum set of files that fulfills the instruction.
- Respect the repository's own rules in CLAUDE.md: no em dashes anywhere, no fabricated data. The hard rules section of CLAUDE.md may only be edited when Firas explicitly names the hard rule he wants changed.
- Questions are never changes. "What would happen if" is a question. "Change it" is a change. When genuinely unsure, use answer mode and ask one short clarifying question.
- If he asks you to improve a queued LinkedIn draft, edit state/queue.json directly, keeping its schema, and note in your reply that the heartbeat's edit: directive is the alternative that reruns his full voice pipeline.

Ground every answer in the provided state. If the state does not contain the answer, say so plainly. Never reveal or speculate about credentials."""


# ---------------------------------------------------------------- plumbing

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
                                                       "16000")),
        "temperature": 0.3,
        "messages": [{"role": "system", "content": system}] + messages,
    }
    resp = http(FIREWORKS_URL, "POST", body,
                {"Authorization": f"Bearer {os.environ['FIREWORKS_API_KEY'].strip()}"})
    return resp["choices"][0]["message"]["content"]


def git(*args, check=True):
    r = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                       text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()[:400]}")
    return r.stdout.strip()


def push_main():
    token = os.environ.get("GH_STATE_TOKEN", "").strip()
    if not token:
        raise RuntimeError("GH_STATE_TOKEN missing; cannot push changes")
    remote = f"https://x-access-token:{token}@github.com/{REPO}.git"
    for attempt in (1, 2):
        r = subprocess.run(["git", "push", remote, "HEAD:main"],
                           cwd=REPO_ROOT, capture_output=True, text=True)
        if r.returncode == 0:
            return
        if attempt == 1:
            subprocess.run(["git", "pull", "--rebase", remote, "main"],
                           cwd=REPO_ROOT, capture_output=True, text=True)
    raise RuntimeError(f"push failed after rebase retry: {r.stderr.strip()[:300]}")


# ------------------------------------------------------------ read context

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
        ("Assistant memory (durable notes from Firas)",
         read_file("state/assistant-memory.md", 6000)),
        ("Constitution (CLAUDE.md)", read_file("CLAUDE.md", 20000)),
        ("Strategy", read_file("identity/strategy.md", 8000)),
        ("Voice rules", read_file("identity/voice.md", 8000)),
        ("Topic board", read_file("state/topics.json", 8000)),
        ("Watchlist", read_file("state/watchlist.json", 3000)),
        ("Draft queue", read_file("state/queue.json", 10000)),
        ("Posted history", read_file("state/posted.json", 3000)),
        ("Sources and budgets", read_file("sources/sources.md", 8000)),
        ("Run log, last 20 lines", tail_file("state/run-log.jsonl", 20)),
        ("Lessons, tail", tail_file("state/lessons.md", 60)),
        ("Recent commits", git("log", "--oneline", "-12")),
        ("Live deployment status", deployment_status()),
        ("Repository file listing", git("ls-files")),
    ]
    return "\n\n".join(f"## {title}\n{body}" for title, body in parts)


def is_heartbeat_directive(text):
    t = text.strip().lower()
    return t in HEARTBEAT_EXACT or any(t.startswith(p) for p in HEARTBEAT_PREFIX)


def dm_channel():
    try:
        return slack("conversations.open", {"users": FIRAS_ID})["channel"]["id"]
    except RuntimeError:
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


def recent_conversation(channel, thread_ts=None, limit=30):
    """Top-level DM history, merged with the active thread's replies when
    the message being answered lives inside one, chronological, capped by
    total size so long sessions do not blow the prompt up."""
    msgs = []
    try:
        resp = slack("conversations.history", {"channel": channel,
                                               "limit": limit})
        msgs.extend(resp.get("messages", []))
    except Exception:
        pass
    if thread_ts:
        try:
            resp = slack("conversations.replies", {"channel": channel,
                                                   "ts": thread_ts,
                                                   "limit": 30})
            msgs.extend(resp.get("messages", []))
        except Exception:
            pass
    seen, convo = set(), []
    for m in sorted(msgs, key=lambda m: float(m["ts"])):
        if m["ts"] in seen:
            continue
        seen.add(m["ts"])
        text = (m.get("text") or "").strip()
        if not text:
            continue
        role = "user" if m.get("user") == FIRAS_ID else "assistant"
        convo.append({"role": role, "content": text[:2000]})
    total = 0
    kept = []
    for m in reversed(convo):
        total += len(m["content"])
        if total > 24000:
            break
        kept.append(m)
    return list(reversed(kept))


# --------------------------------------------------------------- executing

def parse_plan(raw):
    raw = raw.strip()
    raw = re.sub(r"^```(json)?\s*|\s*```$", "", raw, flags=re.M).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # The model answered in prose; treat it as a plain answer.
        return {"mode": "answer", "reply": raw[:3000]}


def guard_change(plan, user_text):
    """Structural safety checks. Returns None when clear, or a message when
    the change is held for confirmation."""
    confirming = "confirm" in user_text.lower()
    for f in plan.get("files", []):
        path = os.path.normpath(f.get("path", ""))
        if path.startswith("..") or os.path.isabs(path):
            return f"That change touches an unsafe path ({f.get('path')}), refused."
        full = os.path.join(REPO_ROOT, path)
        new = f.get("content", "")
        if path == "CLAUDE.md" and "## Hard rules" not in new:
            return ("That edit would remove the hard rules section of "
                    "CLAUDE.md, refused. Name the specific hard rule you "
                    "want changed and I will edit just that.")
        if os.path.exists(full) and not confirming:
            old_size = os.path.getsize(full)
            if old_size > 2000 and len(new.encode()) < old_size * 0.3:
                return (f"That would shrink {path} by more than 70 percent, "
                        f"which usually means lost content. If that is "
                        f"really what you want, resend with the word "
                        f"confirm in the message.")
    return None


def execute_change(plan):
    for f in plan["files"]:
        path = os.path.normpath(f["path"])
        full = os.path.join(REPO_ROOT, path)
        os.makedirs(os.path.dirname(full) or REPO_ROOT, exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(f["content"])
        git("add", path)
    git("-c", "user.name=assistant", "-c", f"user.email={ASSISTANT_AUTHOR}",
        "commit", "-m", f"assistant: {plan.get('summary', 'change')}"[:120])
    push_main()
    sha = git("rev-parse", "--short", "HEAD")
    files = ", ".join(f["path"] for f in plan["files"])
    return (f"Done. {plan.get('summary', 'Changed')} ({files}).\n"
            f"Commit {sha}: https://github.com/{REPO}/commit/{sha}\n"
            f"The heartbeat picks this up on its next cycle. Say revert if "
            f"it is wrong.")


def execute_revert():
    log = git("log", "--format=%H %ae %s", "-20", "main")
    target = None
    for line in log.splitlines():
        sha, email, *msg = line.split(" ", 2)
        if email == ASSISTANT_AUTHOR and not " ".join(msg).startswith(
                "Revert"):
            target = (sha, " ".join(msg))
            break
    if not target:
        return "Nothing to revert: no recent assistant commit found on main."
    git("-c", "user.name=assistant", "-c", f"user.email={ASSISTANT_AUTHOR}",
        "revert", "--no-edit", target[0])
    push_main()
    sha = git("rev-parse", "--short", "HEAD")
    return (f"Reverted: {target[1]}\n"
            f"Commit {sha}: https://github.com/{REPO}/commit/{sha}")


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


def append_memory(lines):
    """Persist durable notes to state/assistant-memory.md as a commit."""
    import datetime
    path = os.path.join(REPO_ROOT, "state", "assistant-memory.md")
    today = datetime.date.today().isoformat()
    with open(path, "a", encoding="utf-8") as f:
        for line in lines:
            f.write(f"- {today}: {line.strip()}\n")
    git("add", "state/assistant-memory.md")
    git("-c", "user.name=assistant", "-c", f"user.email={ASSISTANT_AUTHOR}",
        "commit", "-m", "assistant: memory note")
    push_main()


def respond(text, channel, ts, thread_ts=None):
    """Route one message from Firas and act on it. Used by both the instant
    listener and the fallback poller."""
    convo = recent_conversation(channel, thread_ts)
    context = build_context()
    raw = kimi(ROUTER_SYSTEM, convo + [{
        "role": "user",
        "content": f"SYSTEM STATE SNAPSHOT (current):\n{context}\n\n"
                   f"FIRAS'S MESSAGE:\n{text}",
    }])
    plan = parse_plan(raw)
    mode = plan.get("mode", "answer")

    if mode == "change" and plan.get("files"):
        held = guard_change(plan, text)
        if held:
            reply = held
        else:
            try:
                reply = execute_change(plan)
            except Exception as e:
                reply = f"Change failed before landing: {str(e)[:400]}"
    elif mode == "revert":
        try:
            reply = execute_revert()
        except Exception as e:
            reply = f"Revert failed: {str(e)[:400]}"
    elif mode == "pr":
        dispatch_apply(text, channel)
        reply = plan.get("reply") or ("Preparing a pull request; the link "
                                      "lands here when it is open.")
    else:
        reply = plan.get("reply") or "I did not get a usable answer, try rephrasing."

    slack("chat.postMessage", {"channel": channel, "text": reply[:39000],
                               "thread_ts": thread_ts or ts})
    slack("reactions.add", {"channel": channel, "name": HANDLED_REACTION,
                            "timestamp": ts})
    remember = [x for x in (plan.get("remember") or []) if str(x).strip()]
    if remember:
        try:
            append_memory([str(x) for x in remember][:5])
        except Exception as e:
            print(f"respond: memory append failed: {e}")


# ------------------------------------------------------------------ modes

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
    # Thread replies never appear in conversations.history, so sweep the
    # threads of recent top-level messages for unhandled replies too.
    for m in history:
        if not m.get("reply_count"):
            continue
        if now - float(m.get("latest_reply", m["ts"])) > 86400:
            continue
        try:
            replies = slack("conversations.replies",
                            {"channel": channel, "ts": m["ts"],
                             "limit": 50}).get("messages", [])
        except Exception:
            continue
        for r in replies:
            if r.get("user") != FIRAS_ID or r.get("subtype"):
                continue
            if r["ts"] == m["ts"] or now - float(r["ts"]) > 86400:
                continue
            reactions = {x["name"] for x in r.get("reactions", [])}
            if HANDLED_REACTION in reactions:
                continue
            if is_heartbeat_directive(r.get("text", "")):
                continue
            r["_thread_ts"] = m["ts"]
            pending.append(r)
    if not pending:
        print("chat: nothing pending")
        return
    for msg in sorted(pending, key=lambda m: float(m["ts"])):
        try:
            respond(msg.get("text", "").strip(), channel, msg["ts"],
                    msg.get("_thread_ts"))
            print(f"chat: handled {msg['ts']}")
        except Exception as e:
            print(f"chat: error on {msg['ts']}: {e}")


APPLY_SYSTEM = """You are preparing a reviewable file change for Firas Shaher's LinkedIn content agent repository, at his explicit request for a pull request. You will be shown the repository file listing and the contents of relevant files.

Rules:
- Output ONLY a JSON object, no markdown fences: {"summary": "<one line>", "branch_hint": "<short-kebab-slug>", "files": [{"path": "<repo-relative path>", "content": "<complete new file content>"}]}
- Every file must contain its COMPLETE new content. Unchanged files are omitted.
- Respect CLAUDE.md: no em dashes anywhere, no fabricated data, hard rules may not be weakened.
- Touch the minimum set of files.
- If the instruction is unsafe or too ambiguous, return {"summary": "REFUSED: <reason>", "branch_hint": "refused", "files": []}"""


def apply_mode():
    instruction = os.environ.get("APPLY_INSTRUCTION", "").strip()
    channel = os.environ.get("APPLY_CHANNEL", "").strip() or dm_channel()
    if not instruction:
        print("apply: no instruction provided")
        sys.exit(1)

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
    plan = parse_plan(kimi(APPLY_SYSTEM,
                           [{"role": "user", "content": prompt}]))
    if plan.get("summary", "").startswith("REFUSED") or not plan.get("files"):
        slack("chat.postMessage", {
            "channel": channel,
            "text": f"Could not prepare that change. "
                    f"{plan.get('summary', 'No files produced.')}",
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
    git("-c", "user.name=assistant", "-c", f"user.email={ASSISTANT_AUTHOR}",
        "commit", "-m", f"assistant: {plan['summary']}"[:120])
    git("push", "origin", branch)

    token = os.environ["GITHUB_TOKEN"].strip()
    pr = http(
        f"{GITHUB_URL}/repos/{REPO}/pulls", "POST",
        {"title": f"assistant: {plan['summary']}"[:120],
         "head": branch, "base": "main",
         "body": f"Opened by the assistant agent at Firas's request:\n\n"
                 f"> {instruction}\n\n"
                 f"Files changed: {', '.join(f['path'] for f in plan['files'])}"},
        {"Authorization": f"Bearer {token}",
         "Accept": "application/vnd.github+json"},
    )
    slack("chat.postMessage", {
        "channel": channel,
        "text": f"Pull request ready for review: {pr['html_url']}\n"
                f"{plan['summary']}",
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
