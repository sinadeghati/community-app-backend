# Korook authentication architecture (pre–social login)

## Mobile / public API

- **Stack:** Django REST Framework + `rest_framework_simplejwt` (JWT access + refresh).
- **User model:** Django `auth.User` (no custom `AUTH_USER_MODEL`).
- **Email gate:** `UserEmailProfile.email_verified` must be true before password login succeeds (`LoginView`).
- **Token issuance:** `RefreshToken.for_user(user)` on successful password login and email verification (code path).
- **Refresh:** `POST /api/token/refresh/` with `{ "refresh": "..." }`.
- **Authorization:** `Authorization: Bearer <access>` on protected routes.

### Account endpoints (`iranapp/accounts/urls.py`)

| Endpoint | Purpose |
|----------|---------|
| `POST /api/accounts/register/` | Create user; sends verification email; **no JWT** |
| `POST /api/accounts/login/` | Password login → JWT |
| `GET /api/accounts/profile/` | JWT profile |
| `POST /api/accounts/email/verify/` | Verify email → JWT (code path) |
| Password reset / change / delete | Unchanged |

### Mobile session (Expo)

- Tokens: `expo-secure-store` (`authTokens_v2`), refresh via `lib/authSession.ts`.
- Guest cold start: `app/index.tsx` → `/(tabs)/map` (`lib/appLaunchRouting.ts`).
- Post password login: `navigateAfterAuthentication()` → Explore or resume business-claim intent (`lib/postAuthNavigation.ts`).
- Protected actions: alerts → `/login` with optional claim params in AsyncStorage.

## Admin API

- Django **session** cookies at `/api/admin/auth/*` (not JWT).

## Social login extension (this feature)

- Mobile sends **provider identity tokens** only; backend verifies signature, issuer, audience, expiry, and nonce (Apple).
- Korook JWT is issued **only after** verification.
- Permanent key: `(provider, provider_subject)` on `ExternalIdentity`.
- **No auto-merge by email**; collisions require password login + authenticated link.
- Staging env vars: see `docs/SOCIAL_AUTH_STAGING_SETUP.md`.
