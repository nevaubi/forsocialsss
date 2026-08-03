#!/usr/bin/env python3
"""Assistant agent for the forsocialsss system.

Kimi K3 on Fireworks, running a real agent loop over the repository. No
command syntax: Firas talks in plain language and the agent decides whether
to answer, research, or act. For actions it works like an engineer: read the
file, make an exact-match edit, verify, review the diff, commit, report the
commit link. Web research runs through Tavily and direct fetches.

Structural safety lives in the tools, not the prompt: path traversal is
blocked, the hard rules section of CLAUDE.md cannot be removed, em dashes
cannot be committed, edits that gut a file are held until Firas confirms,
and the shell tool runs with all credentials scrubbed from its environment.

Modes (argv[1]): chat (fallback poller), apply (PR workflow).
Env: FIREWORKS_API_KEY, SLACK_BOT_TOKEN, GH_STATE_TOKEN, GITHUB_TOKEN,
     TAVILY_API_KEY (web research), ANTHROPIC_API_KEY (live status),
     FIREWORKS_MODEL, ASSISTANT_MAX_TOKENS.
"""

import datetime
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
MAX_LOOP = 30

HEARTBEAT_EXACT = {"approve", "hold", "status", "retro now"}
HEARTBEAT_PREFIX = ("edit:", "kill:", "posted ")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AGENT_SYSTEM = """You are Firas Shaher's operations agent for his autonomous LinkedIn content system. You are a separate model (Kimi K3) from the heartbeat agent that does the content work. You keep Firas informed and, when he instructs it, you change the system yourself using your tools.

Voice: terse, grounded, direct. No em dashes ever, anywhere, including in files you write. No hype, no exclamation points, no emoji unless he uses them first.

Deciding what to do:
- Questions get answers, grounded in the state snapshot and whatever you read or research. Questions are never actions. "What would happen if" is a question.
- Clear instructions to change the system get executed. When an instruction is too ambiguous to execute safely, ask one short clarifying question instead of guessing.
- "Revert" or "undo" means revert_last.
- Only when he explicitly asks for a pull request, use request_pr instead of committing directly.
- Heartbeat draft directives (approve, edit:, kill:, hold, status, posted, retro now) are not yours; if he seems to want the heartbeat, say so.

How to make changes, in order:
1. read_file everything you are about to touch. Never edit from memory of the snapshot.
2. Prefer edit_file with an exact unique match for existing files; write_file only for new files or genuine full rewrites.
3. Verify: after editing Python run "python3 -m py_compile <file>", after YAML run a python yaml.safe_load check, with the run tool.
4. git_diff and read it critically. If the diff is not exactly what the instruction asked, fix it before committing.
5. commit_and_push with message "assistant: <what changed>". The tool enforces safety guards and returns the commit link.
6. Your final reply states what changed, the commit link, and that the heartbeat picks it up next cycle. If you changed deploy config or the heartbeat model or schedule, note that it needs a Deploy Agent workflow run with recreate=true to take effect.

Research: web_search for current information, fetch_url to read a specific page. Use them whenever the answer depends on anything outside this repository or your training data, and say what you found rather than guessing.

Documents and visuals: when Firas asks for a PDF report, slide deck, infographic, chart, or image, FIRST read the matching recipe in assistant-skills/ (pdf-report.md, slide-deck.md, infographic.md) and follow its pipeline and quality checklist exactly. Build files under assistant-outputs/ with the run tool. generate_image (FLUX on Fireworks) is for photographic or illustrative art; charts, layouts, and data graphics are built deterministically with matplotlib and PIL, which you can control precisely. You have native vision: after building, ALWAYS view_render the artifact and critique what you actually see against the recipe checklist (overflow, contrast, alignment, hierarchy, palette, thumbnail legibility), fix the build script, re-render, and repeat until it passes or two fix rounds are done. Only then deliver_file. If a recipe repeatedly fails you, improve the recipe file itself and commit it.

Memory: when Firas states a durable preference, standing instruction, or decision, call remember with a one-line note. Sparingly, durable facts only.

Never print, request, or attempt to read credentials; your shell runs with them scrubbed. When anything fails, say exactly what failed rather than papering over it. When repository instructions and convenience conflict, the repository wins."""


# ---------------------------------------------------------------- plumbing

def http(url, method="GET", body=None, headers=None, form=False, timeout=120):
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
        with urllib.request.urlopen(req, timeout=timeout) as resp:
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


def sync_to_main():
    """Reset the working tree to current origin/main so every exchange
    starts from the latest pushed state, discarding any leftovers."""
    try:
        git("fetch", "origin", "main")
        git("reset", "--hard", "FETCH_HEAD")
        git("clean", "-fd")
    except Exception as e:
        print(f"sync: {e}")


def safe_path(rel):
    path = os.path.normpath(rel).replace("\\", "/")
    if path.startswith("..") or os.path.isabs(path) or path.startswith(".git/"):
        raise RuntimeError(f"unsafe path: {rel}")
    return path


# ------------------------------------------------------------ read context

def read_repo(rel, max_chars=6000):
    path = os.path.join(REPO_ROOT, rel)
    if not os.path.exists(path):
        return f"(missing: {rel})"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    if len(text) > max_chars:
        return text[:max_chars] + f"\n...(truncated, {len(text)} chars total; read_file for the rest)"
    return text


def tail_repo(rel, lines):
    text = read_repo(rel, max_chars=400000)
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


def build_snapshot():
    parts = [
        ("Assistant memory (durable notes from Firas)",
         read_repo("state/assistant-memory.md", 6000)),
        ("Constitution (CLAUDE.md)", read_repo("CLAUDE.md", 14000)),
        ("Topic board", read_repo("state/topics.json", 4000)),
        ("Watchlist", read_repo("state/watchlist.json", 1500)),
        ("Draft queue", read_repo("state/queue.json", 6000)),
        ("Posted history", read_repo("state/posted.json", 1500)),
        ("Run log, last 15 lines", tail_repo("state/run-log.jsonl", 15)),
        ("Lessons, tail", tail_repo("state/lessons.md", 30)),
        ("Recent commits", git("log", "--oneline", "-12")),
        ("Live deployment status", deployment_status()),
        ("Repository file listing (read_file for any of these)",
         git("ls-files")),
    ]
    return "\n\n".join(f"## {t}\n{b}" for t, b in parts)


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
    total, kept = 0, []
    for m in reversed(convo):
        total += len(m["content"])
        if total > 24000:
            break
        kept.append(m)
    return list(reversed(kept))


# ------------------------------------------------------------------- tools

TOOLS = [
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a repository file in full.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "repo-relative path"}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "list_files",
        "description": "List all tracked files in the repository.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "edit_file",
        "description": "Replace one exact occurrence of old_str with new_str "
                       "in a file. old_str must match exactly once; include "
                       "enough surrounding context to make it unique.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "old_str": {"type": "string"},
            "new_str": {"type": "string"}},
            "required": ["path", "old_str", "new_str"]}}},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Create a new file or fully overwrite an existing one "
                       "with complete content. Prefer edit_file for edits.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"}},
            "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "run",
        "description": "Run a shell command in the repository root, 120s "
                       "timeout, credentials scrubbed from the environment. "
                       "For verification: py_compile, yaml checks, grep, git "
                       "log. Not for pushing; use commit_and_push.",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"}},
            "required": ["command"]}}},
    {"type": "function", "function": {
        "name": "git_diff",
        "description": "Show uncommitted changes: status plus full diff. "
                       "Review before every commit.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "commit_and_push",
        "description": "Commit all working tree changes as the assistant and "
                       "push straight to main. Returns the commit link. "
                       "Safety guards may hold the commit and tell you why.",
        "parameters": {"type": "object", "properties": {
            "message": {"type": "string",
                        "description": "commit message, no assistant: prefix "
                                       "needed, it is added"}},
            "required": ["message"]}}},
    {"type": "function", "function": {
        "name": "revert_last",
        "description": "Revert the most recent assistant commit on main.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "web_search",
        "description": "Search the web (Tavily). Returns an answer synthesis "
                       "and the top results with snippets.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}},
            "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "fetch_url",
        "description": "Fetch a URL and return its text content, tags "
                       "stripped, capped.",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string"}},
            "required": ["url"]}}},
    {"type": "function", "function": {
        "name": "remember",
        "description": "Persist a one-line durable note from Firas to "
                       "state/assistant-memory.md.",
        "parameters": {"type": "object", "properties": {
            "note": {"type": "string"}},
            "required": ["note"]}}},
    {"type": "function", "function": {
        "name": "generate_image",
        "description": "Generate an image with FLUX on Fireworks and save "
                       "it under assistant-outputs/. For photographic or "
                       "illustrative art only; build charts and layouts "
                       "with matplotlib or PIL via run instead.",
        "parameters": {"type": "object", "properties": {
            "prompt": {"type": "string"},
            "filename": {"type": "string",
                         "description": "output name, .jpg, no directories"},
            "aspect_ratio": {"type": "string",
                             "description": "one of 1:1 16:9 9:16 4:5 3:2 "
                                            "2:3, default 1:1"}},
            "required": ["prompt", "filename"]}}},
    {"type": "function", "function": {
        "name": "view_render",
        "description": "Render a file to images and attach them to the "
                       "conversation so you can visually inspect your own "
                       "output. Supports png/jpg directly, pdf (page "
                       "renders), and pptx (converted then rendered). Use "
                       "after every build, before delivering.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "pages": {"type": "integer",
                      "description": "max pages/slides to render, default 4"}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "deliver_file",
        "description": "Upload a finished file from the workspace to Firas "
                       "in this Slack conversation. Use after the quality "
                       "checklist passes.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string",
                     "description": "workspace-relative path, e.g. "
                                    "assistant-outputs/report.pdf"},
            "title": {"type": "string"}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "request_pr",
        "description": "Only when Firas explicitly asks for a pull request: "
                       "dispatch the reviewed-change workflow instead of "
                       "committing directly.",
        "parameters": {"type": "object", "properties": {
            "instruction": {"type": "string"}},
            "required": ["instruction"]}}},
]


def tool_read_file(args, ctx):
    path = safe_path(args["path"])
    full = os.path.join(REPO_ROOT, path)
    if not os.path.exists(full):
        return f"error: {path} does not exist"
    with open(full, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    if len(text) > 60000:
        return text[:60000] + f"\n...(truncated at 60000 of {len(text)} chars)"
    return text


def tool_list_files(args, ctx):
    return git("ls-files")


def tool_edit_file(args, ctx):
    path = safe_path(args["path"])
    full = os.path.join(REPO_ROOT, path)
    if not os.path.exists(full):
        return f"error: {path} does not exist; use write_file to create it"
    with open(full, "r", encoding="utf-8") as f:
        text = f.read()
    count = text.count(args["old_str"])
    if count == 0:
        return "error: old_str not found; read_file again and match exactly"
    if count > 1:
        return f"error: old_str matches {count} times; add surrounding context"
    with open(full, "w", encoding="utf-8") as f:
        f.write(text.replace(args["old_str"], args["new_str"], 1))
    return f"edited {path}"


def tool_write_file(args, ctx):
    path = safe_path(args["path"])
    full = os.path.join(REPO_ROOT, path)
    os.makedirs(os.path.dirname(full) or REPO_ROOT, exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(args["content"])
    return f"wrote {path} ({len(args['content'])} chars)"


SCRUB = ("TOKEN", "KEY", "SECRET", "PASSWORD", "CREDENTIAL")


def tool_run(args, ctx):
    env = {k: v for k, v in os.environ.items()
           if not any(s in k.upper() for s in SCRUB)}
    env["HOME"] = os.environ.get("HOME", "/tmp")
    try:
        r = subprocess.run(["bash", "-c", args["command"]], cwd=REPO_ROOT,
                           capture_output=True, text=True, timeout=120,
                           env=env)
        out = (r.stdout + ("\n" + r.stderr if r.stderr else "")).strip()
        return f"exit {r.returncode}\n{out[:8000]}"
    except subprocess.TimeoutExpired:
        return "error: command timed out at 120s"


def tool_git_diff(args, ctx):
    status = git("status", "--short")
    diff = git("diff")
    out = f"STATUS:\n{status or '(clean)'}\n\nDIFF:\n{diff or '(no changes)'}"
    return out[:20000]


def tool_commit_and_push(args, ctx):
    changed = [p for p in git("status", "--porcelain").splitlines()]
    if not changed:
        return "error: nothing to commit"
    confirming = "confirm" in ctx["user_text"].lower()
    for line in changed:
        path = line[3:].strip().strip('"')
        full = os.path.join(REPO_ROOT, path)
        if not os.path.isfile(full):
            continue
        with open(full, "r", encoding="utf-8", errors="replace") as f:
            new = f.read()
        if "\u2014" in json.dumps(new):
            return (f"held: {path} contains an em dash, which CLAUDE.md bans "
                    f"repo-wide. Replace it and commit again.")
        if path == "CLAUDE.md" and "## Hard rules" not in new:
            return ("held: this would remove the hard rules section of "
                    "CLAUDE.md. Refused; edit the specific rule instead.")
        try:
            old = git("show", f"HEAD:{path}", check=True)
        except RuntimeError:
            old = None
        if (old is not None and not confirming and len(old) > 2000
                and len(new) < len(old) * 0.3):
            return (f"held: this shrinks {path} by more than 70 percent, "
                    f"which usually means lost content. Tell Firas; he can "
                    f"resend with the word confirm to proceed.")
    git("add", "-A")
    msg = args["message"].strip()
    if not msg.startswith("assistant:"):
        msg = f"assistant: {msg}"
    git("-c", "user.name=assistant", "-c", f"user.email={ASSISTANT_AUTHOR}",
        "commit", "-m", msg[:140])
    push_main()
    sha = git("rev-parse", "--short", "HEAD")
    ctx["committed"] = sha
    return f"committed and pushed {sha}: https://github.com/{REPO}/commit/{sha}"


def tool_revert_last(args, ctx):
    log = git("log", "--format=%H %ae %s", "-20", "HEAD")
    target = None
    for line in log.splitlines():
        sha, email, *msg = line.split(" ", 2)
        m = " ".join(msg)
        if email == ASSISTANT_AUTHOR and not m.startswith("Revert"):
            target = (sha, m)
            break
    if not target:
        return "error: no recent assistant commit found to revert"
    git("-c", "user.name=assistant", "-c", f"user.email={ASSISTANT_AUTHOR}",
        "revert", "--no-edit", target[0])
    push_main()
    sha = git("rev-parse", "--short", "HEAD")
    return (f"reverted '{target[1]}' in {sha}: "
            f"https://github.com/{REPO}/commit/{sha}")


def tool_web_search(args, ctx):
    key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not key:
        return "error: TAVILY_API_KEY not available in this runtime"
    resp = http("https://api.tavily.com/search", "POST", {
        "api_key": key, "query": args["query"], "max_results": 5,
        "include_answer": True,
    })
    out = [f"answer: {resp.get('answer', '(none)')}"]
    for r in resp.get("results", []):
        out.append(f"- {r.get('title')} | {r.get('url')}\n  {str(r.get('content'))[:500]}")
    return "\n".join(out)[:10000]


def tool_fetch_url(args, ctx):
    req = urllib.request.Request(args["url"], headers={
        "User-Agent": "Mozilla/5.0 (forsocialsss-assistant)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read(600000).decode(errors="replace")
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw,
                  flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text[:12000]


def tool_remember(args, ctx):
    path = os.path.join(REPO_ROOT, "state", "assistant-memory.md")
    today = datetime.date.today().isoformat()
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"- {today}: {args['note'].strip()}\n")
    git("add", "state/assistant-memory.md")
    git("-c", "user.name=assistant", "-c", f"user.email={ASSISTANT_AUTHOR}",
        "commit", "-m", "assistant: memory note")
    push_main()
    return "remembered"


IMAGE_SIZES = {"1:1": (1024, 1024), "16:9": (1344, 768), "9:16": (768, 1344),
               "4:5": (896, 1152), "3:2": (1216, 832), "2:3": (832, 1216)}


def tool_generate_image(args, ctx):
    key = os.environ.get("FIREWORKS_API_KEY", "").strip()
    if not key:
        return "error: FIREWORKS_API_KEY not available"
    name = os.path.basename(args["filename"]) or "image.jpg"
    if not name.lower().endswith((".jpg", ".jpeg", ".png")):
        name += ".jpg"
    model = os.environ.get("IMAGE_MODEL", "flux-1-schnell-fp8")
    w, h = IMAGE_SIZES.get(args.get("aspect_ratio", "1:1"), (1024, 1024))
    body = json.dumps({"prompt": args["prompt"], "width": w, "height": h}).encode()
    last_err = None
    for path in (
        f"https://api.fireworks.ai/inference/v1/workflows/accounts/fireworks/models/{model}/text_to_image",
        f"https://api.fireworks.ai/inference/v1/image_generation/accounts/fireworks/models/{model}",
    ):
        req = urllib.request.Request(path, data=body, method="POST")
        req.add_header("Authorization", f"Bearer {key}")
        req.add_header("content-type", "application/json")
        req.add_header("accept", "image/jpeg")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            outdir = os.path.join(REPO_ROOT, "assistant-outputs")
            os.makedirs(outdir, exist_ok=True)
            out = os.path.join(outdir, name)
            with open(out, "wb") as f:
                f.write(data)
            return (f"generated assistant-outputs/{name} "
                    f"({len(data)} bytes, {w}x{h})")
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}"
        except Exception as e:
            last_err = str(e)[:300]
    return f"error: image generation failed: {last_err}"


def _render_to_pngs(full, pages):
    """Return a list of PNG file paths rendering the artifact."""
    import shutil
    outdir = os.path.join(REPO_ROOT, "assistant-outputs", ".render")
    os.makedirs(outdir, exist_ok=True)
    for f in os.listdir(outdir):
        os.remove(os.path.join(outdir, f))
    ext = os.path.splitext(full)[1].lower()
    if ext in (".png", ".jpg", ".jpeg"):
        return [full]
    pdf = full
    if ext == ".pptx":
        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        if not soffice:
            raise RuntimeError("libreoffice not available to render pptx; "
                               "deliver the file and ask Firas to review")
        subprocess.run([soffice, "--headless", "--convert-to", "pdf",
                        "--outdir", outdir, full], timeout=180,
                       capture_output=True)
        pdf = os.path.join(outdir, os.path.splitext(
            os.path.basename(full))[0] + ".pdf")
        if not os.path.exists(pdf):
            raise RuntimeError("pptx to pdf conversion produced no output")
    if not pdf.lower().endswith(".pdf"):
        raise RuntimeError(f"cannot render {ext} files")
    if not shutil.which("pdftoppm"):
        subprocess.run(["sudo", "apt-get", "install", "-y", "-qq",
                        "poppler-utils"], timeout=120, capture_output=True)
    subprocess.run(["pdftoppm", "-png", "-r", "110", "-f", "1",
                    "-l", str(pages), pdf,
                    os.path.join(outdir, "page")], timeout=120,
                   capture_output=True)
    outs = sorted(os.path.join(outdir, f) for f in os.listdir(outdir)
                  if f.startswith("page") and f.endswith(".png"))
    if not outs:
        raise RuntimeError("rendering produced no pages")
    return outs


def tool_view_render(args, ctx):
    import base64
    path = safe_path(args["path"])
    full = os.path.join(REPO_ROOT, path)
    if not os.path.isfile(full):
        return f"error: {path} does not exist"
    pages = min(int(args.get("pages") or 4), 6)
    pngs = _render_to_pngs(full, pages)
    try:
        from PIL import Image
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                        "pillow"], timeout=120, capture_output=True)
        from PIL import Image
    encoded = []
    for p in pngs[:pages]:
        img = Image.open(p).convert("RGB")
        if img.width > 1280:
            img = img.resize((1280, int(img.height * 1280 / img.width)))
        tmp = p + ".jpg"
        img.save(tmp, "JPEG", quality=80)
        with open(tmp, "rb") as f:
            encoded.append(base64.b64encode(f.read()).decode())
    ctx["pending_images"] = encoded
    ctx["pending_images_label"] = path
    return (f"rendered {len(encoded)} page(s) of {path}; the images follow "
            f"in the next message. Critique them against the recipe "
            f"checklist before deciding they are done.")


def tool_deliver_file(args, ctx):
    path = safe_path(args["path"])
    full = os.path.join(REPO_ROOT, path)
    if not os.path.isfile(full):
        return f"error: {path} does not exist"
    size = os.path.getsize(full)
    if size > 90 * 1024 * 1024:
        return "error: file exceeds Slack's 90MB limit"
    name = os.path.basename(full)
    up = slack("files.getUploadURLExternal",
               {"filename": name, "length": size})
    with open(full, "rb") as f:
        data = f.read()
    req = urllib.request.Request(up["upload_url"], data=data, method="POST")
    req.add_header("content-type", "application/octet-stream")
    with urllib.request.urlopen(req, timeout=180) as resp:
        resp.read()
    slack("files.completeUploadExternal", {
        "files": json.dumps([{"id": up["file_id"],
                              "title": args.get("title", name)}]),
        "channel_id": ctx["channel"],
    })
    return f"delivered {name} ({size} bytes) to the conversation"


def tool_request_pr(args, ctx):
    token = os.environ["GITHUB_TOKEN"].strip()
    http(
        f"{GITHUB_URL}/repos/{REPO}/actions/workflows/assistant-apply.yml/dispatches",
        "POST",
        {"ref": "main",
         "inputs": {"instruction": args["instruction"][:1000],
                    "channel": ctx["channel"]}},
        {"Authorization": f"Bearer {token}",
         "Accept": "application/vnd.github+json"},
    )
    return "PR workflow dispatched; the link will arrive in Slack when open"


TOOL_IMPL = {
    "read_file": tool_read_file,
    "list_files": tool_list_files,
    "edit_file": tool_edit_file,
    "write_file": tool_write_file,
    "run": tool_run,
    "git_diff": tool_git_diff,
    "commit_and_push": tool_commit_and_push,
    "revert_last": tool_revert_last,
    "web_search": tool_web_search,
    "fetch_url": tool_fetch_url,
    "remember": tool_remember,
    "request_pr": tool_request_pr,
    "generate_image": tool_generate_image,
    "deliver_file": tool_deliver_file,
    "view_render": tool_view_render,
}


def kimi_call(messages, tools=None, max_tokens=None):
    body = {
        "model": os.environ.get("FIREWORKS_MODEL",
                                "accounts/fireworks/models/kimi-k3"),
        "max_tokens": max_tokens or int(os.environ.get("ASSISTANT_MAX_TOKENS",
                                                       "16000")),
        "temperature": 0.3,
        "messages": messages,
    }
    if tools:
        body["tools"] = tools
    resp = http(FIREWORKS_URL, "POST", body,
                {"Authorization": f"Bearer {os.environ['FIREWORKS_API_KEY'].strip()}"})
    return resp["choices"][0]["message"]


def respond(text, channel, ts, thread_ts=None):
    """Run the agent loop for one message from Firas. Used by both the
    instant listener and the fallback poller."""
    sync_to_main()
    convo = recent_conversation(channel, thread_ts)
    snapshot = build_snapshot()
    messages = [{"role": "system", "content": AGENT_SYSTEM}]
    messages += convo
    messages.append({
        "role": "user",
        "content": f"SYSTEM STATE SNAPSHOT (current, {datetime.datetime.now().isoformat()}):\n"
                   f"{snapshot}\n\nFIRAS'S MESSAGE:\n{text}",
    })
    ctx = {"user_text": text, "channel": channel, "committed": None}
    reply = None
    for _ in range(MAX_LOOP):
        msg = kimi_call(messages, tools=TOOLS)
        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            reply = (msg.get("content") or "").strip()
            break
        messages.append({"role": "assistant",
                         "content": msg.get("content") or "",
                         "tool_calls": tool_calls})
        for tc in tool_calls:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            impl = TOOL_IMPL.get(name)
            if impl is None:
                result = f"error: unknown tool {name}"
            else:
                try:
                    result = impl(args, ctx)
                except Exception as e:
                    result = f"error: {str(e)[:600]}"
            messages.append({"role": "tool",
                             "tool_call_id": tc.get("id", name),
                             "content": str(result)[:16000]})
        if ctx.get("pending_images"):
            content = [{"type": "text",
                        "text": f"Rendered pages of "
                                f"{ctx.get('pending_images_label')} for your "
                                f"visual review:"}]
            for b64 in ctx["pending_images"]:
                content.append({"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{b64}"}})
            messages.append({"role": "user", "content": content})
            ctx["pending_images"] = None
    if reply is None:
        reply = ("I hit the tool-step limit before finishing. State of the "
                 "working tree was reset; nothing partial was committed."
                 if not ctx["committed"] else
                 f"Hit the step limit after committing {ctx['committed']}; "
                 f"check the commit and tell me if anything is off.")
        if not ctx["committed"]:
            sync_to_main()
    slack("chat.postMessage", {"channel": channel, "text": reply[:39000],
                               "thread_ts": thread_ts or ts})
    slack("reactions.add", {"channel": channel, "name": HANDLED_REACTION,
                            "timestamp": ts})


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


def parse_plan(raw):
    raw = raw.strip()
    raw = re.sub(r"^```(json)?\s*|\s*```$", "", raw, flags=re.M).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"summary": "REFUSED: model did not return JSON",
                "branch_hint": "refused", "files": []}


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
        relevant.append(f"### {rel}\n{read_repo(rel, 8000)}")
    prompt = (
        f"REPOSITORY FILE LISTING:\n{listing}\n\n"
        f"FILE CONTENTS:\n\n" + "\n\n".join(relevant) +
        f"\n\nINSTRUCTION FROM FIRAS:\n{instruction}"
    )
    msg = kimi_call([{"role": "system", "content": APPLY_SYSTEM},
                     {"role": "user", "content": prompt}])
    plan = parse_plan(msg.get("content") or "")
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
        path = safe_path(f["path"])
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
