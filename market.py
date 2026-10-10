"""Bozor ma'lumotlari: narxlar, rasmlar, kategoriyalar, takliflar, keys EV, inventar, grafik."""
import hashlib
import io
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path

import aiohttp

from config import CSFLOAT_KEY, KEY_PRICE, UZ_TZ

log = logging.getLogger("cs2bot.market")

SKINPORT_URL = "https://api.skinport.com/v1/items"
FALLBACK_SKINS_URL = "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/skins.json"
STEAM_URL = "https://steamcommunity.com/market/priceoverview/"
DMARKET_URL = "https://api.dmarket.com/exchange/v1/market/items"
CSFLOAT_URL = "https://csfloat.com/api/v1/listings"
CBU_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
ER_URL = "https://open.er-api.com/v6/latest/USD"
IMAGE_BASES = [
    "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/",
    "https://bymykel.github.io/CSGO-API/api/en/",
]
IMAGE_FILES = ["skins_not_grouped", "stickers", "crates"]
IMAGE_CACHE_FILE = Path(__file__).with_name("images_cache.json")
ITEMS_CACHE_FILE = Path(__file__).with_name("items_cache.json")

# ---- Xotiradagi kesh ----
ITEMS: dict[str, dict] = {}        # market_hash_name -> Skinport ma'lumoti
LOWER: dict[str, str] = {}
IDS: dict[str, str] = {}           # qisqa id -> nom
IMAGES: dict[str, str] = {}        # nom -> rasm URL
CRATES: dict[str, dict] = {}       # keys nomi -> {"contains": [(nom, rarity)], "rare": [nom]}
BASE_WEARS: dict[str, dict] = {}   # wear'siz nom -> {wear: narx}
STEAM_CACHE: dict[str, tuple] = {}
MARKET_CACHE: dict[tuple, tuple] = {}
FX: dict = {"rate": None, "ts": 0.0, "src": ""}
SESSION: aiohttp.ClientSession | None = None

WEAR_RE = re.compile(r"^(.*) \((Factory New|Minimal Wear|Field-Tested|Well-Worn|Battle-Scarred)\)$")
WEAR_W = {"Factory New": 0.03, "Minimal Wear": 0.24, "Field-Tested": 0.33, "Well-Worn": 0.07, "Battle-Scarred": 0.33}
RARITY_TIERS = [("mil-spec", "Mil-Spec", 0.7992), ("restricted", "Restricted", 0.1598),
                ("classified", "Classified", 0.0320), ("covert", "Covert", 0.0064)]
RARE_PROB = 0.0026


def set_session(s: aiohttp.ClientSession) -> None:
    global SESSION
    SESSION = s


def short_id(name: str) -> str:
    return hashlib.md5(name.encode()).hexdigest()[:10]


# =============== Narx manbalari ===============
async def refresh_items() -> None:
    async with SESSION.get(
        SKINPORT_URL,
        params={"app_id": 730, "currency": "USD", "tradable": 0},
        headers={"Accept-Encoding": "br"},
        timeout=aiohttp.ClientTimeout(total=60),
    ) as r:
        r.raise_for_status()
        data = await r.json()
    items = {i["market_hash_name"]: i for i in data if i.get("min_price") is not None}
    tmp = ITEMS_CACHE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    tmp.replace(ITEMS_CACHE_FILE)
    ITEMS.clear()
    ITEMS.update(items)
    LOWER.clear()
    LOWER.update({n: n.lower() for n in items})
    IDS.clear()
    IDS.update({short_id(n): n for n in items})
    BASE_WEARS.clear()
    for n, it in items.items():
        if n.startswith(("StatTrak™ ", "Souvenir ", "★ StatTrak™ ")):
            continue
        m = WEAR_RE.match(n)
        if m:
            BASE_WEARS.setdefault(m.group(1), {})[m.group(2)] = it["min_price"]
        else:
            BASE_WEARS.setdefault(n, {})["_"] = it["min_price"]
    log.info("Skinport: %d ta skin yangilandi", len(items))


def load_items_cache() -> bool:
    if not ITEMS_CACHE_FILE.exists():
        return False
    try:
        items = json.loads(ITEMS_CACHE_FILE.read_text(encoding="utf-8"))
        if not isinstance(items, dict) or not items:
            return False
        ITEMS.clear(); ITEMS.update(items)
        LOWER.clear(); LOWER.update({n: n.lower() for n in items})
        IDS.clear(); IDS.update({short_id(n): n for n in items})
        BASE_WEARS.clear()
        for n, it in items.items():
            m = WEAR_RE.match(n)
            if m: BASE_WEARS.setdefault(m.group(1), {})[m.group(2)] = it.get("min_price")
            else: BASE_WEARS.setdefault(n, {})["_"] = it.get("min_price")
        log.info("Skin cache yuklandi: %d ta", len(items))
        return True
    except Exception as e:
        log.warning("Skin cache o‘qilmadi: %s", e)
        return False


def _cache_get(source: str, name: str):
    c = MARKET_CACHE.get((source, name))
    if c and time.time() - c[0] < 300:
        return True, c[1]
    return False, None


async def steam_price(name: str) -> float | None:
    cached = STEAM_CACHE.get(name)
    if cached and time.time() - cached[0] < 600:
        return cached[1]
    price = None
    try:
        async with SESSION.get(
            STEAM_URL,
            params={"appid": 730, "currency": 1, "market_hash_name": name},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as r:
            if r.status == 200:
                d = await r.json()
                s = d.get("lowest_price") or d.get("median_price")
                if s:
                    price = float(re.sub(r"[^\d.]", "", s.replace(",", "")))
    except Exception as e:
        log.warning("Steam narxi olinmadi: %s", e)
    STEAM_CACHE[name] = (time.time(), price)
    return price


async def dmarket_price(name: str) -> float | None:
    hit, val = _cache_get("dm", name)
    if hit:
        return val
    price = None
    try:
        async with SESSION.get(
            DMARKET_URL,
            params={"gameId": "a8db", "title": name, "currency": "USD",
                    "orderBy": "price", "orderDir": "asc", "limit": 20},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            if r.status == 200:
                d = await r.json(content_type=None)
                for o in d.get("objects", []):
                    usd = (o.get("price") or {}).get("USD")
                    if o.get("title") == name and usd:
                        price = int(usd) / 100  # sentda keladi
                        break
            else:
                log.warning("DMarket javobi: %s", r.status)
    except Exception as e:
        log.warning("DMarket narxi olinmadi: %s", e)
    MARKET_CACHE[("dm", name)] = (time.time(), price)
    return price


async def csfloat_price(name: str) -> float | None:
    if not CSFLOAT_KEY:
        return None
    hit, val = _cache_get("cf", name)
    if hit:
        return val
    price = None
    try:
        async with SESSION.get(
            CSFLOAT_URL,
            params={"market_hash_name": name, "sort_by": "lowest_price", "limit": 1, "type": "buy_now"},
            headers={"Authorization": CSFLOAT_KEY},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            if r.status == 200:
                d = await r.json(content_type=None)
                rows = d.get("data", []) if isinstance(d, dict) else d
                if rows:
                    price = rows[0]["price"] / 100  # sentda keladi
            else:
                log.warning("CSFloat javobi: %s", r.status)
    except Exception as e:
        log.warning("CSFloat narxi olinmadi: %s", e)
    MARKET_CACHE[("cf", name)] = (time.time(), price)
    return price


async def get_usd_uzs() -> float | None:
    """1 USD necha so'm: avval Markaziy bank, bo'lmasa zaxira manba. 6 soat keshlanadi."""
    if FX["rate"] and time.time() - FX["ts"] < 6 * 3600:
        return FX["rate"]
    rate, src = None, ""
    try:
        async with SESSION.get(CBU_URL, timeout=aiohttp.ClientTimeout(total=10), allow_redirects=True) as r:
            if r.status == 200:
                data = await r.json(content_type=None)
                for row in data:
                    if row.get("Ccy") == "USD":
                        rate, src = float(row["Rate"]), "cbu"
                        break
    except Exception as e:
        log.warning("MB kursi olinmadi: %s", e)
    if not rate:
        try:
            async with SESSION.get(ER_URL, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    d = await r.json(content_type=None)
                    rate, src = float(d["rates"]["UZS"]), "er"
        except Exception as e:
            log.warning("Zaxira kurs olinmadi: %s", e)
    if rate:
        FX.update(rate=rate, ts=time.time(), src=src)
    return FX["rate"]


# =============== Rasmlar va keys ma'lumotlari ===============
def _crate_entry(it: dict) -> dict:
    cont = [(c.get("name"), (c.get("rarity") or {}).get("name", ""))
            for c in it.get("contains", []) if c.get("name")]
    rare = [c.get("name") for c in it.get("contains_rare", []) if c.get("name")]
    return {"contains": cont, "rare": rare}


async def load_images() -> None:
    """Rasm ro'yxati va keys tarkibini ochiq CSGO-API loyihasidan yuklaydi."""
    for f in IMAGE_FILES:
        for base in IMAGE_BASES:
            try:
                async with SESSION.get(f"{base}{f}.json", allow_redirects=True,
                                       timeout=aiohttp.ClientTimeout(total=180)) as r:
                    r.raise_for_status()
                    data = await r.json(content_type=None)
                for it in data:
                    n, img = it.get("market_hash_name"), it.get("image")
                    if n and img:
                        IMAGES[n] = img
                    if f == "crates" and n and n.endswith("Case") and it.get("contains"):
                        CRATES[n] = _crate_entry(it)
                del data
                break
            except Exception as e:
                log.warning("Rasmlar (%s) %s dan yuklanmadi: %s", f, base, e)
    try:
        tmp = IMAGE_CACHE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(IMAGES, ensure_ascii=False), encoding="utf-8")
        tmp.replace(IMAGE_CACHE_FILE)
        log.info("Rasm cache saqlandi: %s", IMAGE_CACHE_FILE)
    except Exception as e:
        log.warning("Rasm cache saqlanmadi: %s", e)
    log.info("Rasmlar: %d ta, keyslar: %d ta", len(IMAGES), len(CRATES))


def load_image_cache() -> bool:
    """API uchun faqat kichik nom->URL mappingini yuklaydi; katta katalogni qayta yuklamaydi."""
    if not IMAGE_CACHE_FILE.exists():
        return False
    try:
        data = json.loads(IMAGE_CACHE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            IMAGES.clear()
            IMAGES.update({str(k): str(v) for k, v in data.items() if v})
            log.info("Rasm cache yuklandi: %d ta", len(IMAGES))
            return bool(IMAGES)
    except Exception as e:
        log.warning("Rasm cache o‘qilmadi: %s", e)
    return False


async def load_fallback_items() -> bool:
    """Skinport vaqtinchalik ishlamasa, narxsiz katalog va rasm nomlarini tiklaydi."""
    try:
        async with SESSION.get(FALLBACK_SKINS_URL, timeout=aiohttp.ClientTimeout(total=45)) as r:
            r.raise_for_status(); data = await r.json(content_type=None)
        items = {}
        for it in data:
            name = it.get("market_hash_name") or it.get("name")
            if name:
                items[name] = {"market_hash_name": name, "min_price": None, "quantity": 0, "image": it.get("image")}
                if it.get("image"): IMAGES[name] = it["image"]
        if not items: return False
        ITEMS.clear(); ITEMS.update(items)
        LOWER.clear(); LOWER.update({n: n.lower() for n in items})
        IDS.clear(); IDS.update({short_id(n): n for n in items})
        ITEMS_CACHE_FILE.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
        log.warning("Fallback katalog yuklandi: %d ta (narxlar vaqtincha yo‘q)", len(items))
        return True
    except Exception as e:
        log.error("Fallback katalog ham yuklanmadi: %s", e)
        return False


def find_image(name: str) -> str | None:
    if name in IMAGES:
        return IMAGES[name]
    return IMAGES.get(name.replace("StatTrak™ ", "").replace("Souvenir ", ""))


# =============== Qidiruv va kategoriyalar ===============
WEAPONS = [
    ("g_rifles", ["AK-47", "M4A4", "M4A1-S", "AUG", "SG 553", "FAMAS", "Galil AR"]),
    ("g_snipers", ["AWP", "SSG 08", "SCAR-20", "G3SG1"]),
    ("g_pistols", ["Glock-18", "USP-S", "P2000", "Desert Eagle", "Five-SeveN", "Tec-9",
                   "CZ75-Auto", "P250", "R8 Revolver", "Dual Berettas"]),
    ("g_smg", ["MP9", "MAC-10", "MP7", "MP5-SD", "UMP-45", "P90", "PP-Bizon"]),
    ("g_heavy", ["Nova", "XM1014", "Sawed-Off", "MAG-7", "M249", "Negev"]),
]
KNIVES = ["Karambit", "Butterfly Knife", "M9 Bayonet", "Bayonet", "Flip Knife", "Gut Knife",
          "Huntsman Knife", "Falchion Knife", "Bowie Knife", "Shadow Daggers", "Navaja Knife",
          "Stiletto Knife", "Talon Knife", "Ursus Knife", "Classic Knife", "Paracord Knife",
          "Survival Knife", "Nomad Knife", "Skeleton Knife", "Kukri Knife"]
GLOVES = ["Sport Gloves", "Specialist Gloves", "Driver Gloves", "Hand Wraps", "Moto Gloves",
          "Bloodhound Gloves", "Hydra Gloves", "Broken Fang Gloves"]


def search(query: str, limit: int = 8) -> list[str]:
    tokens = query.lower().split()
    if not tokens:
        return []
    found = [n for n, low in LOWER.items() if all(t in low for t in tokens)]
    found.sort(key=lambda n: ITEMS[n].get("quantity") or 0, reverse=True)
    return found[:limit]


def base_name(n: str) -> str:
    for p in ("★ ", "StatTrak™ ", "Souvenir "):
        if n.startswith(p):
            n = n[len(p):]
    return n


def matches(name: str, prefix: str) -> bool:
    b = base_name(name)
    return b.startswith(prefix + " | ") or b.split(" (")[0] == prefix


def is_glove(n: str) -> bool:
    return n.startswith("★") and ("Gloves" in n or "Hand Wraps" in n)


def category_items(cat: str, sub: str) -> list[str]:
    names = list(ITEMS)
    if cat == "w":
        gi, wi = map(int, sub.split("."))
        w = WEAPONS[gi][1][wi]
        return [n for n in names if not n.startswith("★") and matches(n, w)]
    if cat == "k":
        out = [n for n in names if n.startswith("★") and not is_glove(n)]
        return out if sub == "x" else [n for n in out if matches(n, KNIVES[int(sub)])]
    if cat == "g":
        out = [n for n in names if is_glove(n)]
        return out if sub == "x" else [n for n in out if matches(n, GLOVES[int(sub)])]
    if cat == "s":
        return [n for n in names if n.startswith("Sticker | ")]
    return [n for n in names if n.endswith(" Case") and " | " not in n]


def sort_names(names: list[str], mode: str) -> list[str]:
    if mode == "a":
        return sorted(names, key=lambda n: ITEMS[n]["min_price"])
    if mode == "d":
        return sorted(names, key=lambda n: ITEMS[n]["min_price"], reverse=True)
    return sorted(names, key=lambda n: ITEMS[n].get("quantity") or 0, reverse=True)


# =============== Eng yaxshi takliflar ===============
def top_deals(limit: int = 10, exclude=()) -> list[tuple[str, float]]:
    """Skinport'da hozirgi narxi o'rtacha narxdan sezilarli past (likvid) skinlar."""
    out = []
    for n, it in ITEMS.items():
        mn, md, q = it.get("min_price"), it.get("median_price"), it.get("quantity") or 0
        if not mn or not md or q < 5 or mn < 2 or n in exclude:
            continue
        dip = 1 - mn / md
        if 0.10 <= dip <= 0.55:
            out.append((dip * min(q, 25) ** 0.5, n, dip))
    out.sort(reverse=True)
    return [(n, dip) for _, n, dip in out[:limit]]


# =============== Keys kalkulyatori ===============
def item_ev_price(name: str) -> float | None:
    w = BASE_WEARS.get(name)
    if not w:
        return None
    if set(w) == {"_"}:
        return w["_"]
    num = den = 0.0
    for wear, p in w.items():
        if wear == "_":
            continue
        num += p * WEAR_W[wear]
        den += WEAR_W[wear]
    return num / den if den else None


def _avg(prices: list) -> float | None:
    prices = [p for p in prices if p]
    return sum(prices) / len(prices) if prices else None


def case_ev(case_name: str) -> dict | None:
    c, it = CRATES.get(case_name), ITEMS.get(case_name)
    if not c or not it:
        return None
    tiers, ev = [], 0.0
    for key, label, prob in RARITY_TIERS:
        names = [n for n, r in c["contains"] if key in r.lower()]
        prices = [item_ev_price(n) for n in names]
        avg = _avg(prices)
        tiers.append({"label": label, "prob": prob, "avg": avg,
                      "found": len([p for p in prices if p]), "total": len(names)})
        if avg:
            ev += prob * avg
    rprices = [item_ev_price(n) for n in c["rare"]]
    ravg = _avg(rprices)
    tiers.append({"label": "★ Rare", "prob": RARE_PROB, "avg": ravg,
                  "found": len([p for p in rprices if p]), "total": len(c["rare"])})
    if ravg:
        ev += RARE_PROB * ravg
    cost = it["min_price"] + KEY_PRICE
    return {"case": it["min_price"], "key": KEY_PRICE, "cost": cost, "ev": ev,
            "ratio": ev / cost * 100 if cost else 0.0, "tiers": tiers}


# =============== Steam inventar ===============
STEAMID_RE = re.compile(r"7656119\d{10}")


async def resolve_steamid(text: str) -> str | None:
    text = text.strip()
    m = STEAMID_RE.search(text)
    if m:
        return m.group(0)
    m = re.search(r"steamcommunity\.com/id/([^/?#\s]+)", text)
    if m:
        vanity = m.group(1)
    elif re.fullmatch(r"[A-Za-z0-9_\-]{2,32}", text):
        vanity = text
    else:
        return None
    try:
        async with SESSION.get(f"https://steamcommunity.com/id/{vanity}/?xml=1",
                               timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status != 200:
                return None
            body = await r.text()
    except Exception as e:
        log.warning("SteamID aniqlanmadi: %s", e)
        return None
    m = re.search(r"<steamID64>(\d+)</steamID64>", body)
    return m.group(1) if m else None


async def fetch_inventory(steamid: str) -> tuple[dict | None, str]:
    """(buyumlar {nom: soni}, holat). Holat: ok / private / rate / error."""
    counts: dict[str, int] = {}
    start = None
    try:
        for _ in range(5):
            params = {"l": "english", "count": 2000}
            if start:
                params["start_assetid"] = start
            async with SESSION.get(f"https://steamcommunity.com/inventory/{steamid}/730/2", params=params,
                                   timeout=aiohttp.ClientTimeout(total=30)) as r:
                if r.status in (401, 403):
                    return None, "private"
                if r.status == 429:
                    return None, "rate"
                if r.status != 200:
                    return None, "error"
                data = await r.json(content_type=None)
            if data is None:
                return None, "private"
            desc = {(d["classid"], d["instanceid"]): d for d in data.get("descriptions", [])}
            for a in data.get("assets", []):
                d = desc.get((a["classid"], a["instanceid"]))
                if d and d.get("market_hash_name"):
                    counts[d["market_hash_name"]] = counts.get(d["market_hash_name"], 0) + int(a.get("amount", 1))
            if data.get("more_items") and data.get("last_assetid"):
                start = data["last_assetid"]
            else:
                break
    except Exception as e:
        log.warning("Inventar olinmadi: %s", e)
        return None, "error"
    return counts, "ok"


def value_inventory(counts: dict) -> tuple[float, list, int]:
    """(jami qiymat, [(qiymat, nom, soni, narx)] kamayish tartibida, narxi topilmagan buyumlar soni)."""
    total, rows, unpriced = 0.0, [], 0
    for name, cnt in counts.items():
        it = ITEMS.get(name)
        if it and it.get("min_price"):
            v = it["min_price"] * cnt
            total += v
            rows.append((v, name, cnt, it["min_price"]))
        else:
            unpriced += cnt
    rows.sort(reverse=True)
    return total, rows, unpriced


# =============== Grafik ===============
def make_chart(name: str, points: list) -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    xs = [datetime.fromtimestamp(ts, UZ_TZ) for ts, _ in points]
    ys = [p for _, p in points]
    fig, ax = plt.subplots(figsize=(8, 4), dpi=110)
    ax.plot(xs, ys, linewidth=2)
    ax.fill_between(xs, ys, min(ys), alpha=0.15)
    ax.set_title(name, fontsize=10)
    ax.set_ylabel("USD")
    ax.grid(alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m %H:%M"))
    fig.autofmt_xdate()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()
