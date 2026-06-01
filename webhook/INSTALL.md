# Auto-deploy webhook — install steps

All commands run on the production server. Run them in order.

## 1. Give www-data an SSH deploy key for the repo

The webhook runs deploy.sh as `www-data`, which calls `git pull`. Today
`www-data` has no SSH key, so we create one and register it as a GitHub
Deploy Key (read-only, scoped to this repo).

```bash
# Create an ssh dir owned by www-data (its $HOME is /var/www, so we use that).
sudo install -d -o www-data -g www-data -m 0700 /var/www/.ssh

# Generate a keypair (no passphrase — it has to be non-interactive).
sudo -u www-data ssh-keygen -t ed25519 -N "" \
    -f /var/www/.ssh/id_ed25519 \
    -C "afterclass-deploy@$(hostname)"

# Trust github.com's host key so the first pull doesn't prompt.
sudo -u www-data ssh-keyscan github.com >> /var/www/.ssh/known_hosts
sudo chown www-data:www-data /var/www/.ssh/known_hosts

# Print the public key — copy this into GitHub.
sudo cat /var/www/.ssh/id_ed25519.pub
```

Then in GitHub: **repo → Settings → Deploy keys → Add deploy key**, paste
the public key, title "afterclass prod", leave "Allow write access"
**unchecked**.

Verify:

```bash
sudo -u www-data ssh -T git@github.com
# Expected: "Hi changjiang1124/afterclass! You've successfully authenticated..."
```

## 2. Pick a webhook secret and store it

```bash
# Generate a strong random secret (save the output — you will paste it into GitHub).
openssl rand -hex 32

# Write it to a root-owned env file the systemd unit will load.
sudo tee /etc/afterclass-webhook.env >/dev/null <<'EOF'
GITHUB_WEBHOOK_SECRET=PASTE_THE_SECRET_FROM_ABOVE_HERE
EOF
sudo chmod 0640 /etc/afterclass-webhook.env
sudo chown root:www-data /etc/afterclass-webhook.env
```

## 3. Install the sudoers rule

deploy.sh runs `sudo systemctl restart afterclass`. Give www-data exactly
that, no more.

```bash
sudo install -m 0440 -o root -g root \
    /var/www/afterclass/webhook/sudoers.afterclass-deploy \
    /etc/sudoers.d/afterclass-deploy

# Sanity-check the sudoers file (will refuse to install if broken).
sudo visudo -c
```

## 4. Install and start the listener service

```bash
sudo ln -sf /var/www/afterclass/webhook/afterclass-webhook.service \
    /etc/systemd/system/afterclass-webhook.service
sudo systemctl daemon-reload
sudo systemctl enable --now afterclass-webhook
sudo systemctl status afterclass-webhook --no-pager
```

Quick local check (should return `ok`):

```bash
curl -fsS http://127.0.0.1:9000/health
```

## 5. Expose it through nginx

Edit `/etc/nginx/sites-available/afterclass` and paste the block from
`webhook/nginx-location.conf` inside the existing `server { ... listen 443 ssl; ... }`
section (e.g. just above the existing `location / { ... }`). Then:

```bash
sudo nginx -t
sudo systemctl reload nginx

# External smoke test (signature missing → 401 is the expected response):
curl -i -X POST https://afterclass.learnchineseperth.com.au/gh-webhook/ \
    -H 'X-GitHub-Event: ping' -d '{}'
```

## 6. Configure the GitHub webhook

In the repo: **Settings → Webhooks → Add webhook**

- Payload URL: `https://afterclass.learnchineseperth.com.au/gh-webhook/`
- Content type: `application/json`
- Secret: the value of `GITHUB_WEBHOOK_SECRET` from step 2
- SSL verification: **enabled**
- Which events: **Just the push event**
- Active: ✓

Click **Add webhook**. GitHub immediately sends a `ping` — open the webhook,
scroll to **Recent Deliveries**, expand it, you should see HTTP 200 with
body `pong`.

## 7. Verify end-to-end

```bash
# Tail listener logs in one terminal:
sudo journalctl -u afterclass-webhook -f
# And the deploy log in another:
tail -f /var/www/afterclass/logs/webhook-deploy.log
```

Push a trivial commit to `main`. Within a few seconds you should see:

1. listener log: `accepted push by <you> after <sha>`
2. deploy log: pull → collectstatic → migrate → `Active: active (running)`
3. service restarted: `systemctl status afterclass`

## Troubleshooting

- **401 invalid signature**: secret in `/etc/afterclass-webhook.env` doesn't
  match the one configured in GitHub. Edit the env file, then
  `sudo systemctl restart afterclass-webhook`.
- **deploy log shows `Permission denied (publickey)`**: step 1 wasn't
  completed, or the deploy key wasn't added to GitHub.
- **deploy log shows `sudo: a password is required`**: step 3 wasn't applied
  or visudo rejected the file.
- **GitHub shows 502/504**: the listener isn't running — check
  `sudo systemctl status afterclass-webhook`.
- **Manually trigger a deploy** without pushing: in GitHub webhook page →
  Recent Deliveries → pick a delivery → **Redeliver**.
