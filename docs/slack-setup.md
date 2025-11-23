# Slack Webhook Setup

The unified webhook server (`examples/unified_webhook_server.py`) supports Slack along with other platforms (Webex, Teams). It offers two security modes, depending on your hosting approach.

## Security Mode Comparison

| Security Mode | Best For | HMAC in App | Rate Limiting | Use Case |
|--------------|----------|-------------|---------------|----------|
| **Web Service Hosted** | ngrok with verification | ❌ Optional | ❌ No | ngrok handles verification at tunnel level |
| **Self-Hosted** | Direct internet exposure | ✅ Required | ✅ Yes | Your server validates requests |

## Web Service Hosted Mode (ngrok with Signature Verification)

### Security Features

- ✅ Approval ID validation (prevents path traversal attacks)
- ✅ ngrok signature verification (at tunnel level)
- ✅ Configurable debug mode
- ❌ No application-level HMAC verification (ngrok handles it)
- ❌ No rate limiting (rely on ngrok)

**When to use:** Production or development with ngrok (free tier: 500 verifications/month, unlimited on Pro/Enterprise)

**Why this is production-ready:** ngrok validates Slack signatures before requests reach your app, providing the same security as application-level HMAC verification.

### Setup with ngrok Signature Verification

```bash
# 1. Get your Slack signing secret
# Go to: https://api.slack.com/apps → Your App → Basic Information → Signing Secret

# 2. Create ngrok traffic policy file: ngrok-slack-policy.yml
cat > ngrok-slack-policy.yml <<EOF
on_http_request:
  - actions:
      - type: "webhook-verification"
        config:
          provider: "slack"
          secret: "YOUR_SLACK_SIGNING_SECRET_HERE"
EOF

# 3. Set environment variables
export SLACK_BOT_TOKEN=xoxb-your-token-here
export ENABLE_SLACK=true
export SECURITY_MODE=local  # ngrok handles verification

# 4. Run the webhook server
python examples/unified_webhook_server.py

# 5. In another terminal, start ngrok with traffic policy
ngrok http 3000 --traffic-policy-file ngrok-slack-policy.yml

# 6. Configure in Slack
# Go to: https://api.slack.com/apps → Your App → Interactivity & Shortcuts
# Set Request URL: https://your-ngrok-url.ngrok.io/slack/interactive
```

**How ngrok verification works:** ngrok validates Slack's signature at the tunnel level before forwarding requests to your app. Invalid requests are blocked automatically.

**Free tier limitation:** 500 signature verifications per month. Upgrade to ngrok Pro or Enterprise for unlimited verifications.

### Alternative (basic setup without verification)

```bash
export SLACK_BOT_TOKEN=xoxb-your-token-here
export ENABLE_SLACK=true
python examples/unified_webhook_server.py
ngrok http 3000  # No verification - use only for quick testing
```

⚠️ **Without ngrok verification or HMAC verification, anyone with your ngrok URL can send fake approval requests.**

## Self-Hosted Mode (Direct Internet Exposure)

### Security Features

- ✅ Slack HMAC-SHA256 signature verification (in application)
- ✅ Approval ID validation (prevents path traversal)
- ✅ Rate limiting (configurable, default: 60 requests/minute)
- ✅ Input validation (prevents JSON bomb attacks)
- ✅ Sanitized error messages (prevents information disclosure)
- ✅ Replay attack prevention (5-minute timestamp window)
- ✅ Debug mode disabled by default

**When to use:** Self-hosted servers directly exposed to internet (no ngrok tunnel), or when you need application-level rate limiting

**Why HMAC in the app?** When your server is directly accessible from the internet (not behind ngrok), you need to validate Slack signatures at the application level. This cryptographically verifies that requests actually come from Slack, preventing anyone from sending fake approval requests.

### Setup

```bash
# 1. Get your Slack signing secret
# Go to: https://api.slack.com/apps → Your App → Basic Information → Signing Secret

# 2. Set environment variables
export SLACK_BOT_TOKEN=xoxb-your-token-here
export SLACK_SIGNING_SECRET=your-signing-secret-here
export ENABLE_SLACK=true
export SECURITY_MODE=production

# 3. Run the webhook server
python examples/unified_webhook_server.py

# 4. Deploy your server
# - Cloud providers: Use your provider's deployment method (AWS, GCP, Azure, etc.)
# - VPS: Run server on your VPS with process manager (systemd, supervisor, etc.)
# - Ensure server is accessible via HTTPS (required by Slack)
# - Example URL: https://your-domain.com or https://your-server-ip:3000

# 5. Configure in Slack
# Go to: https://api.slack.com/apps → Your App → Interactivity & Shortcuts
# Set Request URL: https://your-domain.com/slack/interactive
```

**How HMAC verification works:** Your application validates Slack's cryptographic signature on every request. Only requests with valid signatures (proving they came from Slack) are processed. Invalid requests are rejected with a 401 error.

## Configuration Reference

| Environment Variable | Web Service (ngrok) | Self-Hosted | Default | Description |
|---------------------|---------------------|-------------|---------|-------------|
| `SLACK_BOT_TOKEN` | Required | Required | - | Your Slack bot token |
| `SECURITY_MODE` | `local` | `production` | `local` | Security mode |
| `SLACK_SIGNING_SECRET` | For ngrok policy* | Required | - | Slack signing secret |
| `PORT` | Optional | Optional | `3000` | Webhook server port |
| `DEBUG` | Optional | Not recommended | `false` | Flask debug mode |
| `RATE_LIMIT_MAX_REQUESTS` | N/A | Optional | `60` | Max requests per window |
| `RATE_LIMIT_WINDOW_SECONDS` | N/A | Optional | `60` | Rate limit window (seconds) |

\* For web service hosted (ngrok): Secret goes in ngrok traffic policy file, not environment variable

## Security Best Practices

### For All Deployments

1. **Always use signature verification** - Either ngrok traffic policy OR application-level HMAC (production mode)
2. **Always use HTTPS** - ngrok provides this automatically; self-hosted requires SSL certificate
3. **Never commit secrets** - Use environment variables or secure secret management
4. **Restrict Slack bot permissions** - Only grant necessary OAuth scopes (`chat:write`, `channels:read`, etc.)
5. **Rotate secrets regularly** - Update `SLACK_SIGNING_SECRET` periodically (Slack recommends every few months)

### For Web Service Hosted (ngrok)

6. **Use traffic policy verification** - Blocks invalid requests before they reach your app
7. **Monitor ngrok verification quota** - Free tier: 500/month, upgrade if needed
8. **Secure your ngrok config** - Don't commit `ngrok-slack-policy.yml` with secrets

### For Self-Hosted

9. **Enable production mode** - Set `SECURITY_MODE=production` for HMAC verification
10. **Monitor webhook logs** - Watch for invalid signatures, rate limit hits
11. **Adjust rate limits as needed** - Tune `RATE_LIMIT_MAX_REQUESTS` based on usage
12. **Use reverse proxy** - nginx or similar for HTTPS termination and additional security

**Why NOT IP allowlisting:** Slack uses dynamic AWS IPs that change frequently; use signature verification instead

## Troubleshooting

### ngrok: "Invalid signature" errors

- Verify signing secret in `ngrok-slack-policy.yml` matches your Slack app
- Check Slack app: Basic Information → Signing Secret
- Ensure ngrok is started with `--traffic-policy-file` flag
- Test without policy first to isolate issue

### Self-hosted: "Invalid signature" errors

- Verify `SLACK_SIGNING_SECRET` environment variable matches your Slack app
- Check Slack app configuration: Basic Information → Signing Secret
- Ensure you're using the signing secret, NOT the client secret
- Verify `SECURITY_MODE=production` is set

### "Rate limit exceeded" errors (self-hosted only)

- Default: 60 requests per 60 seconds per IP address
- This is normal if you're clicking approve/reject rapidly during testing
- To adjust limits, set environment variables:
  - `RATE_LIMIT_MAX_REQUESTS=120` (increase max requests)
  - `RATE_LIMIT_WINDOW_SECONDS=60` (time window in seconds)
- Rate limiting only applies in production mode

### Webhook not receiving requests

- Test ngrok URL: `curl https://your-ngrok-url.ngrok.io/health`
- Check Slack app configuration: Request URL must be `https://your-ngrok-url.ngrok.io/slack/interactive`
- Verify bot is installed to workspace
- Check webhook server logs for errors

### "Invalid approval_id format" warnings

- The webhook automatically blocks suspicious approval IDs (prevents path traversal)
- This is a security feature - if you see this, someone may be attempting an attack
- Valid approval IDs contain only: letters, numbers, hyphens, underscores
