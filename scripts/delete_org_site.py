#!/usr/bin/env python3
"""Delete a kem-llc org repo from its live GitHub Pages URL."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from deploy_org_site import github_request  # noqa: E402


def repo_slug_from_live_url(live_url: str, org: str) -> str:
    raw = live_url.strip()
    if not raw:
        raise SystemExit("LIVE_URL is empty")

    # Allow bare repo slug for convenience
    if re.fullmatch(r"[\w.-]+", raw) and "://" not in raw and "/" not in raw:
        return raw

    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").strip("/")

    if not path or path.count("/") > 0:
        raise SystemExit(
            f"Could not parse repo slug from URL: {live_url}\n"
            f"Expected: https://{org}.github.io/{{repo-slug}}/"
        )

    slug = path.split("/")[0]
    expected_host = f"{org.lower()}.github.io"
    if host and host != expected_host:
        print(f"Warning: host is {host}, expected {expected_host} — using slug '{slug}' anyway")

    return slug


def delete_org_repo(org: str, repo: str, token: str) -> None:
    status, body = github_request("DELETE", f"/repos/{org}/{repo}", token)
    if status == 404:
        raise SystemExit(f"Repo not found: {org}/{repo}")
    if status not in {202, 204}:
        message = (body or {}).get("message", body) if isinstance(body, dict) else body
        raise SystemExit(f"Failed to delete {org}/{repo}: HTTP {status} — {message}")
    print(f"Deleted GitHub repo: {org}/{repo}")


def main() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    org = os.environ.get("DEPLOY_ORG", os.environ.get("GITHUB_ORG", "kem-llc"))
    token = os.environ.get("ORG_DEPLOY_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    live_url = os.environ.get("LIVE_URL") or os.environ.get("SITE_URL")
    if not token:
        raise SystemExit("ORG_DEPLOY_TOKEN (or GH_TOKEN) is not set")
    if not live_url:
        raise SystemExit("LIVE_URL is not set")

    repo_slug = repo_slug_from_live_url(live_url, org)
    print(f"Deleting {org}/{repo_slug} (from {live_url})")
    delete_org_repo(org, repo_slug, token)
    print("Done — GitHub Pages URL will stop working after DNS/cache propagates")


if __name__ == "__main__":
    main()
