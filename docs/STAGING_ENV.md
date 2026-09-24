# Staging environment variables

Variables for the **Staging** Railway service (`community-app-backend`) only. Do not set staging-specific reset URLs on production.

## Forgot password (Path A)

The staging backend hosts a minimal reset page at `/reset-password/`. Reset emails must point to that page so users can open the link on mobile and submit the new password to the staging API (same origin).

| Variable | Staging value |
|----------|----------------|
| `FRONTEND_PASSWORD_RESET_URL` | `https://community-app-backend-staging.up.railway.app/reset-password` |

Optional alias (same value if `FRONTEND_PASSWORD_RESET_URL` is unset):

| Variable | Staging value |
|----------|----------------|
| `PASSWORD_RESET_WEB_URL` | `https://community-app-backend-staging.up.railway.app/reset-password` |

## Email (already configured on staging)

| Variable | Example |
|----------|---------|
| `EMAIL_PROVIDER` | `sendgrid` |
| `SENDGRID_API_KEY` | *(secret)* |
| `DEFAULT_FROM_EMAIL` | `Korook <noreply@korook.com>` |

## Apply via Railway CLI

```bash
railway link --project passionate-cat --environment Staging --service community-app-backend

railway variables --set "FRONTEND_PASSWORD_RESET_URL=https://community-app-backend-staging.up.railway.app/reset-password" \
  --service community-app-backend --environment Staging
```

Redeploy the staging service after changing variables.

## Business media (persistent volume)

Listing images are stored on disk under `MEDIA_ROOT`. Railway’s default container filesystem is **ephemeral** — uploads are lost on redeploy unless a volume is mounted.

1. Create and attach a volume (one-time):

```bash
railway link --project passionate-cat --environment Staging --service community-app-backend
railway volume add --service community-app-backend --mount-path /data/media
```

2. Set on the **community-app-backend** Staging service:

| Variable | Value |
|----------|--------|
| `MEDIA_ROOT` | `/data/media` |
| `SERVE_MEDIA` | `1` |

`MEDIA_URL` defaults to `/media/`; public URLs must never include the filesystem path.

After the volume is live, **re-upload** any images whose files were lost before the volume (DB rows may still exist without files on disk).
