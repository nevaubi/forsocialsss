// Instant-reply receiver for the forsocialsss assistant.
//
// NOT CURRENTLY DEPLOYED. The live instant path is assistant/listener.py
// (Socket Mode). This file predates the syntax-free router and persistent
// memory; port those from assistant.py before ever deploying it.
//
// Deploy on Cloudflare Workers (free tier). Slack's Events API pushes every
// DM to this worker the moment it is sent; the worker verifies the request
// signature, asks Kimi K3 on Fireworks with current repo state as context,
// and replies in the same thread within a few seconds. It marks handled
// messages with the robot_face reaction, so the 5-minute GitHub Actions
// poller (the fallback path, and the handler for apply: messages) skips
// anything the worker already answered.
//
// Worker secrets to configure (Settings > Variables and Secrets, type Secret):
//   SLACK_BOT_TOKEN       xoxb token, same one the agents use
//   SLACK_SIGNING_SECRET  Slack app > Basic Information > Signing Secret
//   FIREWORKS_API_KEY     Fireworks key
//   GH_DISPATCH_TOKEN     optional: GitHub token with actions write access;
//                         lets apply: messages dispatch the PR workflow
//                         instantly instead of waiting for the cron
//   ANTHROPIC_API_KEY     optional: adds live deployment status to context
//
// Slack app wiring (api.slack.com/apps > your app):
//   Event Subscriptions > Enable > Request URL = this worker's URL
//   Subscribe to bot events: message.im
//   Save, and reinstall if prompted.

const FIRAS_ID = "U0BM0RF8AHM";
const REPO = "nevaubi/forsocialsss";
const RAW = `https://raw.githubusercontent.com/${REPO}/main/`;
const HANDLED_REACTION = "robot_face";
const DEPLOYMENT_NAME = "linkedin-heartbeat";
const HEARTBEAT_EXACT = new Set(["approve", "hold", "status", "retro now"]);
const HEARTBEAT_PREFIX = ["edit:", "kill:", "posted "];

const CHAT_SYSTEM = `You are Firas Shaher's operations assistant for his autonomous LinkedIn content agent system. You are a separate model (Kimi K3) from the heartbeat agent that does the content work; your job is to keep Firas informed and answer his questions.

Voice: terse, grounded, direct. No em dashes ever. No hype, no exclamation points, no emoji unless he uses them first. Answer the question asked; do not pad.

You have read access to the full system state, provided below: the agent's constitution, current topics, draft queue, run log, lessons, recent state, and the live deployment status when available. Ground every answer in that data. If the data does not contain the answer, say so plainly instead of guessing.

You are read-only. You cannot change files, trigger runs, or post anything. If Firas asks you to change something, tell him to send the same request prefixed with "apply:" and a pull request will be opened for his review. If he asks about heartbeat directives (approve, edit:, kill:, hold, status, posted, retro now), remind him those go to the heartbeat agent in this same DM and are picked up on its next cycle.

Never reveal, print, or speculate about credentials or tokens.`;

export default {
  async fetch(request, env, ctx) {
    if (request.method !== "POST") {
      return new Response("assistant worker", { status: 200 });
    }
    const body = await request.text();

    const valid = await verifySlackSignature(request, body, env);
    if (!valid) {
      return new Response("bad signature", { status: 401 });
    }

    const payload = JSON.parse(body);
    if (payload.type === "url_verification") {
      return new Response(JSON.stringify({ challenge: payload.challenge }), {
        headers: { "content-type": "application/json" },
      });
    }

    // Slack retries delivery if it does not get a fast 200. We always ack
    // immediately and skip retried deliveries to avoid duplicate replies.
    if (request.headers.get("x-slack-retry-num")) {
      return new Response("ok", { status: 200 });
    }

    if (payload.type === "event_callback") {
      const ev = payload.event || {};
      const isFirasDm =
        ev.type === "message" &&
        ev.channel_type === "im" &&
        ev.user === FIRAS_ID &&
        !ev.subtype &&
        !ev.bot_id &&
        (ev.text || "").trim().length > 0;
      if (isFirasDm && !isHeartbeatDirective(ev.text)) {
        ctx.waitUntil(handleMessage(ev, env));
      }
    }
    return new Response("ok", { status: 200 });
  },
};

function isHeartbeatDirective(text) {
  const t = text.trim().toLowerCase();
  if (HEARTBEAT_EXACT.has(t)) return true;
  return HEARTBEAT_PREFIX.some((p) => t.startsWith(p));
}

async function verifySlackSignature(request, body, env) {
  const ts = request.headers.get("x-slack-request-timestamp");
  const sig = request.headers.get("x-slack-signature");
  if (!ts || !sig) return false;
  if (Math.abs(Date.now() / 1000 - Number(ts)) > 300) return false;
  const base = `v0:${ts}:${body}`;
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(env.SLACK_SIGNING_SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const mac = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(base),
  );
  const hex = [...new Uint8Array(mac)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  const expected = `v0=${hex}`;
  if (expected.length !== sig.length) return false;
  let diff = 0;
  for (let i = 0; i < expected.length; i++) {
    diff |= expected.charCodeAt(i) ^ sig.charCodeAt(i);
  }
  return diff === 0;
}

async function handleMessage(ev, env) {
  const text = ev.text.trim();
  try {
    // Skip if the cron poller beat us to it.
    const already = await slack(env, "reactions.get", {
      channel: ev.channel,
      timestamp: ev.ts,
    }).catch(() => null);
    const reactions = already?.message?.reactions || [];
    if (reactions.some((r) => r.name === HANDLED_REACTION)) return;

    if (text.toLowerCase().startsWith("apply:")) {
      await handleApply(ev, text.slice(6).trim(), env);
    } else {
      const context = await buildContext(env);
      const convo = await recentConversation(ev.channel, env);
      const reply = await kimi(env, [
        ...convo,
        {
          role: "user",
          content: `SYSTEM STATE SNAPSHOT (current):\n${context}\n\nFIRAS'S MESSAGE:\n${text}`,
        },
      ]);
      await slack(env, "chat.postMessage", {
        channel: ev.channel,
        text: reply.slice(0, 39000),
        thread_ts: ev.ts,
      });
    }
    await slack(env, "reactions.add", {
      channel: ev.channel,
      name: HANDLED_REACTION,
      timestamp: ev.ts,
    }).catch(() => null);
  } catch (err) {
    await slack(env, "chat.postMessage", {
      channel: ev.channel,
      text: `Assistant error: ${String(err).slice(0, 500)}. The 5-minute fallback poller will retry this message.`,
      thread_ts: ev.ts,
    }).catch(() => null);
  }
}

async function handleApply(ev, instruction, env) {
  if (env.GH_DISPATCH_TOKEN) {
    const resp = await fetch(
      `https://api.github.com/repos/${REPO}/actions/workflows/assistant-apply.yml/dispatches`,
      {
        method: "POST",
        headers: {
          authorization: `Bearer ${env.GH_DISPATCH_TOKEN}`,
          accept: "application/vnd.github+json",
          "user-agent": "forsocialsss-assistant-worker",
          "content-type": "application/json",
        },
        body: JSON.stringify({
          ref: "main",
          inputs: { instruction: instruction.slice(0, 1000), channel: ev.channel },
        }),
      },
    );
    const note = resp.ok
      ? "On it. Preparing a pull request for that change; link lands here when it is open."
      : `Could not dispatch the apply workflow (HTTP ${resp.status}). The 5-minute poller will pick it up instead.`;
    await slack(env, "chat.postMessage", {
      channel: ev.channel,
      text: note,
      thread_ts: ev.ts,
    });
    // Only mark handled if the dispatch succeeded; otherwise leave it for
    // the poller.
    if (!resp.ok) throw new Error("dispatch failed, leaving for poller");
  } else {
    await slack(env, "chat.postMessage", {
      channel: ev.channel,
      text: "Apply request noted. The workflow poller picks this up within 5 minutes and a pull request link will land here.",
      thread_ts: ev.ts,
    });
    throw new Error("no dispatch token, leaving for poller");
  }
}

async function recentConversation(channel, env) {
  try {
    const resp = await slack(env, "conversations.history", {
      channel,
      limit: 12,
    });
    return (resp.messages || [])
      .sort((a, b) => Number(a.ts) - Number(b.ts))
      .filter((m) => (m.text || "").trim())
      .map((m) => ({
        role: m.user === FIRAS_ID ? "user" : "assistant",
        content: m.text.slice(0, 2000),
      }));
  } catch {
    return [];
  }
}

async function buildContext(env) {
  const files = [
    ["Constitution (CLAUDE.md)", "CLAUDE.md", 5000],
    ["Strategy", "identity/strategy.md", 3000],
    ["Topic board", "state/topics.json", 4000],
    ["Watchlist", "state/watchlist.json", 2000],
    ["Draft queue", "state/queue.json", 4000],
    ["Posted history", "state/posted.json", 2000],
    ["Run log tail", "state/run-log.jsonl", 6000],
    ["Lessons tail", "state/lessons.md", 5000],
  ];
  const parts = await Promise.all(
    files.map(async ([title, path, cap]) => {
      try {
        const resp = await fetch(RAW + path, {
          headers: { "user-agent": "forsocialsss-assistant-worker" },
        });
        if (!resp.ok) return `## ${title}\n(unavailable: HTTP ${resp.status})`;
        let text = await resp.text();
        // For logs and lessons, the tail matters more than the head.
        if (path.endsWith(".jsonl") || path.endsWith("lessons.md")) {
          text = text.slice(-cap);
        } else if (text.length > cap) {
          text = text.slice(0, cap) + `\n...(truncated)`;
        }
        return `## ${title}\n${text}`;
      } catch (e) {
        return `## ${title}\n(fetch error)`;
      }
    }),
  );
  parts.push(`## Live deployment status\n${await deploymentStatus(env)}`);
  return parts.join("\n\n");
}

async function deploymentStatus(env) {
  if (!env.ANTHROPIC_API_KEY) return "(not configured on this worker)";
  try {
    const headers = {
      "x-api-key": env.ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01",
      "anthropic-beta": "managed-agents-2026-04-01",
    };
    const deps = await (
      await fetch("https://api.anthropic.com/v1/deployments?limit=100", {
        headers,
      })
    ).json();
    const dep = (deps.data || []).find((d) => d.name === DEPLOYMENT_NAME);
    if (!dep) return "(deployment not found)";
    const runs = await (
      await fetch(
        `https://api.anthropic.com/v1/deployment_runs?deployment_id=${dep.id}&limit=5`,
        { headers },
      )
    ).json();
    return JSON.stringify({
      status: dep.status,
      schedule: dep.schedule?.expression,
      timezone: dep.schedule?.timezone,
      upcoming_runs: (dep.schedule?.upcoming_runs_at || []).slice(0, 2),
      recent_runs: (runs.data || []).map((r) => ({
        at: r.created_at,
        error: r.error?.type || null,
      })),
    });
  } catch (e) {
    return `(status error: ${String(e).slice(0, 200)})`;
  }
}

async function kimi(env, messages) {
  const resp = await fetch(
    "https://api.fireworks.ai/inference/v1/chat/completions",
    {
      method: "POST",
      headers: {
        authorization: `Bearer ${env.FIREWORKS_API_KEY}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model: "accounts/fireworks/models/kimi-k3",
        max_tokens: 2000,
        temperature: 0.4,
        messages: [{ role: "system", content: CHAT_SYSTEM }, ...messages],
      }),
    },
  );
  if (!resp.ok) {
    throw new Error(`fireworks HTTP ${resp.status}: ${(await resp.text()).slice(0, 300)}`);
  }
  const data = await resp.json();
  return data.choices[0].message.content.trim();
}

async function slack(env, method, body) {
  const resp = await fetch(`https://slack.com/api/${method}`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${env.SLACK_BOT_TOKEN}`,
      "content-type": "application/json; charset=utf-8",
    },
    body: JSON.stringify(body),
  });
  const data = await resp.json();
  if (!data.ok) throw new Error(`slack ${method}: ${data.error}`);
  return data;
}
