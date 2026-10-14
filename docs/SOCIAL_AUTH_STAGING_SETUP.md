# Staging Google & Apple sign-in — manual setup checklist

**Staging only.** Do not reuse production OAuth clients or Apple keys on staging without separate IDs.

## Google Cloud

1. Create or select a **Google Cloud project** for Korook staging.
2. **OAuth consent screen** — Internal or External (test users while in testing).
3. Create **OAuth client IDs**:
   - **iOS** — bundle ID `com.korook.app` (staging builds).
   - **Android** — package `com.korook.app` + **SHA-1** from EAS staging/dev keystore (`eas credentials`).
   - **Web** — used as `webClientId` on Android for ID token validation (public client ID, not a secret).
4. **Authorized redirect URIs** — not required for native Google Sign-In ID-token flow.
5. Railway **Staging** backend env:
   - `SOCIAL_AUTH_GOOGLE_CLIENT_IDS` = comma-separated staging iOS, Android, and Web client IDs accepted as token `aud`.

## Apple Developer

1. **App ID** `com.korook.app` — enable **Sign in with Apple**.
2. **EAS / Xcode** — `usesAppleSignIn: true` entitlement (mobile `app.json`).
3. **Services ID** — not required for native iOS Sign in with Apple.
4. Railway **Staging** backend env:
   - `SOCIAL_AUTH_APPLE_CLIENT_IDS` = `com.korook.app`

## Mobile (public IDs in `.env` / EAS)

| Variable | Purpose |
|----------|---------|
| `EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID_STAGING` | iOS `iosClientId` |
| `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID_STAGING` | Android `webClientId` |
| `EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID_PRODUCTION` | Production placeholder |
| `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID_PRODUCTION` | Production placeholder |

**Never** put OAuth client secrets or Apple `.p8` keys in `EXPO_PUBLIC_*`.

## EAS development build

**Required.** `@react-native-google-signin/google-signin` and `expo-apple-authentication` do **not** work in Expo Go.

`eas build --profile development` or `staging` after setting env vars and Google `iosUrlScheme` plugin (from iOS client ID in `app.config.js`).

## Disconnect / account deletion

- Cannot disconnect the only login method (password or another provider required).
- Account delete cascades `ExternalIdentity` rows.
