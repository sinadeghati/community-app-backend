# Korook Admin Panel — Phase 1

Develop branch only. No production deployment.

## Backend

- Admin API: `/api/admin/*` (staff session auth)
- App package: **`korook_platform`** (renamed from `platform` to avoid Python stdlib clash)
- Public additive APIs: `/api/events/`, `/api/promotions/`, `/api/hero-slides/`
- Django Admin fallback: `/admin/`

### Create staff user

```bash
cd iranapp
python manage.py createsuperuser
```

## Admin SPA

```bash
cd admin-panel
npm install
npm run dev
```

Proxy targets `http://127.0.0.1:8000` for `/api`.

## Tests

```bash
cd iranapp
python manage.py test korook_admin accounts.tests listings.tests
```
