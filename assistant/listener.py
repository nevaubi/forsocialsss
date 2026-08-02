#!/usr/bin/env python3
"""Live Socket Mode listener for instant assistant replies.

Connects to Slack over a websocket (Socket Mode, using the xapp app-level
token) so Firas's DMs reach Kimi the second they are sent, with replies in
about one to two seconds. Runs inside the assistant-listener workflow for a
bounded window, then exits so the workflow can re-dispatch itself; the
5-minute poller remains the fallback for any gap between windows.

Reuses the context assembly, Kimi call, Slack helper, and directive rules
from assistant.py so the two paths cannot drift apart.

Env: SLACK_APP_TOKEN, SLACK_BOT_TOKEN, FIREWORKS_API_KEY,
     ANTHROPIC_API_KEY (optional, live status), GITHUB_TOKEN (apply dispatch)
     LISTENER_MINUTES (default 340)
"""

import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from assistant import (  # noqa: E402
    FIRAS_ID,
    is_heartbeat_directive,
    respond,
    slack,
)

from slack_sdk.socket_mode import SocketModeClient  # noqa: E402
from slack_sdk.socket_mode.request import SocketModeRequest  # noqa: E402
from slack_sdk.socket_mode.response import SocketModeResponse  # noqa: E402
from slack_sdk.web import WebClient  # noqa: E402

processed = set()
processed_lock = threading.Lock()


def already_processed(ts):
    with processed_lock:
        if ts in processed:
            return True
        processed.add(ts)
        if len(processed) > 500:
            for old in sorted(processed)[:250]:
                processed.discard(old)
        return False


def handle(client: SocketModeClient, req: SocketModeRequest):
    # Ack first, always; Slack redelivers anything not acked fast.
    client.send_socket_mode_response(
        SocketModeResponse(envelope_id=req.envelope_id))
    if req.type != "events_api":
        return
    ev = (req.payload or {}).get("event", {})
    if (
        ev.get("type") != "message"
        or ev.get("channel_type") != "im"
        or ev.get("user") != FIRAS_ID
        or ev.get("subtype")
        or ev.get("bot_id")
        or not (ev.get("text") or "").strip()
    ):
        return
    text = ev["text"].strip()
    if is_heartbeat_directive(text):
        return
    if already_processed(ev["ts"]):
        return
    channel = ev["channel"]
    try:
        respond(text, channel, ev["ts"])
        print(f"listener: handled {ev['ts']}", flush=True)
    except Exception as e:  # keep the listener alive on any single failure
        print(f"listener: error handling {ev['ts']}: {e}", flush=True)
        try:
            slack("chat.postMessage", {
                "channel": channel,
                "text": f"Assistant error: {str(e)[:400]}. The 5-minute "
                        f"fallback poller will retry this message.",
                "thread_ts": ev["ts"],
            })
        except Exception:
            pass


def main():
    minutes = int(os.environ.get("LISTENER_MINUTES", "340"))
    client = SocketModeClient(
        app_token=os.environ["SLACK_APP_TOKEN"].strip(),
        web_client=WebClient(token=os.environ["SLACK_BOT_TOKEN"].strip()),
    )
    client.socket_mode_request_listeners.append(handle)
    client.connect()
    print(f"listener: connected, serving for {minutes} minutes", flush=True)
    deadline = time.time() + minutes * 60
    while time.time() < deadline:
        time.sleep(30)
        if not client.is_connected():
            print("listener: reconnecting", flush=True)
            try:
                client.connect()
            except Exception as e:
                print(f"listener: reconnect failed: {e}", flush=True)
    print("listener: window complete, exiting for restart", flush=True)
    client.close()


if __name__ == "__main__":
    main()
