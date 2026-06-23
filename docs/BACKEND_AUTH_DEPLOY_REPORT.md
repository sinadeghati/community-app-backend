# Backend auth deploy & test report

**Date:** 2026-06-23  
**Backend repo:** `sinadeghati/community-app-backend`  
**Branch:** `develop` (commit `073815f`)  
**Mobile contract:** `iranianapp-mobile` `lib/authApiContract.ts`

---

## Summary

| Item | Status |
|------|--------|
| Code implemented on `develop` | **Done** |
| Pushed to GitHub `origin/develop` | **Done** |
| Railway CLI deploy | **Blocked** — `railway login` required |
| Staging live deploy | **Not yet** — staging still serves pre-`develop` build |
| Local E2E (full flow) | **Pass** |
| Staging E2E (remote) | **Partial** — mobile paths 404 on current deploy |

---

## Endpoints implemented

| Method | Path | Behavior |
|--------|------|----------|
| `POST` | `/api/accounts/email/verify/` | `{ email, code }` or `{ uid, token }`; returns JWT on success |
| `POST` | `/api/accounts/email/resend/` | Mobile alias; 60s cooldown, max 5/hour |
| `DELETE` | `/api/accounts/delete/` | Mobile alias; authenticated permanent delete |

Register sends a 6-digit code. Login is blocked (403) until verified.

---

## Live probe results

### Staging (current deploy)

| Endpoint | HTTP |
|----------|------|
| `POST /accounts/email/resend/` | 404 |
| `DELETE /accounts/delete/` | 404 |
| `POST /accounts/login/` unverified user | 200 (no gate yet) |

### Local `develop` server

| Step | Result |
|------|--------|
| Register | 201 |
| Login before verify | 403 |
| Verify with code | 200 + tokens |
| Login after verify | 200 |
| Delete account | 200 |

---

## Deploy to Railway

1. `railway login`
2. Link **community-app-backend-staging** service to branch **`develop`**
3. Redeploy (migration `accounts.0002` runs via `railway.toml`)
4. Re-test with `scripts/mobile_auth_e2e.py`
