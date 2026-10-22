#!/usr/bin/env python3
import json
import os
import urllib.error
import urllib.request

BASE = os.getenv("SMOKE_BASE", "http://127.0.0.1:8080").rstrip("/")
HEADERS = {"X-Demo-User-Id": "999"}

def get(path):
    req = urllib.request.Request(BASE + path, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        assert r.status == 200, (path, r.status)
        return json.load(r)

def get_asset(path):
    req = urllib.request.Request(BASE + path, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        assert r.status == 200, (path, r.status)
        return r.headers.get_content_type(), r.read().decode("utf-8")

content_type, page = get_asset("/")
assert content_type == "text/html"
assert '/miniapp/styles.css' in page
for asset in ("app.js", "styles.css", "placeholder.svg"):
    content_type, _ = get_asset(f"/miniapp/{asset}")
    assert content_type != "application/octet-stream", (asset, content_type)
try:
    get_asset("/miniapp/config.py")
    raise AssertionError("non-frontend files must not be served")
except urllib.error.HTTPError as exc:
    assert exc.code == 404, exc.code

health = get("/api/health")
assert health["ok"] is True
assert get("/api/categories")["categories"]
catalog = get("/api/skins")
assert catalog["items"]
assert all("price_uzs" in item for item in catalog["items"])
assert "items" in get("/api/favorites")
assert "items" in get("/api/alerts")
assert "user" in get("/api/profile")
assert "items" in get("/api/market/listings")
assert "items" in get("/api/market/orders")
assert "items" in get("/api/market/payouts")
assert "listings" in get("/api/admin/overview")
print("smoke_test: OK", health)
