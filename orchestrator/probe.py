#!/usr/bin/env python3
"""
Throwaway sanity check: submit ONE small job using the same template machinery
the orchestrator will use, poll until it finishes.

Usage:
    UCLOUD_TOKEN=<token> python probe.py [path-to-batch-script]

If no batch script path is given, it uses test.sh (must already exist on UCloud
at /1096288/Jobs/benchmark/ucloud-benchmark/test.sh).
"""
from __future__ import annotations
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl.create_default_context()
from pathlib import Path

HERE = Path(__file__).parent
TEMPLATE_SPEC = HERE / "template-spec.json"
UCLOUD_BASE = "https://cloud.sdu.dk"
FINAL_STATES = {"SUCCESS", "FAILURE", "CANCELED", "EXPIRED"}


def api(method: str, path: str, token: str, body: dict | None = None) -> dict:
    url = UCLOUD_BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            text = r.read().decode()
    except urllib.error.HTTPError as e:
        text = e.read().decode()
        raise RuntimeError(f"HTTP {e.code} on {method} {path}: {text}") from e
    return json.loads(text) if text else {}


def main() -> None:
    token = os.environ.get("UCLOUD_TOKEN", "").strip()
    if not token:
        sys.exit("Set UCLOUD_TOKEN env var.")
    if not TEMPLATE_SPEC.exists():
        sys.exit(f"Missing {TEMPLATE_SPEC}")

    batch_path = sys.argv[1] if len(sys.argv) > 1 else \
        "/1096288/Jobs/benchmark/ucloud-benchmark/test.sh"

    spec = json.loads(TEMPLATE_SPEC.read_text())
    spec["name"] = f"probe-{int(time.time())}"
    spec["parameters"]["batchScript"]["path"] = batch_path
    spec["allowDuplicateJob"] = True

    print(f"Submitting probe job pointing to {batch_path}")
    resp = api("POST", "/api/jobs", token, {"items": [spec], "type": "bulk"})
    job_id = resp["responses"][0]["id"]
    print(f"  job_id = {job_id}")
    print(f"  view at {UCLOUD_BASE}/app/jobs/properties/{job_id}")

    while True:
        s = api("GET", f"/api/jobs/retrieve?id={job_id}", token).get("status", {}).get("state")
        print(f"[{time.strftime('%H:%M:%S')}] state = {s}")
        if s in FINAL_STATES:
            break
        time.sleep(10)
    print("done.")


if __name__ == "__main__":
    main()
