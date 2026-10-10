"""CS2 MarketUZ Mini App API (lokal MVP).

Ishga tushirish: MINIAPP_DEV_MODE=1 python api_server.py
Productionda Telegram initData tekshiruvi majburiy bo‘ladi.
"""
import asyncio
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from urllib.parse import parse_qsl

from aiohttp import ClientSession, web
import aiosqlite

import config as cfg
import db
import market

ROOT = Path(__file__).parent
DEV_MODE = os.getenv("MINIAPP_DEV_MODE", "1") == "1"
HOST = os.getenv("MINIAPP_HOST", "127.0.0.1")
PORT = int(os.getenv("MINIAPP_PORT", "8080"))
MARKET_TEST_MODE = os.getenv("MARKETPLACE_TEST_MODE", "1") == "1"


def verify_init_data(raw: str, bot_token: str, max_age: int = 86400) -> dict | None:
    """Telegram WebApp initData HMAC-SHA256 tekshiruvi."""
    if not raw or not bot_token:
        return None
    pairs = dict(parse_qsl(raw, keep_blank_values=True))
    received = pairs.pop("hash", None)
    if not received:
        return None
    try:
        auth_date = int(pairs.get("auth_date", "0") or 0)
    except ValueError:
        return None
    if not auth_date or time.time() - auth_date > max_age:
        return None
    check = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        return None
    try:
        user = json.loads(pairs.get("user", "{}"))
    except json.JSONDecodeError:
        return None
    return user if user.get("id") else None


async def current_user(request: web.Request) -> dict | None:
    user = verify_init_data(request.headers.get("X-Telegram-Init-Data", ""), cfg.BOT_TOKEN)
    if user:
        await db.touch_user(int(user["id"]))
        return user
    if DEV_MODE:
        demo_id = request.headers.get("X-Demo-User-Id", os.getenv("MINIAPP_DEV_USER_ID", "0"))
        try:
            demo_id = int(demo_id)
        except ValueError:
            demo_id = 0
        return {"id": demo_id, "first_name": "Demo"}
    return None


def skin_json(name: str) -> dict:
    item = market.ITEMS[name]
    return {"id": market.short_id(name), "name": name, "image": market.find_image(name),
            "price": item.get("min_price"), "median": item.get("median_price"),
            "best_source": "Skinport", "change_24h": None, "steam": None}


async def auth(request: web.Request) -> dict:
    user = await current_user(request)
    if not user:
        raise web.HTTPUnauthorized(text="Telegram authentication required")
    return user


async def health(request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "market_items": len(market.ITEMS), "dev_mode": DEV_MODE})


async def skins(request: web.Request) -> web.Response:
    await auth(request)
    q = request.query.get("q", "").strip().lower()
    category = request.query.get("category", "all")
    if category in {"weapons", "rifles", "pistols", "knives", "gloves", "stickers", "cases"} and not q:
        mapping = {"knives": ("k", "x"), "gloves": ("g", "x"), "stickers": ("s", "x"), "cases": ("c", "x")}
        if category in mapping:
            names = market.category_items(*mapping[category])
        elif category == "rifles":
            names = market.category_items("w", "0.0") + market.category_items("w", "0.1")
        elif category == "pistols":
            names = market.category_items("w", "2.0") + market.category_items("w", "2.1")
        else:
            names = market.category_items("w", "0.0")
        names = market.sort_names(names, "q")[:40]
    else:
        names = market.search(q, 40) if q else sorted(market.ITEMS, key=lambda n: market.ITEMS[n].get("quantity") or 0, reverse=True)[:40]
    return web.json_response({"items": [skin_json(n) for n in names]})


async def categories(request: web.Request) -> web.Response:
    await auth(request)
    return web.json_response({"categories": [
        {"id": "all", "title": "Barchasi"}, {"id": "rifles", "title": "Rifles"},
        {"id": "pistols", "title": "Pistols"}, {"id": "knives", "title": "Pichoqlar"},
        {"id": "gloves", "title": "Qo‘lqoplar"}, {"id": "stickers", "title": "Stickers"},
        {"id": "cases", "title": "Case’lar"},
    ]})


async def skin_detail(request: web.Request) -> web.Response:
    await auth(request)
    name = market.IDS.get(request.match_info["sid"])
    if not name or name not in market.ITEMS:
        raise web.HTTPNotFound(text="Skin not found")
    item = skin_json(name)
    steam, dmarket, csfloat, rate = await asyncio.gather(
        market.steam_price(name), market.dmarket_price(name),
        market.csfloat_price(name), market.get_usd_uzs())
    current = item.get("price")
    old = await db.price_at(name, int(time.time()) - 86400)
    item.update({"steam": steam, "dmarket": dmarket, "csfloat": csfloat,
                 "usd_uzs": rate, "price_uzs": round(current * rate) if current and rate else None,
                 "change_24h": round((current / old - 1) * 100, 2) if current and old else None})
    return web.json_response(item)


async def skin_chart(request: web.Request) -> web.Response:
    await auth(request)
    name = market.IDS.get(request.match_info["sid"])
    if not name or name not in market.ITEMS:
        raise web.HTTPNotFound(text="Skin not found")
    points = await db.get_history(name, 30)
    if len(points) < 2:
        raise web.HTTPNotFound(text="Not enough chart data")
    png = await asyncio.to_thread(market.make_chart, name, points)
    return web.Response(body=png, content_type="image/png", headers={"Cache-Control": "no-store"})


async def favorites(request: web.Request) -> web.Response:
    user = await auth(request)
    uid = int(user["id"])
    if request.method == "GET":
        names = [n for n in await db.list_favs(uid) if n in market.ITEMS]
        return web.json_response({"items": [skin_json(n) for n in names]})
    data = await request.json()
    name = market.IDS.get(str(data.get("skin_id", "")))
    if not name:
        raise web.HTTPBadRequest(text="Unknown skin")
    if request.method == "POST":
        added = await db.toggle_fav(uid, name)
        return web.json_response({"name": name, "favorite": added})
    if await db.is_fav(uid, name):
        await db.toggle_fav(uid, name)
    return web.json_response({"name": name, "favorite": False})


async def alerts(request: web.Request) -> web.Response:
    user = await auth(request)
    uid = int(user["id"])
    if request.method == "GET":
        rows = await db.list_alerts(uid)
        return web.json_response({"items": [{"id": aid, "name": name, "target": target, "direction": direction} for aid, name, target, direction in rows]})
    if request.method == "POST":
        if await db.count_alerts(uid) >= cfg.MAX_ALERTS_PER_USER:
            raise web.HTTPBadRequest(text="Alert limit reached")
        data = await request.json()
        name = market.IDS.get(str(data.get("skin_id", "")))
        direction = str(data.get("direction", "below"))
        try:
            target = float(data.get("target"))
        except (TypeError, ValueError):
            raise web.HTTPBadRequest(text="Invalid target")
        if not name or direction not in {"below", "above"} or target <= 0:
            raise web.HTTPBadRequest(text="Invalid alert")
        await db.add_alert(uid, name, round(target, 2), direction)
        return web.json_response({"ok": True, "name": name, "target": round(target, 2), "direction": direction})
    data = await request.json()
    await db.delete_alert(int(data.get("id", 0)), uid)
    return web.json_response({"ok": True})


async def profile(request: web.Request) -> web.Response:
    user = await auth(request)
    uid = int(user["id"])
    is_admin = bool(MARKET_TEST_MODE or (cfg.ADMIN_ID and uid == cfg.ADMIN_ID))
    return web.json_response({"user": user, "favorites": await db.count_favs(uid), "alerts": await db.count_alerts(uid), "tracked": len(await db.tracked_names()), "is_admin": is_admin})


async def admin_auth(request: web.Request) -> dict:
    user = await auth(request)
    if not (MARKET_TEST_MODE or (cfg.ADMIN_ID and int(user["id"]) == cfg.ADMIN_ID)):
        raise web.HTTPForbidden(text="Admin access required")
    return user


async def admin_overview(request: web.Request) -> web.Response:
    await admin_auth(request)
    async with aiosqlite.connect(cfg.DB_PATH) as con:
        result = {}
        for key, table in (("listings", "listings"), ("orders", "orders"), ("payments", "payments"), ("payouts", "payout_requests"), ("audit", "audit_log")):
            result[key] = (await (await con.execute(f"SELECT COUNT(*) FROM {table}")).fetchone())[0]
        result["active_listings"] = (await (await con.execute("SELECT COUNT(*) FROM listings WHERE status='active' AND moderation_status='approved'")).fetchone())[0]
        result["open_orders"] = (await (await con.execute("SELECT COUNT(*) FROM orders WHERE status NOT IN ('delivered','refunded','cancelled')")).fetchone())[0]
    return web.json_response(result)


async def admin_listings(request: web.Request) -> web.Response:
    await admin_auth(request)
    async with aiosqlite.connect(cfg.DB_PATH) as con:
        cur = await con.execute("SELECT id,seller_id,market_hash_name,price_usd,status,ownership_verified,moderation_status FROM listings ORDER BY id DESC LIMIT 200")
        rows = await cur.fetchall()
    return web.json_response({"items": [{"id":i,"seller_id":s,"name":n,"price":p,"status":st,"ownership_verified":bool(v),"moderation_status":m} for i,s,n,p,st,v,m in rows]})


async def admin_orders(request: web.Request) -> web.Response:
    await admin_auth(request)
    async with aiosqlite.connect(cfg.DB_PATH) as con:
        cur = await con.execute("SELECT id,listing_id,buyer_id,seller_id,amount_usd,status,created_at,updated_at FROM orders ORDER BY id DESC LIMIT 200")
        rows = await cur.fetchall()
    return web.json_response({"items": [{"id":i,"listing_id":l,"buyer_id":b,"seller_id":s,"amount":a,"status":st,"created_at":c,"updated_at":u} for i,l,b,s,a,st,c,u in rows]})


async def market_listings(request: web.Request) -> web.Response:
    user = await current_user(request)
    if not user:
        raise web.HTTPUnauthorized(text="Telegram authentication required")
    if request.method == "GET":
        async with aiosqlite.connect(cfg.DB_PATH) as con:
            cur = await con.execute("SELECT id,seller_id,market_hash_name,price_usd,status,ownership_verified,moderation_status FROM listings WHERE status='active' AND moderation_status='approved' ORDER BY id DESC LIMIT 100")
            rows = await cur.fetchall()
        return web.json_response({"items": [{"id": i, "seller_id": s, "name": n, "price": p, "status": st, "ownership_verified": bool(v), "moderation_status": m} for i,s,n,p,st,v,m in rows]})
    data = await request.json()
    name = market.IDS.get(str(data.get("skin_id", ""))) or str(data.get("market_hash_name", ""))
    try:
        price = float(data.get("price"))
    except (TypeError, ValueError):
        raise web.HTTPBadRequest(text="Invalid price")
    if not name or price <= 0:
        raise web.HTTPBadRequest(text="Skin and positive price required")
    steamid = str(data.get("steam_id", "")).strip()
    verified = 0
    if steamid and not MARKET_TEST_MODE:
        resolved = await market.resolve_steamid(steamid)
        if not resolved:
            raise web.HTTPBadRequest(text="Steam profile not found")
        counts, state = await market.fetch_inventory(resolved)
        if state != "ok" or not counts or not counts.get(name):
            raise web.HTTPBadRequest(text="Skin not found in public Steam inventory")
        steamid, verified = resolved, 1
    status = "active" if MARKET_TEST_MODE else "draft"
    moderation = "approved" if MARKET_TEST_MODE else "pending"
    now = int(time.time())
    async with aiosqlite.connect(cfg.DB_PATH) as con:
        cur = await con.execute("INSERT INTO listings(seller_id,market_hash_name,asset_id,seller_steamid,ownership_verified,moderation_status,price_usd,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (int(user["id"]), name, str(data.get("asset_id", "")), steamid, verified, moderation, price, status, now, now))
        listing_id = cur.lastrowid
        await con.execute("INSERT INTO audit_log(actor_id,entity_type,entity_id,action,payload,created_at) VALUES(?,?,?,?,?,?)", (int(user["id"]), "listing", listing_id, "created", json.dumps({"name": name, "price": price}), now))
        await con.commit()
    return web.json_response({"ok": True, "id": listing_id, "name": name, "price": price, "status": status, "moderation_status": moderation, "ownership_verified": bool(verified)})


async def moderate_listing(request: web.Request) -> web.Response:
    user = await auth(request)
    if not (MARKET_TEST_MODE or (cfg.ADMIN_ID and int(user["id"]) == cfg.ADMIN_ID)):
        raise web.HTTPForbidden(text="Admin access required")
    action = (await request.json()).get("action")
    if action not in {"approve", "reject"}:
        raise web.HTTPBadRequest(text="Invalid moderation action")
    moderation = "approved" if action == "approve" else "rejected"
    status = "active" if action == "approve" else "cancelled"
    async with aiosqlite.connect(cfg.DB_PATH) as con:
        await con.execute("UPDATE listings SET moderation_status=?,status=?,updated_at=? WHERE id=?", (moderation, status, int(time.time()), int(request.match_info["lid"])))
        await con.commit()
    return web.json_response({"ok": True, "moderation_status": moderation, "status": status})


async def market_orders(request: web.Request) -> web.Response:
    user = await auth(request)
    uid = int(user["id"])
    if request.method == "GET":
        async with aiosqlite.connect(cfg.DB_PATH) as con:
            cur = await con.execute("SELECT id,listing_id,buyer_id,seller_id,amount_usd,status FROM orders WHERE buyer_id=? OR seller_id=? ORDER BY id DESC", (uid, uid))
            rows = await cur.fetchall()
        return web.json_response({"items": [{"id": i, "listing_id": l, "buyer_id": b, "seller_id": s, "amount": a, "status": st} for i,l,b,s,a,st in rows]})
    data = await request.json()
    listing_id = int(data.get("listing_id", 0))
    async with aiosqlite.connect(cfg.DB_PATH) as con:
        cur = await con.execute("SELECT seller_id,price_usd,status FROM listings WHERE id=?", (listing_id,))
        listing = await cur.fetchone()
        if not listing or listing[2] != "active" or listing[0] == uid:
            raise web.HTTPBadRequest(text="Listing unavailable")
        now = int(time.time())
        cur = await con.execute("INSERT INTO orders(listing_id,buyer_id,seller_id,amount_usd,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", (listing_id, uid, listing[0], listing[1], "created", now, now))
        order_id = cur.lastrowid
        await con.execute("UPDATE listings SET status='reserved',updated_at=? WHERE id=?", (now, listing_id))
        await con.execute("INSERT INTO audit_log(actor_id,entity_type,entity_id,action,payload,created_at) VALUES(?,?,?,?,?,?)", (uid, "order", order_id, "created", json.dumps({"listing_id": listing_id}), now))
        await con.commit()
    return web.json_response({"ok": True, "id": order_id, "status": "created", "amount": listing[1]})


async def market_order_status(request: web.Request) -> web.Response:
    user = await auth(request)
    uid = int(user["id"])
    data = await request.json()
    new_status = str(data.get("status", ""))
    allowed = {"created": {"paid", "cancelled"}, "paid": {"awaiting_trade", "refunded"}, "awaiting_trade": {"delivered", "disputed"}, "disputed": {"refunded"}}
    async with aiosqlite.connect(cfg.DB_PATH) as con:
        cur = await con.execute("SELECT buyer_id,seller_id,status FROM orders WHERE id=?", (int(request.match_info["oid"]),))
        row = await cur.fetchone()
        if not row or uid not in (row[0], row[1]) or new_status not in allowed.get(row[2], set()):
            raise web.HTTPBadRequest(text="Invalid order transition")
        now = int(time.time())
        await con.execute("UPDATE orders SET status=?,updated_at=? WHERE id=?", (new_status, now, int(request.match_info["oid"])))
        if new_status == "delivered":
            amount = (await (await con.execute("SELECT amount_usd FROM orders WHERE id=?", (int(request.match_info["oid"]),))).fetchone())[0]
            exists = await (await con.execute("SELECT 1 FROM ledger WHERE order_id=? AND kind='seller_credit'", (int(request.match_info["oid"]),))).fetchone()
            if not exists:
                fee = round(amount * cfg.PLATFORM_FEE_PERCENT / 100, 2)
                await con.execute("INSERT INTO ledger(order_id,kind,amount_usd,created_at) VALUES(?,?,?,?)", (int(request.match_info["oid"]), "platform_fee", fee, now))
                await con.execute("INSERT INTO ledger(order_id,kind,amount_usd,created_at) VALUES(?,?,?,?)", (int(request.match_info["oid"]), "seller_credit", round(amount - fee, 2), now))
        await con.execute("INSERT INTO audit_log(actor_id,entity_type,entity_id,action,payload,created_at) VALUES(?,?,?,?,?,?)", (uid, "order", int(request.match_info["oid"]), "status_changed", json.dumps({"from": row[2], "to": new_status}), now))
        await con.commit()
    return web.json_response({"ok": True, "status": new_status})


async def mock_pay_order(request: web.Request) -> web.Response:
    user = await auth(request)
    uid = int(user["id"])
    if not MARKET_TEST_MODE:
        raise web.HTTPNotImplemented(text="Payment provider is not configured")
    oid = int(request.match_info["oid"])
    async with aiosqlite.connect(cfg.DB_PATH) as con:
        cur = await con.execute("SELECT buyer_id,seller_id,amount_usd,status FROM orders WHERE id=?", (oid,))
        row = await cur.fetchone()
        if not row or row[0] != uid or row[3] != "created":
            raise web.HTTPBadRequest(text="Order cannot be paid")
        now = int(time.time())
        cur = await con.execute("INSERT INTO payments(order_id,provider,provider_payment_id,amount_usd,status,created_at) VALUES(?,?,?,?,?,?)", (oid, "mock", f"mock_{oid}_{now}", row[2], "paid", now))
        payment_id = cur.lastrowid
        await con.execute("INSERT INTO ledger(order_id,kind,amount_usd,created_at) VALUES(?,?,?,?)", (oid, "buyer_charge", row[2], now))
        await con.execute("UPDATE orders SET status='paid',updated_at=? WHERE id=?", (now, oid))
        await con.execute("INSERT INTO audit_log(actor_id,entity_type,entity_id,action,payload,created_at) VALUES(?,?,?,?,?,?)", (uid, "order", oid, "mock_payment_paid", json.dumps({"payment_id": payment_id}), now))
        await con.commit()
    return web.json_response({"ok": True, "payment_id": payment_id, "status": "paid", "provider": "mock"})


async def dispute_order(request: web.Request) -> web.Response:
    user = await auth(request)
    uid = int(user["id"])
    oid = int(request.match_info["oid"])
    async with aiosqlite.connect(cfg.DB_PATH) as con:
        cur = await con.execute("SELECT buyer_id,seller_id,status FROM orders WHERE id=?", (oid,))
        row = await cur.fetchone()
        if not row or uid not in (row[0], row[1]) or row[2] not in {"paid", "awaiting_trade"}:
            raise web.HTTPBadRequest(text="Order cannot be disputed")
        now = int(time.time())
        await con.execute("UPDATE orders SET status='disputed',updated_at=? WHERE id=?", (now, oid))
        await con.execute("INSERT INTO audit_log(actor_id,entity_type,entity_id,action,payload,created_at) VALUES(?,?,?,?,?,?)", (uid, "order", oid, "disputed", None, now))
        await con.commit()
    return web.json_response({"ok": True, "status": "disputed"})


async def refund_order(request: web.Request) -> web.Response:
    user = await admin_auth(request)
    oid = int(request.match_info["oid"])
    async with aiosqlite.connect(cfg.DB_PATH) as con:
        cur = await con.execute("SELECT amount_usd,status FROM orders WHERE id=?", (oid,))
        row = await cur.fetchone()
        if not row or row[1] not in {"paid", "disputed", "awaiting_trade"}:
            raise web.HTTPBadRequest(text="Order cannot be refunded")
        now = int(time.time())
        await con.execute("INSERT INTO payments(order_id,provider,provider_payment_id,amount_usd,status,created_at) VALUES(?,?,?,?,?,?)", (oid, "mock", f"refund_{oid}_{now}", row[0], "refunded", now))
        await con.execute("INSERT INTO ledger(order_id,kind,amount_usd,created_at) VALUES(?,?,?,?)", (oid, "refund", row[0], now))
        await con.execute("UPDATE orders SET status='refunded',updated_at=? WHERE id=?", (now, oid))
        await con.execute("INSERT INTO audit_log(actor_id,entity_type,entity_id,action,payload,created_at) VALUES(?,?,?,?,?,?)", (int(user["id"]), "order", oid, "refunded", None, now))
        await con.commit()
    return web.json_response({"ok": True, "status": "refunded"})


async def seller_balance(request: web.Request) -> web.Response:
    user = await auth(request)
    uid = int(user["id"])
    async with aiosqlite.connect(cfg.DB_PATH) as con:
        cur = await con.execute("SELECT COALESCE(SUM(l.amount_usd),0) FROM ledger l JOIN orders o ON o.id=l.order_id WHERE o.seller_id=? AND l.kind='seller_credit'", (uid,))
        credited = float((await cur.fetchone())[0])
        cur = await con.execute("SELECT COALESCE(SUM(l.amount_usd),0) FROM ledger l JOIN orders o ON o.id=l.order_id WHERE o.seller_id=? AND l.kind='refund'", (uid,))
        refunded = float((await cur.fetchone())[0])
        cur = await con.execute("SELECT COALESCE(SUM(amount_usd),0) FROM payout_requests WHERE seller_id=? AND status IN ('approved','paid')", (uid,))
        paid_out = float((await cur.fetchone())[0])
    return web.json_response({"seller_id": uid, "credited": round(credited, 2), "refunded": round(refunded, 2), "paid_out": round(paid_out, 2), "available": round(credited - refunded - paid_out, 2), "currency": "USD"})


async def payout_requests(request: web.Request) -> web.Response:
    user = await auth(request); uid = int(user["id"])
    if request.method == "GET":
        async with aiosqlite.connect(cfg.DB_PATH) as con:
            cur = await con.execute("SELECT id,amount_usd,status,created_at,updated_at FROM payout_requests WHERE seller_id=? ORDER BY id DESC", (uid,))
            rows = await cur.fetchall()
        return web.json_response({"items": [{"id":i,"amount":a,"status":s,"created_at":c,"updated_at":u} for i,a,s,c,u in rows]})
    if not MARKET_TEST_MODE:
        raise web.HTTPNotImplemented(text="Payout provider is not configured")
    amount = float((await request.json()).get("amount", 0))
    async with aiosqlite.connect(cfg.DB_PATH) as con:
        credited = float((await (await con.execute("SELECT COALESCE(SUM(l.amount_usd),0) FROM ledger l JOIN orders o ON o.id=l.order_id WHERE o.seller_id=? AND l.kind='seller_credit'", (uid,))).fetchone())[0])
        paid_out = float((await (await con.execute("SELECT COALESCE(SUM(amount_usd),0) FROM payout_requests WHERE seller_id=? AND status IN ('approved','paid')", (uid,))).fetchone())[0])
    if amount <= 0 or amount > round(credited - paid_out, 2):
        raise web.HTTPBadRequest(text="Insufficient seller balance")
    now = int(time.time())
    async with aiosqlite.connect(cfg.DB_PATH) as con:
        cur = await con.execute("INSERT INTO payout_requests(seller_id,amount_usd,status,created_at,updated_at) VALUES(?,?,?,?,?)", (uid, round(amount,2), "pending", now, now))
        pid = cur.lastrowid; await con.commit()
    return web.json_response({"ok": True, "id": pid, "status": "pending", "amount": round(amount,2)})


async def admin_payouts(request: web.Request) -> web.Response:
    await admin_auth(request)
    async with aiosqlite.connect(cfg.DB_PATH) as con:
        cur = await con.execute("SELECT id,seller_id,amount_usd,status,created_at FROM payout_requests ORDER BY id DESC LIMIT 200")
        rows = await cur.fetchall()
    return web.json_response({"items": [{"id":i,"seller_id":s,"amount":a,"status":st,"created_at":c} for i,s,a,st,c in rows]})


async def decide_payout(request: web.Request) -> web.Response:
    user = await admin_auth(request); action = (await request.json()).get("action")
    if action not in {"approve", "reject"}: raise web.HTTPBadRequest(text="Invalid payout action")
    status = "approved" if action == "approve" else "rejected"; pid = int(request.match_info["pid"])
    async with aiosqlite.connect(cfg.DB_PATH) as con:
        await con.execute("UPDATE payout_requests SET status=?,updated_at=? WHERE id=? AND status='pending'", (status, int(time.time()), pid))
        await con.execute("INSERT INTO audit_log(actor_id,entity_type,entity_id,action,payload,created_at) VALUES(?,?,?,?,?,?)", (int(user["id"]), "payout", pid, action, None, int(time.time())))
        await con.commit()
    return web.json_response({"ok": True, "status": status})


async def create_trade(request: web.Request) -> web.Response:
    user = await auth(request); uid = int(user["id"]); oid = int(request.match_info["oid"])
    async with aiosqlite.connect(cfg.DB_PATH) as con:
        row = await (await con.execute("SELECT buyer_id,seller_id,status FROM orders WHERE id=?", (oid,))).fetchone()
        if not row or uid not in (row[0], row[1]) or row[2] not in {"paid", "awaiting_trade"}: raise web.HTTPBadRequest(text="Trade cannot be created")
        now = int(time.time()); cur = await con.execute("INSERT INTO trades(order_id,steam_offer_id,status,created_at,updated_at) VALUES(?,?,?,?,?)", (oid, f"mock_offer_{oid}_{now}", "sent", now, now)); tid = cur.lastrowid
        await con.execute("UPDATE orders SET status='awaiting_trade',updated_at=? WHERE id=?", (now, oid)); await con.commit()
    return web.json_response({"ok": True, "trade_id": tid, "status": "sent", "provider": "mock"})


async def accept_trade(request: web.Request) -> web.Response:
    user = await auth(request); uid = int(user["id"]); tid = int(request.match_info["tid"])
    async with aiosqlite.connect(cfg.DB_PATH) as con:
        row = await (await con.execute("SELECT t.order_id,o.buyer_id,o.seller_id,o.amount_usd,t.status FROM trades t JOIN orders o ON o.id=t.order_id WHERE t.id=?", (tid,))).fetchone()
        if not row or uid not in (row[1], row[2]) or row[4] != "sent": raise web.HTTPBadRequest(text="Trade cannot be accepted")
        now=int(time.time()); fee=round(row[3]*cfg.PLATFORM_FEE_PERCENT/100,2)
        await con.execute("UPDATE trades SET status='accepted',updated_at=? WHERE id=?", (now,tid)); await con.execute("UPDATE orders SET status='delivered',updated_at=? WHERE id=?", (now,row[0]))
        await con.execute("INSERT INTO ledger(order_id,kind,amount_usd,created_at) VALUES(?,?,?,?)", (row[0],"platform_fee",fee,now)); await con.execute("INSERT INTO ledger(order_id,kind,amount_usd,created_at) VALUES(?,?,?,?)", (row[0],"seller_credit",round(row[3]-fee,2),now)); await con.commit()
    return web.json_response({"ok": True, "status": "accepted", "order_status": "delivered"})


async def payment_webhook(request: web.Request) -> web.Response:
    raw = await request.read()
    secret = cfg.PAYMENT_WEBHOOK_SECRET.encode()
    signature = request.headers.get("X-Payment-Signature", "")
    expected = hmac.new(secret, raw, hashlib.sha256).hexdigest() if secret else ""
    if not secret or not hmac.compare_digest(signature, expected):
        raise web.HTTPUnauthorized(text="Invalid webhook signature")
    try:
        data = json.loads(raw.decode("utf-8")); provider_id = str(data["provider_payment_id"]); status = str(data["status"])
    except (ValueError, KeyError, TypeError):
        raise web.HTTPBadRequest(text="Invalid webhook payload")
    if status not in {"paid", "failed", "refunded"}:
        raise web.HTTPBadRequest(text="Unsupported payment status")
    async with aiosqlite.connect(cfg.DB_PATH) as con:
        row = await (await con.execute("SELECT order_id FROM payments WHERE provider_payment_id=?", (provider_id,))).fetchone()
        if not row: raise web.HTTPNotFound(text="Payment not found")
        now = int(time.time()); await con.execute("UPDATE payments SET status=? WHERE provider_payment_id=?", (status, provider_id))
        if status == "paid": await con.execute("UPDATE orders SET status='paid',updated_at=? WHERE id=? AND status='created'", (now,row[0]))
        if status == "refunded": await con.execute("UPDATE orders SET status='refunded',updated_at=? WHERE id=?", (now,row[0]))
        await con.execute("INSERT INTO audit_log(actor_id,entity_type,entity_id,action,payload,created_at) VALUES(?,?,?,?,?,?)", (None, "payment", row[0], f"webhook_{status}", json.dumps({"provider_payment_id":provider_id}), now)); await con.commit()
    return web.json_response({"ok": True, "status": status})


async def create_app() -> web.Application:
    await db.init_db()
    async with aiosqlite.connect(cfg.DB_PATH) as con:
        await con.executescript((ROOT / "marketplace_schema.sql").read_text(encoding="utf-8"))
        for statement in (
            "ALTER TABLE listings ADD COLUMN seller_steamid TEXT",
            "ALTER TABLE listings ADD COLUMN ownership_verified INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE listings ADD COLUMN moderation_status TEXT NOT NULL DEFAULT 'approved'",
        ):
            try:
                await con.execute(statement)
            except aiosqlite.OperationalError:
                pass
        await con.commit()
    app = web.Application()
    app.router.add_get("/", lambda r: web.FileResponse(ROOT / "miniapp/index.html"))
    app.router.add_get("/manus-routes.json", lambda r: web.FileResponse(ROOT / "manus-routes.json"))
    app.router.add_get("/miniapp/{path:.*}", lambda r: web.FileResponse(ROOT / "miniapp" / r.match_info["path"]))
    app.router.add_get("/api/health", health)
    app.router.add_get("/api/skins", skins)
    app.router.add_get("/api/categories", categories)
    app.router.add_get("/api/skins/{sid}", skin_detail)
    app.router.add_get("/api/skins/{sid}/chart", skin_chart)
    app.router.add_get("/api/favorites", favorites)
    app.router.add_post("/api/favorites", favorites)
    app.router.add_delete("/api/favorites", favorites)
    app.router.add_get("/api/alerts", alerts)
    app.router.add_post("/api/alerts", alerts)
    app.router.add_delete("/api/alerts", alerts)
    app.router.add_get("/api/profile", profile)
    app.router.add_get("/api/admin/overview", admin_overview)
    app.router.add_get("/api/admin/listings", admin_listings)
    app.router.add_get("/api/admin/orders", admin_orders)
    app.router.add_get("/api/market/listings", market_listings)
    app.router.add_post("/api/market/listings", market_listings)
    app.router.add_post("/api/market/listings/{lid}/moderate", moderate_listing)
    app.router.add_get("/api/market/orders", market_orders)
    app.router.add_post("/api/market/orders", market_orders)
    app.router.add_post("/api/market/orders/{oid}/status", market_order_status)
    app.router.add_post("/api/market/orders/{oid}/pay", mock_pay_order)
    app.router.add_post("/api/market/orders/{oid}/dispute", dispute_order)
    app.router.add_post("/api/market/orders/{oid}/refund", refund_order)
    app.router.add_get("/api/market/balance", seller_balance)
    app.router.add_get("/api/market/payouts", payout_requests)
    app.router.add_post("/api/market/payouts", payout_requests)
    app.router.add_get("/api/admin/payouts", admin_payouts)
    app.router.add_post("/api/admin/payouts/{pid}/decision", decide_payout)
    app.router.add_post("/api/market/orders/{oid}/trade", create_trade)
    app.router.add_post("/api/market/trades/{tid}/accept", accept_trade)
    app.router.add_post("/api/webhooks/payment/{provider}", payment_webhook)

    session = ClientSession(headers={"User-Agent": "cs2marketuz-miniapp/1.0"})
    market.set_session(session)
    app["session"] = session
    # Render port scan uchun app darhol listen qiladi; katalog yangilanishi fonda bajariladi.
    market.load_items_cache()
    market.load_image_cache()
    if not market.ITEMS:
        await market.load_fallback_items()
    async def warm_market():
        try:
            await market.refresh_items()
            market.load_image_cache()
        except Exception as exc:
            print(f"market refresh skipped: {exc}")
    app["warm_task"] = asyncio.create_task(warm_market())
    async def cleanup(app):
        app["warm_task"].cancel()
        await app["session"].close()
    app.on_cleanup.append(cleanup)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host=HOST, port=PORT)
