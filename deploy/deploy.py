#!/usr/bin/env python3
"""Provision and operate the LinkedIn heartbeat agent on Claude Managed Agents.

Stdlib only. All configuration comes from environment variables; no secrets
are ever written to disk or printed.

Actions:
  provision   Create or reuse the vault, environment, agent, and scheduled
              deployment. Idempotent by resource name. Pass --recreate to
              archive the existing deployment and rebuild agent, environment,
              and deployment from the current repo files.
  run         Trigger one manual deployment run right now.
  fire MSG    Start a one-off session with a custom directive (breaking news
              nudge, retro now, and so on) using the same agent, environment,
              vault, and repo mount.
  status      Show the deployment, its schedule, and the last 10 runs.
  pause       Pause the schedule (manual runs still allowed).
  unpause     Resume the schedule.

Required env:   ANTHROPIC_API_KEY
Optional env:   APIFY_API_KEY, TAVILY_API_KEY, SLACK_BOT_TOKEN,
                GH_STATE_TOKEN, FIREWORKS_API_KEY   (vault credentials;
                missing ones are skipped with a warning)
Overrides:      AGENT_MODEL (default claude-opus-5)
                HEARTBEAT_CRON (default "15 7-21/2 * * *")
                HEARTBEAT_TZ (default America/Chicago)
                REPO_URL (default https://github.com/nevaubi/forsocialsss)
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.anthropic.com"
BETA = "managed-agents-2026-04-01"

AGENT_NAME = "linkedin-heartbeat"
ENV_NAME = "linkedin-heartbeat-env"
VAULT_NAME = "linkedin-heartbeat-secrets"
DEPLOYMENT_NAME = "linkedin-heartbeat"
MOUNT_PATH = "/workspace/forsocialsss"

# Each credential is substituted at the network boundary only for its own
# hosts, so a leaked placeholder is useless anywhere else.
SECRET_HOSTS = {
    "APIFY_API_KEY": ["api.apify.com"],
    "TAVILY_API_KEY": ["api.tavily.com"],
    "SLACK_BOT_TOKEN": ["slack.com"],
    "SLACK_USER_TOKEN": ["slack.com"],
    "GH_STATE_TOKEN": ["github.com", "api.github.com", "*.githubusercontent.com"],
    "FIREWORKS_API_KEY": ["api.fireworks.ai"],
}
SECRET_NAMES = list(SECRET_HOSTS)

ALLOWED_HOSTS = [
    "api.apify.com",
    "api.tavily.com",
    "slack.com",
    "github.com",
    "api.github.com",
    "*.githubusercontent.com",
    "hn.algolia.com",
    "export.arxiv.org",
    "api.fireworks.ai",
]

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def api(method, path, body=None, ok_missing=False):
    """Call the Claude API. Returns parsed JSON, or None on 404/405 when
    ok_missing is set (used for optimistic list calls)."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        die("ANTHROPIC_API_KEY is not set")
    url = API + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("x-api-key", key)
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("anthropic-beta", BETA)
    if data is not None:
        req.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = resp.read().decode()
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        if ok_missing and e.code in (404, 405):
            return None
        die(f"{method} {path} failed with HTTP {e.code}:\n{detail}")
    except urllib.error.URLError as e:
        die(f"{method} {path} failed: {e.reason}")


def die(msg):
    print(f"deploy.py: error: {msg}", file=sys.stderr)
    sys.exit(1)


def warn(msg):
    print(f"deploy.py: warning: {msg}")


def read_repo_file(rel):
    path = os.path.join(REPO_ROOT, rel)
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def list_all(path):
    """List a collection, following pagination if present."""
    items = []
    after = None
    while True:
        q = "?limit=100" + (f"&after_id={after}" if after else "")
        resp = api("GET", path + q, ok_missing=True)
        if resp is None:
            return items
        data = resp.get("data", [])
        items.extend(data)
        if resp.get("has_more") and data:
            after = data[-1].get("id")
        else:
            return items


def find_by_name(path, name, key="name"):
    for item in list_all(path):
        if item.get(key) == name or item.get("display_name") == name:
            if item.get("archived_at"):
                continue
            return item
    return None


def ensure_vault():
    vault = find_by_name("/v1/vaults", VAULT_NAME, key="display_name")
    if vault:
        print(f"vault: reusing {vault['id']}")
    else:
        vault = api("POST", "/v1/vaults", {"display_name": VAULT_NAME})
        print(f"vault: created {vault['id']}")
    vid = vault["id"]

    existing = {}
    for cred in list_all(f"/v1/vaults/{vid}/credentials"):
        sn = cred.get("secret_name") or cred.get("auth", {}).get("secret_name")
        if sn and not cred.get("archived_at"):
            existing[sn] = cred["id"]

    present, missing = [], []
    for name in SECRET_NAMES:
        value = os.environ.get(name, "").strip()
        if not value:
            missing.append(name)
            continue
        if name in existing:
            # Rotate through the documented archive-and-recreate path so the
            # key is freed before the replacement is written.
            api("POST", f"/v1/vaults/{vid}/credentials/{existing[name]}/archive")
        api(
            "POST",
            f"/v1/vaults/{vid}/credentials",
            {
                "display_name": name,
                "auth": {
                    "type": "environment_variable",
                    "secret_name": name,
                    "secret_value": value,
                    "networking": {
                        "type": "limited",
                        "allowed_hosts": SECRET_HOSTS[name],
                    },
                },
            },
        )
        present.append(name)
    if present:
        print(f"vault: credentials set for {', '.join(present)}")
    for name in missing:
        warn(f"secret {name} not provided; the agent runs degraded without it "
             f"(see README for what each one unlocks)")
    return vid, missing


def ensure_environment(recreate):
    existing = find_by_name("/v1/environments", ENV_NAME)
    if existing and not recreate:
        print(f"environment: reusing {existing['id']}")
        return existing["id"]
    if existing and recreate:
        api("POST", f"/v1/environments/{existing['id']}/archive", ok_missing=True)
        print(f"environment: archived {existing['id']}")
    env = api(
        "POST",
        "/v1/environments",
        {
            "name": ENV_NAME,
            "config": {
                "type": "cloud",
                "packages": {"pip": ["requests"]},
                "networking": {
                    "type": "limited",
                    "allowed_hosts": ALLOWED_HOSTS,
                    "allow_package_managers": True,
                    "allow_mcp_servers": False,
                },
            },
        },
    )
    print(f"environment: created {env['id']}")
    return env["id"]


def ensure_agent(recreate):
    existing = find_by_name("/v1/agents", AGENT_NAME)
    if existing and not recreate:
        print(f"agent: reusing {existing['id']}")
        return existing["id"]
    if existing and recreate:
        api("POST", f"/v1/agents/{existing['id']}/archive", ok_missing=True)
        print(f"agent: archived {existing['id']}")
    agent = api(
        "POST",
        "/v1/agents",
        {
            "name": AGENT_NAME,
            "model": os.environ.get("AGENT_MODEL", "claude-opus-5"),
            "system": read_repo_file("prompts/agent-system.md"),
            "tools": [{"type": "agent_toolset_20260401"}],
        },
    )
    print(f"agent: created {agent['id']}")
    return agent["id"]


def repo_resource():
    resource = {
        "type": "github_repository",
        "url": os.environ.get("REPO_URL", "https://github.com/nevaubi/forsocialsss"),
        "mount_path": MOUNT_PATH,
    }
    token = os.environ.get("GH_STATE_TOKEN", "").strip()
    if token:
        resource["authorization_token"] = token
    return resource


def kickoff_event(text):
    return {"type": "user.message", "content": [{"type": "text", "text": text}]}


def ensure_deployment(agent_id, env_id, vault_id, recreate):
    existing = find_by_name("/v1/deployments", DEPLOYMENT_NAME)
    if existing and not recreate:
        print(f"deployment: reusing {existing['id']} (status {existing.get('status')})")
        return existing
    if existing and recreate:
        api("POST", f"/v1/deployments/{existing['id']}/archive")
        print(f"deployment: archived {existing['id']}")
    dep = api(
        "POST",
        "/v1/deployments",
        {
            "name": DEPLOYMENT_NAME,
            "agent": agent_id,
            "environment_id": env_id,
            "vault_ids": [vault_id],
            "resources": [repo_resource()],
            "initial_events": [
                kickoff_event(read_repo_file("prompts/deployment-kickoff.md"))
            ],
            "schedule": {
                "type": "cron",
                "expression": os.environ.get("HEARTBEAT_CRON", "15 7-21/2 * * *"),
                "timezone": os.environ.get("HEARTBEAT_TZ", "America/Chicago"),
            },
        },
    )
    print(f"deployment: created {dep['id']}")
    return dep


def provision(recreate):
    vault_id, missing = ensure_vault()
    env_id = ensure_environment(recreate)
    agent_id = ensure_agent(recreate)
    dep = ensure_deployment(agent_id, env_id, vault_id, recreate)
    print()
    print("provisioned:")
    print(f"  agent        {agent_id}")
    print(f"  environment  {env_id}")
    print(f"  vault        {vault_id}")
    print(f"  deployment   {dep['id']} ({dep.get('status')})")
    upcoming = (dep.get("schedule") or {}).get("upcoming_runs_at") or []
    for ts in upcoming[:3]:
        print(f"  next run     {ts}")
    if missing:
        print()
        print(f"degraded until these secrets are added and provision is rerun: "
              f"{', '.join(missing)}")


def get_deployment_or_die():
    dep = find_by_name("/v1/deployments", DEPLOYMENT_NAME)
    if not dep:
        die(f"deployment {DEPLOYMENT_NAME!r} not found; run provision first")
    return dep


def run_now():
    dep = get_deployment_or_die()
    result = api("POST", f"/v1/deployments/{dep['id']}/run")
    print(json.dumps(result, indent=2))


def fire(message):
    vault = find_by_name("/v1/vaults", VAULT_NAME, key="display_name")
    env = find_by_name("/v1/environments", ENV_NAME)
    agent = find_by_name("/v1/agents", AGENT_NAME)
    if not (vault and env and agent):
        die("agent, environment, or vault missing; run provision first")
    session = api(
        "POST",
        "/v1/sessions",
        {
            "agent": agent["id"],
            "environment_id": env["id"],
            "vault_ids": [vault["id"]],
            "resources": [repo_resource()],
            "title": "fire: manual directive",
        },
    )
    api(
        "POST",
        f"/v1/sessions/{session['id']}/events",
        {
            "events": [
                kickoff_event(
                    "Fire trigger. Read prompts/routine-fire.md for handling "
                    "rules, then act on this directive:\n\n" + message
                )
            ]
        },
    )
    print(f"session: {session['id']} started with the directive")


def status():
    dep = get_deployment_or_die()
    print(json.dumps({k: dep.get(k) for k in
                      ("id", "status", "paused_reason", "schedule")}, indent=2))
    runs = api(
        "GET",
        f"/v1/deployment_runs?deployment_id={urllib.parse.quote(dep['id'])}&limit=10",
        ok_missing=True,
    )
    if runs:
        print()
        print("recent runs:")
        for r in runs.get("data", []):
            err = (r.get("error") or {}).get("type") or "ok"
            print(f"  {r.get('created_at')}  session={r.get('session_id')}  {err}")


def pause(unpause=False):
    dep = get_deployment_or_die()
    verb = "unpause" if unpause else "pause"
    api("POST", f"/v1/deployments/{dep['id']}/{verb}")
    print(f"deployment {dep['id']}: {verb}d")


def main():
    args = [a for a in sys.argv[1:] if a != "--recreate"]
    recreate = "--recreate" in sys.argv[1:]
    action = args[0] if args else "provision"
    if action == "provision":
        provision(recreate)
    elif action == "run":
        run_now()
    elif action == "fire":
        if len(args) < 2:
            die("fire requires a message argument")
        fire(" ".join(args[1:]))
    elif action == "status":
        status()
    elif action == "pause":
        pause()
    elif action == "unpause":
        pause(unpause=True)
    else:
        die(f"unknown action {action!r}")


if __name__ == "__main__":
    main()
