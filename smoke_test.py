#!/usr/bin/env python3
import json
import os
import urllib.request

BASE = os.getenv("SMOKE_BASE", "http://127.0.0.1:8080").rstrip("/")
HEADERS = {"X-Demo-User-Id": "999"}

def get(path):
    req = urllib.request.Request(BASE + path, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        assert r.status == 200, (path, r.status)
        return json.load(r)

health = get("/api/health")
assert health["ok"] is True
assert get("/api/categories")["categories"]
assert "items" in get("/api/favorites")
assert "items" in get("/api/alerts")
assert "user" in get("/api/profile")
assert "items" in get("/api/market/listings")
assert "items" in get("/api/market/orders")
assert "items" in get("/api/market/payouts")
assert "listings" in get("/api/admin/overview")
print("smoke_test: OK", health)
