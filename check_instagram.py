#!/usr/bin/env python3
"""Instagram post alerts.

Checks the profiles listed in profiles.txt through Apify and sends a Slack
message for every post it has not seen before. Uses two Apify keys: if key 1
fails (for example out of credits), it retries with key 2.

Needs three secrets (set in GitHub, see README.md):
  APIFY_TOKEN_1, APIFY_TOKEN_2 (optional), SLACK_WEBHOOK_URL
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

ACTOR = "apidojo~instagram-scraper"
STATE_FILE = os.path.join("state", "seen.json")
PROFILES_FILE = "profiles.txt"
IST = timezone(timedelta(hours=5, minutes=30))
KEEP_PER_PROFILE = 100


# ---------- helpers ----------

def load_profiles():
    names = []
    with open(PROFILES_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip().lstrip("@")
            if line and not line.startswith("#"):
                names.append(line.lower())
    return names


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    state.setdefault("initialized", False)
    state.setdefault("seen", {})
    state.setdefault("down_alerted", False)
    state.setdefault("failover_alerted", False)
    return state


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def post_json(url, payload, headers=None, timeout=60):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def slack_post(webhook, text):
    status, body = post_json(webhook, {"text": text}, timeout=30)
    if status != 200:
        raise RuntimeError(f"Slack returned {status}: {body[:200]}")


# ---------- Apify ----------

def fetch_posts(token, usernames, window, per_profile):
    url = (
        f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items"
        "?timeout=120&format=json"
    )
    payload = {
        "startUrls": [f"https://www.instagram.com/{u}/" for u in usernames],
        "resultsLimit": per_profile,
        "until": window,
        "maxItems": per_profile * len(usernames),
    }
    status, body = post_json(
        url, payload, headers={"Authorization": f"Bearer {token}"}, timeout=150
    )
    if status not in (200, 201):
        raise RuntimeError(f"Apify returned {status}: {body[:200]}")
    items = json.loads(body)
    if not isinstance(items, list):
        raise RuntimeError(f"Unexpected Apify response: {body[:200]}")
    return [p for p in (normalise(i) for i in items) if p]


def normalise(item):
    code = item.get("code")
    if not code:
        return None  # "noResults" marker rows have no code
    owner = item.get("owner")
    user = owner.get("username") if isinstance(owner, dict) else None
    user = user or item.get("owner.username") or ""
    return {
        "code": code,
        "user": user.lower(),
        "url": item.get("url") or f"https://www.instagram.com/p/{code}/",
        "created": item.get("createdAt") or "",
        "caption": item.get("caption") or "",
    }


def fetch_with_failover(keys, usernames, window, per_profile):
    """keys is a list of (label, token). Returns (posts, label_used)."""
    errors = []
    for label, token in keys:
        try:
            return fetch_posts(token, usernames, window, per_profile), label
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:200]
            errors.append(f"{label}: HTTP {e.code} {detail}")
        except Exception as e:  # network problems, bad JSON, timeouts
            errors.append(f"{label}: {type(e).__name__} {e}")
    raise RuntimeError("; ".join(errors))


# ---------- messages ----------

def when(created):
    try:
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        return dt.astimezone(IST).strftime("%d %b, %I:%M %p IST")
    except (ValueError, AttributeError):
        return "time unknown"


def alert_text(post, prefix=""):
    caption = " ".join(post["caption"].split())
    if len(caption) > 220:
        caption = caption[:217].rstrip() + "..."
    lines = [f"{prefix}:camera_with_flash: *New Instagram post from @{post['user']}*"]
    if caption:
        lines.append(caption)
    lines.append(f"<{post['url']}|Open post> | posted {when(post['created'])}")
    return "\n".join(lines)


# ---------- main ----------

def main():
    keys = []
    for label, env in (("key 1", "APIFY_TOKEN_1"), ("key 2", "APIFY_TOKEN_2")):
        token = os.environ.get(env, "").strip()
        if token:
            keys.append((label, token))
    webhook = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if not keys or not webhook:
        print("Missing secrets: need APIFY_TOKEN_1 and SLACK_WEBHOOK_URL.")
        return 1

    usernames = load_profiles()
    if not usernames:
        print("profiles.txt is empty.")
        return 1

    # Test mode: send the latest post of each profile as a sample alert.
    if os.environ.get("TEST_ALERT", "").lower() == "true":
        posts, label = fetch_with_failover(keys, usernames, "3 days", 1)
        if not posts:
            slack_post(webhook, "TEST: connected to Apify and Slack, but no posts in the last 3 days to show.")
        for p in posts:
            slack_post(webhook, alert_text(p, prefix="TEST (sample alert) | "))
        print(f"Test alert sent using {label}.")
        return 0

    state = load_state()
    first_run = not state["initialized"]
    window = "3 days" if first_run else "3 hours"
    per_profile = 3 if first_run else 5

    try:
        posts, label_used = fetch_with_failover(keys, usernames, window, per_profile)
    except RuntimeError as e:
        print(f"All Apify keys failed: {e}")
        if not state["down_alerted"]:
            try:
                slack_post(
                    webhook,
                    ":warning: Instagram tracker is down. Neither Apify key worked. "
                    "Check your Apify credits and the tokens saved in GitHub secrets.",
                )
                state["down_alerted"] = True
            except Exception as se:
                print(f"Could not post the down notice to Slack: {se}")
        save_state(state)
        return 1

    state["down_alerted"] = False

    # Tell the user once when key 1 stops working and key 2 takes over.
    if label_used != keys[0][0]:
        if not state["failover_alerted"]:
            try:
                slack_post(
                    webhook,
                    ":information_source: Apify key 1 failed, so the tracker switched to key 2. "
                    "Top up or replace key 1 when you can.",
                )
                state["failover_alerted"] = True
            except Exception as se:
                print(f"Could not post the failover notice to Slack: {se}")
    else:
        state["failover_alerted"] = False

    seen = state["seen"]

    if first_run:
        slack_post(
            webhook,
            ":white_check_mark: Instagram tracker is live. Watching "
            + ", ".join(f"@{u}" for u in usernames)
            + ". Their latest posts are saved as the starting point, so you will only be alerted about new ones.",
        )
        for p in posts:
            codes = seen.setdefault(p["user"], [])
            if p["code"] not in codes:
                codes.append(p["code"])
        state["initialized"] = True
        save_state(state)
        print(f"First run done, saved {len(posts)} posts as baseline.")
        return 0

    new_posts = [p for p in posts if p["code"] not in seen.get(p["user"], [])]
    new_posts.sort(key=lambda p: p["created"])
    exit_code = 0
    for p in new_posts:
        try:
            slack_post(webhook, alert_text(p))
        except Exception as e:
            print(f"Slack failed for {p['code']}: {e}")
            exit_code = 1
            break  # not marked as seen, so it is retried on the next run
        codes = seen.setdefault(p["user"], [])
        codes.append(p["code"])
        del codes[:-KEEP_PER_PROFILE]
        print(f"Alerted: @{p['user']} {p['code']}")

    save_state(state)
    print(f"Checked {len(usernames)} profiles with {label_used}, {len(new_posts)} new posts.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
