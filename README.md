# Instagram post alerts 

Sends a Slack message whenever a tracked Instagram profile posts something new.

- Checks every 30 minutes on GitHub Actions (free).
- Reads posts through Apify. Uses key 1 first and switches to key 2 if key 1 fails.
- Remembers the posts it has already alerted on, so you never get duplicates.
- Sends a Slack warning if both Apify keys stop working.

Profiles tracked right now are in `profiles.txt`: thevarunmayya and vaibhavsisinty.

## Setup (about 15 minutes)

### Step 1. Create the GitHub repo

1. Go to https://github.com/new while signed in to your GitHub account.
2. Repository name: `instagram-post-alerts`.
3. Choose **Private**.
4. Leave "Add a README", ".gitignore" and "license" all unticked. Click **Create repository**.

### Step 2. Upload the files

1. Unzip `instagram-post-alerts.zip` on your computer.
2. On a Mac, press Cmd+Shift+. (dot) in Finder to show hidden folders. You need to see the `.github` folder.
3. On the new repo page, click **uploading an existing file**.
4. Select everything inside the unzipped folder (`.github`, `state`, `check_instagram.py`, `profiles.txt`, `README.md`) and drag it into the browser window.
5. Wait for the upload to finish, then click **Commit changes**.

Check: in the repo you should see `.github/workflows/check.yml`. If the `.github` folder is missing, click **Add file > Create new file**, type `.github/workflows/check.yml` as the name (typing the slashes creates the folders), paste in the contents of `check.yml` from the zip, and commit.

### Step 3. Create the Slack webhook

This is the link the script uses to post into Slack.

1. Go to https://api.slack.com/apps and click **Create New App > From scratch**.
2. Name it `Instagram Alerts`, pick your Slack workspace, click **Create App**.
3. In the left menu, click **Incoming Webhooks** and switch **Activate Incoming Webhooks** to On.
4. Click **Add New Webhook to Workspace**.
5. Choose where alerts should land: a channel, or your own direct messages. Click **Allow**.
6. Copy the **Webhook URL** (it starts with `https://hooks.slack.com/services/`).

If Slack says an admin has to approve the app, ask your workspace admin to approve it. The webhook will not work until they do.

### Step 4. Get your two Apify tokens

1. Log in to https://console.apify.com with the first account.
2. Go to **Settings > API & Integrations** and copy the **Personal API token**.
3. Repeat with the second account to get a second token.

### Step 5. Save the three secrets in GitHub

In your repo, go to **Settings > Secrets and variables > Actions** and click **New repository secret** three times:

| Name | Value |
|---|---|
| `APIFY_TOKEN_1` | token from the first Apify account |
| `APIFY_TOKEN_2` | token from the second Apify account (optional, but this is the backup) |
| `SLACK_WEBHOOK_URL` | the webhook URL from step 3 |

Paste the values directly into GitHub. Do not share them in chat or email.

### Step 6. Test it

1. Open the **Actions** tab of the repo. If GitHub asks you to enable workflows, click the green button.
2. Click **Instagram post alerts** in the left list, then **Run workflow**.
3. Tick **Send a sample alert to Slack**, then click the green **Run workflow** button.
4. After about a minute, you should get two sample alerts in Slack (one per profile). If you do, Apify and Slack are both connected.
5. Run the workflow once more with the tick **off**. You will get "Instagram tracker is live" in Slack. This saves the current posts as the starting point.

From here it runs by itself every 30 minutes.

## Changing things later

- **Add or remove profiles:** edit `profiles.txt` in GitHub (pencil icon), one username per line.
- **Change how often it checks:** edit `.github/workflows/check.yml` and change the `cron` line. `"0 * * * *"` means hourly.
- **Pause it:** Actions tab > Instagram post alerts > the three dots > Disable workflow.

## If something goes wrong

- **No sample alert in Slack:** open the failed run in the Actions tab and read the red step. A Slack error means the webhook URL is wrong or the app is not approved. An Apify error means a token is wrong or out of credits.
- **Slack says "Apify key 1 failed, switched to key 2":** key 1 ran out of credits or was replaced. Top it up or update the `APIFY_TOKEN_1` secret.
- **Slack says "Instagram tracker is down":** neither key works. Check credits and tokens.
- **Check the cost after the first day:** Apify console > Billing > Usage. It should be a few cents a day. Each post found costs about $0.0005, and runs with nothing new cost almost nothing.
- GitHub can start scheduled runs a few minutes late. That is normal.
