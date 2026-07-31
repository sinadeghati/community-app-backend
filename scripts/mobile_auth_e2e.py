"""HTTP integration check for Korook mobile auth contract."""

from __future__ import annotations

import argparse
import os
import sys
import uuid

import requests

DEFAULT_BASE = "https://community-app-backend-staging.up.railway.app/api"


def probe_paths(base_url: str) -> dict[str, int]:
    results: dict[str, int] = {}
    probes = [
        ("POST", f"{base_url}/accounts/email/resend/", {"email": "probe@example.com"}),
        ("POST", f"{base_url}/accounts/email/verify/", {"email": "x@y.com", "code": "000000"}),
        ("DELETE", f"{base_url}/accounts/delete/", None),
    ]
    for method, url, payload in probes:
        try:
            kwargs = {"timeout": 20}
            if payload is not None:
                kwargs["json"] = payload
            response = requests.request(method, url, **kwargs)
            results[url.replace(base_url, "")] = response.status_code
        except requests.RequestException as exc:
            results[url.replace(base_url, "")] = -1
            print(f"ERROR {url}: {exc}")
    return results


def issue_code_via_orm(email: str) -> str:
    import django

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "iranapp"))
    if root not in sys.path:
        sys.path.insert(0, root)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "iranapp.settings")
    django.setup()

    from django.contrib.auth.models import User

    from accounts.models import get_or_create_email_profile
    from accounts.verification_codes import issue_verification_code

    user = User.objects.get(email__iexact=email)
    profile = get_or_create_email_profile(user)
    profile.verification_last_sent_at = None
    profile.verification_sends_in_window = 0
    profile.save(
        update_fields=["verification_last_sent_at", "verification_sends_in_window"]
    )
    return issue_verification_code(profile)


def run_flow(base_url: str, *, use_orm_code: bool) -> int:
    suffix = uuid.uuid4().hex[:10]
    username = f"korook_e2e_{suffix}"
    email = f"{username}@korook-e2e.test"
    password = "KorookE2e!234"
    failures = 0

    print(f"API base: {base_url}")
    print("--- endpoint probes ---")
    for path, code in probe_paths(base_url).items():
        print(f"{path} -> {code}")
        if code == 404:
            failures += 1

    print("--- register ---")
    register = requests.post(
        f"{base_url}/accounts/register/",
        json={"username": username, "email": email, "password": password},
        timeout=30,
    )
    print(f"register -> {register.status_code} {register.text[:200]}")
    if register.status_code != 201:
        failures += 1
        return failures

    print("--- login before verify (expect 403) ---")
    login = requests.post(
        f"{base_url}/accounts/login/",
        json={"email": email, "password": password},
        timeout=30,
    )
    print(f"login -> {login.status_code} {login.text[:200]}")
    if login.status_code != 403:
        failures += 1

    print("--- resend ---")
    resend = requests.post(
        f"{base_url}/accounts/email/resend/",
        json={"email": email},
        timeout=30,
    )
    print(f"resend -> {resend.status_code} {resend.text[:200]}")
    if not use_orm_code and resend.status_code not in (200, 429):
        failures += 1

    if use_orm_code:
        code = issue_code_via_orm(email)
        print(f"issued verification code via local ORM helper: {code}")
    else:
        print("Skipping verify/login/delete success steps without --use-orm-code")
        return failures

    print("--- verify with code ---")
    verify = requests.post(
        f"{base_url}/accounts/email/verify/",
        json={"email": email, "code": code},
        timeout=30,
    )
    print(f"verify -> {verify.status_code} {verify.text[:240]}")
    if verify.status_code != 200 or "access" not in verify.json():
        failures += 1
        return failures

    print("--- login after verify ---")
    login2 = requests.post(
        f"{base_url}/accounts/login/",
        json={"email": email, "password": password},
        timeout=30,
    )
    print(f"login -> {login2.status_code} {login2.text[:200]}")
    if login2.status_code != 200:
        failures += 1
        return failures

    access = login2.json().get("access")
    print("--- delete account ---")
    delete = requests.delete(
        f"{base_url}/accounts/delete/",
        headers={"Authorization": f"Bearer {access}"},
        timeout=30,
    )
    print(f"delete -> {delete.status_code} {delete.text[:200]}")
    if delete.status_code != 200:
        failures += 1

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.environ.get("API_BASE_URL", DEFAULT_BASE))
    parser.add_argument(
        "--use-orm-code",
        action="store_true",
        help="Issue a verification code via local Django ORM (localhost only).",
    )
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    return run_flow(base_url, use_orm_code=args.use_orm_code)


if __name__ == "__main__":
    raise SystemExit(main())
