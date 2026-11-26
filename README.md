# Instagram post alerts 
 
 [![Instagram post alerts](https://github.com/Infrasity-Labs/instagram-post-alerts/actions/workflows/checks.yml/badge.svg)](https://github.com/Infrasity-Labs/instagram-post-alerts/actions/workflows/checks.yml)
 
Sends a Slack message whenever a tracked Instagram profile posts something new.

- Checks every 30 minutes on GitHub Actions (free).
- Reads posts through Apify. Uses key 1 first and switches to key 2 if key 1 fails.
- Remembers the posts it has already alerted on, so you never get duplicates.
- Sends a Slack warning if both Apify keys stop working.

Profiles tracked right now are in `profiles.txt`: thevarunmayya and vaibhavsisinty.

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
