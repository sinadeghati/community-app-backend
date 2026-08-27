#!/usr/bin/env python3
"""Staging QA for admin create-business flow (API-level, no deploy required)."""

from __future__ import annotations

import io
import json
import sys
import uuid
from pathlib import Path

import requests

BASE = "https://community-app-backend-staging.up.railway.app"
ADMIN_USER = "korook_admin_demo"
ADMIN_PASS = "KorookAdminDemo!2026"
OWNER_ID = 9  # staging admin user — separate from businesses 19/20/22


def minimal_png() -> bytes:
    # 1x1 transparent PNG
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
    )


class StagingQa:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.results: list[tuple[str, bool, str]] = []
        self.business_id: int | None = None

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.results.append((name, ok, detail))
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))

    def login(self) -> None:
        csrf = self.session.get(f"{BASE}/api/admin/auth/csrf/").json()["csrfToken"]
        self.session.headers.update({"X-CSRFToken": csrf, "Referer": BASE})
        res = self.session.post(
            f"{BASE}/api/admin/auth/login/",
            json={"username": ADMIN_USER, "password": ADMIN_PASS},
        )
        # Refresh CSRF from session cookie after login.
        cookie_csrf = self.session.cookies.get("csrftoken")
        if cookie_csrf:
            self.session.headers["X-CSRFToken"] = cookie_csrf
        self.add("Admin login", res.status_code == 200, f"HTTP {res.status_code}")

    def create_business(self) -> None:
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "title": f"QA Admin Create {suffix}",
            "business_name": f"QA Test Business {suffix}",
            "description": "Staging QA business — safe to delete",
            "about": "Created by admin create-business QA script",
            "category": "Food",
            "address": "123 QA Test St",
            "city": "San Diego",
            "state": "CA",
            "latitude": 32.7157,
            "longitude": -117.1611,
            "phone": "6195550100",
            "contact_info": "qa-test@korook.com",
            "website": "https://korook.com",
            "instagram": "@korookqa",
            "status": "draft",
            "owner_id": OWNER_ID,
            "is_featured": False,
            "verified_badge": False,
        }
        res = self.session.post(f"{BASE}/api/admin/businesses/", json=payload)
        ok = res.status_code == 201
        if ok:
            self.business_id = res.json()["id"]
        self.add("Create draft business", ok, f"HTTP {res.status_code}, id={self.business_id}")

    def upload_media(self) -> None:
        if not self.business_id:
            self.add("Upload media", False, "No business id")
            return
        png = minimal_png()
        uploads = [
            ("logo", "logo.png"),
            ("cover", "cover.png"),
            ("gallery", "gallery1.png"),
            ("gallery", "gallery2.png"),
        ]
        uploaded = 0
        for role, name in uploads:
            files = {"image": (name, io.BytesIO(png), "image/png")}
            data = {"role": role}
            res = self.session.post(
                f"{BASE}/api/admin/businesses/{self.business_id}/images/",
                files=files,
                data=data,
            )
            if res.status_code == 201:
                uploaded += 1
        self.add("Upload logo/cover/2 gallery", uploaded == 4, f"{uploaded}/4 uploaded")

    def verify_admin_detail(self) -> None:
        if not self.business_id:
            self.add("Verify admin detail", False, "No business id")
            return
        res = self.session.get(f"{BASE}/api/admin/businesses/{self.business_id}/")
        ok = res.status_code == 200
        data = res.json() if ok else {}
        images = data.get("images", [])
        roles = {img.get("role") for img in images if img.get("media_status") == "active"}
        gallery_count = sum(1 for img in images if img.get("role") == "gallery")
        checks = (
            data.get("category") == "Food"
            and data.get("city") == "San Diego"
            and "logo" in roles
            and "cover" in roles
            and gallery_count >= 2
        )
        self.add(
            "Admin detail persists fields/media",
            ok and checks,
            f"category={data.get('category')}, roles={sorted(roles)}, gallery={gallery_count}",
        )

    def publish(self) -> None:
        if not self.business_id:
            self.add("Publish business", False, "No business id")
            return
        res = self.session.post(f"{BASE}/api/admin/businesses/{self.business_id}/publish/")
        self.add("Publish business", res.status_code == 200, f"HTTP {res.status_code}")

    def verify_public_api(self) -> None:
        if not self.business_id:
            self.add("Public API verification", False, "No business id")
            return
        listings = requests.get(f"{BASE}/api/listings/", timeout=30).json()
        match = next((item for item in listings if item.get("id") == self.business_id), None)
        if not match:
            self.add("Public listings includes business", False, "Not found in /api/listings/")
            return
        self.add("Public listings includes business", True, match.get("title", ""))

        detail = requests.get(f"{BASE}/api/listings/{self.business_id}/", timeout=30).json()
        images = detail.get("images", [])
        has_logo = bool(detail.get("logo"))
        has_cover = bool(detail.get("cover_image"))
        gallery_count = sum(1 for img in images if img.get("role") == "gallery")
        ok = (
            detail.get("category") == "Food"
            and detail.get("city") == "San Diego"
            and float(detail.get("latitude") or 0) != 0
            and has_logo
            and has_cover
            and gallery_count >= 2
        )
        self.add(
            "Public detail: category/location/media",
            ok,
            f"category={detail.get('category')}, logo={has_logo}, cover={has_cover}, gallery={gallery_count}",
        )

    def summary(self) -> int:
        failed = [name for name, ok, _ in self.results if not ok]
        print("\n--- QA Summary ---")
        print(f"Business ID: {self.business_id} (temporary QA — not 19/20/22)")
        print(f"Passed: {sum(1 for _, ok, _ in self.results if ok)}/{len(self.results)}")
        if failed:
            print("Failed:", ", ".join(failed))
        report_path = Path(__file__).with_name("staging_create_business_qa_report.json")
        report_path.write_text(
            json.dumps(
                {
                    "business_id": self.business_id,
                    "results": [
                        {"name": name, "ok": ok, "detail": detail}
                        for name, ok, detail in self.results
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Report: {report_path}")
        return 1 if failed else 0


def main() -> int:
    qa = StagingQa()
    print(f"STAGING QA: {BASE}\n")
    qa.login()
    qa.create_business()
    qa.upload_media()
    qa.verify_admin_detail()
    qa.publish()
    qa.verify_public_api()
    return qa.summary()


if __name__ == "__main__":
    sys.exit(main())
