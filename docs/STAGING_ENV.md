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
