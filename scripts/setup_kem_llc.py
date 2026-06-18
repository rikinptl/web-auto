#!/usr/bin/env python3
"""Verify kem-llc org access and configure web-auto repo secrets/variables."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

ORG = os.environ.get("DEPLOY_ORG", os.environ.get("GITHUB_ORG", "kem-llc"))
REPO = os.environ.get("SETUP_REPO", "rikinptl/web-auto")


def gh(*args: str) -> str:
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def api_get(path: str, token: str) -> tuple[int, dict | None]:
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"message": raw}
        return exc.code, body


def main() -> None:
    token = os.environ.get("ORG_DEPLOY_TOKEN") or gh("auth", "token")
    status, body = api_get(f"/orgs/{ORG}", token)
    if status != 200:
        msg = (body or {}).get("message", "not found")
        print(f"Org '{ORG}' is not ready yet ({status}: {msg}).")
        print(f"Create it: https://github.com/organizations/plan?organization_name={ORG}")
        print("Use the free plan, then re-run: python scripts/setup_kem_llc.py")
        sys.exit(1)

    print(f"Org OK: {ORG}")

    gh("variable", "set", "DEPLOY_ORG", "--body", ORG, "--repo", REPO)
    print(f"Set repository variable DEPLOY_ORG={ORG} on {REPO}")

    proc = subprocess.run(
        ["gh", "secret", "set", "ORG_DEPLOY_TOKEN", "--body", token, "--repo", REPO],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip())
    print(f"Set repository secret ORG_DEPLOY_TOKEN on {REPO}")

    status, _ = api_get(f"/orgs/{ORG}/repos?per_page=1", token)
    if status != 200:
        print("Warning: token may not have permission to list org repos")
    else:
        print("Token can access org repositories API")

    print("Setup complete. Pipeline will deploy each lead to:")
    print(f"  https://{ORG}.github.io/<business-slug>/")


if __name__ == "__main__":
    main()
