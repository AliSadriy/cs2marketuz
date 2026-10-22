"""
CS2 Skin Narx Boti (asosiy fayl)

Imkoniyatlar: skin qidirish, kategoriyalar, Skinport/DMarket/CSFloat/Steam narxlari,
so'mda narx, 3 til, sevimlilar, signallar (pasayish/oshish), takliflar, narx grafigi,
inventar narxi, keys kalkulyatori, kunlik xabar, kanalga e'lon, statistika.
"""
import asyncio
import html
import logging
import time
from datetime import datetime
from pathlib import Path

import aiohttp
from aiogram import BaseMiddleware, Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BotCommand,
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

import config as cfg
import db
import market
from i18n import t, variants

log = logging.getLogger("cs2bot")
dp = Dispatcher()
BOT_USERNAME = ""
START_BANNER = Path(__file__).with_name("assets") / "cs2marketuz-start.png"


class Form(StatesGroup):
    alert_price = State()
    inventory = State()


class TouchMiddleware(BaseMiddleware):
    """Har bir harakatda foydalanuvchining oxirgi faolligini yangilaydi (statistika uchun)."""

    async def __call__(self, handler, event, data):
        u = getattr(event, "from_user", None)
        if u:
            try:
                await db.touch_user(u.id)
            except Exception as e:
                log.warning("touch_user: %s", e)
        return await handler(event, data)


dp.message.outer_middleware(TouchMiddleware())
dp.callback_query.outer_middleware(TouchMiddleware())


# =============== Yordamchi funksiyalar ===============
def btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def kb(rows: list) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def grid(buttons: list, per_row: int = 2) -> list:
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


def money(x: float | None) -> str:
    return f"${x:,.2f}" if x is not None else "—"


def fmt_uzs(usd: float, rate: float) -> str:
    v = usd * rate
    step = 100 if v < 100_000 else 1000
    v = round(v / step) * step
    return f"{v:,.0f}".replace(",", " ")


def money_uzs(x: float | None, rate: float | None, lang: str) -> str:
    if x is None:
        return "—"
    s = money(x)
    if rate:
        s += f" (≈ {fmt_uzs(x, rate)} {t(lang, 'som')})"
    return s


async def get_lang(uid: int) -> str:
    return await db.get_lang(uid) or "uz"


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    rows = []
    if cfg.MINIAPP_URL:
        rows.append([KeyboardButton(text=t(lang, "btn_app"), web_app=WebAppInfo(url=cfg.MINIAPP_URL))])
    rows += [
            [KeyboardButton(text=t(lang, "btn_search")), KeyboardButton(text=t(lang, "btn_cats"))],
            [KeyboardButton(text=t(lang, "btn_fav")), KeyboardButton(text=t(lang, "btn_alerts"))],
            [KeyboardButton(text=t(lang, "btn_deals")), KeyboardButton(text=t(lang, "btn_more"))],
        ]
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
    )


def lang_kb() -> InlineKeyboardMarkup:
    return kb([[btn("🇺🇿 O'zbekcha", "lg:uz"), btn("🇷🇺 Русский", "lg:ru"), btn("🇬🇧 English", "lg:en")]])


async def safe_edit(c: CallbackQuery, text: str, rows: list) -> None:
    markup = kb(rows)
    try:
        await c.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as e:
        if "not modified" not in str(e):
            await c.message.answer(text, reply_markup=markup)


def is_button(text: str) -> bool:
    keys = ("btn_search", "btn_cats", "btn_fav", "btn_alerts", "btn_deals", "btn_more")
    return any(text in variants(k) for k in keys)


def btn_filter(key: str):
    return F.text.in_(variants(key))


async def price_change(name: str, current: float | None) -> float | None:
    """Skinport narxining so'nggi 24 soatdagi o'zgarishi (%), ma'lumot bo'lsa."""
    if not current:
        return None
    old = await db.price_at(name, int(time.time()) - 24 * 3600)
    return (current / old - 1) * 100 if old else None


# =============== Skin kartochkasi ===============
async def detail_text(name: str, lang: str) -> str:
    it = market.ITEMS[name]
    sp = it.get("min_price")
    steam, dm, cf, rate = await asyncio.gather(
        market.steam_price(name), market.dmarket_price(name),
        market.csfloat_price(name), market.get_usd_uzs())

    def m(x):
        return money_uzs(x, rate, lang)

    avail = {k: v for k, v in {"Skinport": sp, "DMarket": dm, "CSFloat": cf}.items() if v}
    lines = [
        f"🔫 <b>{html.escape(name)}</b>",
        "",
        f"🟢 Skinport: <b>{m(sp)}</b>  ({t(lang, 'lbl_sold', q=it.get('quantity', 0))})",
        f"🟣 DMarket: <b>{m(dm)}</b>",
    ]
    if cfg.CSFLOAT_KEY:
        lines.append(f"🟠 CSFloat: <b>{m(cf)}</b>")
    lines += [f"🟦 Steam: <b>{money(steam)}</b>", t(lang, "lbl_median", p=money(it.get("median_price")))]
    ch = await price_change(name, sp)
    if ch is not None:
        lines.append(t(lang, "lbl_24h", pct=f"{ch:+.1f}%"))
    if len(avail) >= 2:
        best = min(avail, key=avail.get)
        extra = ""
        if best != "Skinport" and sp:
            extra = t(lang, "lbl_cheaper", pct=f"{(1 - avail[best] / sp) * 100:.0f}")
        lines += ["", t(lang, "lbl_best", src=best, p=m(avail[best]), extra=extra)]
    ref = min(avail.values()) if avail else None
    if steam and ref:
        lines += ["", t(lang, "lbl_steam_diff", pct=f"{(steam / ref - 1) * 100:+.0f}%"),
                  t(lang, "lbl_steam_wallet", p=money(steam / 1.15))]
    links = []
    if it.get("item_page"):
        links.append(f'<a href="{it["item_page"]}">Skinport</a>')
    from urllib.parse import quote
    links.append(f'<a href="https://dmarket.com/ingame-items/item-list/csgo-skins?title={quote(name)}">DMarket</a>')
    links.append(f'<a href="https://csfloat.com/search?market_hash_name={quote(name)}">CSFloat</a>')
    lines += ["", "🔗 " + " · ".join(links), t(lang, "lbl_note")]
    return "\n".join(lines)


def detail_kb(name: str, lang: str, fav: bool) -> InlineKeyboardMarkup:
    sid = market.short_id(name)
    return kb([
        [btn(t(lang, "btn_alert_menu"), f"am:{sid}"),
         btn(t(lang, "btn_fav_del" if fav else "btn_fav_add"), f"fv:{sid}"),
         btn(t(lang, "btn_chart"), f"ch:{sid}")],
        [btn(t(lang, "btn_refresh"), f"r:{sid}")],
    ])


def alert_kb(sid: str, lang: str) -> InlineKeyboardMarkup:
    return kb([
        [btn("📉 −5%", f"a:{sid}:b5"), btn("📉 −10%", f"a:{sid}:b10"), btn("📉 −20%", f"a:{sid}:b20")],
        [btn("📈 +10%", f"a:{sid}:u10"), btn("📈 +20%", f"a:{sid}:u20")],
        [btn(t(lang, "alert_btn_custom"), f"ap:{sid}")],
        [btn(t(lang, "btn_back"), f"ab:{sid}")],
    ])


async def send_detail(message: Message, name: str, lang: str, uid: int) -> None:
    await db.track(name)
    await db.bump_view(name)
    await db.record_prices({name: market.ITEMS[name]["min_price"]})
    text = await detail_text(name, lang)
    markup = detail_kb(name, lang, await db.is_fav(uid, name))
    img = market.find_image(name)
    if img:
        try:
            await message.answer_photo(img, caption=text, reply_markup=markup)
            return
        except Exception as e:
            log.warning("Rasm yuborilmadi (%s): %s", name, e)
    await message.answer(text, reply_markup=markup, disable_web_page_preview=True)


async def create_alert(uid: int, name: str, target: float, direction: str, lang: str) -> str | None:
    """Tasdiq matnini qaytaradi; limitga yetgan bo'lsa None."""
    if await db.count_alerts(uid) >= cfg.MAX_ALERTS_PER_USER:
        return None
    await db.add_alert(uid, name, target, direction)
    return t(lang, "alert_set_below" if direction == "below" else "alert_set_above", p=money(target))


# =============== Buyruqlar ===============
@dp.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    lang = await db.get_lang(m.from_user.id)
    if not lang:
        await m.answer_photo(
            BufferedInputFile(START_BANNER.read_bytes(), filename="cs2marketuz-start.png"),
            caption=t("uz", "choose_lang"),
            reply_markup=lang_kb(),
        )
        return
    await m.answer_photo(
        BufferedInputFile(START_BANNER.read_bytes(), filename="cs2marketuz-start.png"),
        caption=t(lang, "welcome"),
        reply_markup=main_menu(lang),
    )


@dp.message(Command("lang"))
async def cmd_lang(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(t("uz", "choose_lang"), reply_markup=lang_kb())


@dp.message(Command("help"))
async def cmd_help(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(t(await get_lang(m.from_user.id), "help"))


@dp.message(Command("id"))
async def cmd_id(m: Message):
    await m.answer(f"ID: <code>{m.from_user.id}</code>")


@dp.message(Command("stats"))
async def cmd_stats(m: Message):
    if not cfg.ADMIN_ID or m.from_user.id != cfg.ADMIN_ID:
        return
    s = await db.stats_summary()
    top_s = "\n".join(f"{i}. {html.escape(q)} — {c}" for i, (q, c) in enumerate(s["top_search"], 1)) or "—"
    top_v = "\n".join(f"{i}. {html.escape(n)} — {c}" for i, (n, c) in enumerate(s["top_views"], 1)) or "—"
    await m.answer(
        "📊 <b>Statistika</b>\n"
        f"👥 Foydalanuvchilar: {s['users']}\n🆕 24 soatda yangi: {s['new24']}\n"
        f"🟢 24 soatda faol: {s['active24']}\n📅 7 kunda faol: {s['active7']}\n"
        f"🗞 Kunlik xabar: {s['digest']}\n🔔 Signallar: {s['alerts']}\n⭐ Sevimlilar: {s['favs']}\n"
        f"📈 Kuzatilayotgan skinlar: {s['tracked']}\n\n🔍 <b>Ko'p qidirilgan:</b>\n{top_s}\n\n"
        f"👁 <b>Ko'p ochilgan skinlar:</b>\n{top_v}")


# =============== Menyu tugmalari ===============
@dp.message(btn_filter("btn_search"))
async def h_search_btn(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(t(await get_lang(m.from_user.id), "search_prompt"))


def cats_rows(lang: str) -> list:
    return [[btn(t(lang, f"cat_{k}"), f"c:{k}")] for k in ("w", "k", "g", "s", "c")]


@dp.message(btn_filter("btn_cats"))
async def h_cats_btn(m: Message, state: FSMContext):
    await state.clear()
    lang = await get_lang(m.from_user.id)
    await m.answer(t(lang, "pick_cat"), reply_markup=kb(cats_rows(lang)))


async def fav_view(uid: int, lang: str):
    names = [n for n in await db.list_favs(uid) if n in market.ITEMS]
    if not names:
        return t(lang, "fav_empty"), None
    rows = []
    for n in names:
        cur = market.ITEMS[n]["min_price"]
        old = await db.price_at(n, int(time.time()) - 24 * 3600)
        ch = ""
        if old:
            arrow = "▲" if cur > old else "▼" if cur < old else "▬"
            ch = f" {arrow}{abs(cur / old - 1) * 100:.1f}%"
        rows.append([btn(f"{money(cur)}{ch} · {n}"[:64], f"j:{market.short_id(n)}")])
    return t(lang, "fav_title", n=len(names)), rows


@dp.message(Command("fav"))
@dp.message(btn_filter("btn_fav"))
async def h_fav(m: Message, state: FSMContext):
    await state.clear()
    lang = await get_lang(m.from_user.id)
    if not market.ITEMS:
        await m.answer(t(lang, "loading"))
        return
    text, rows = await fav_view(m.from_user.id, lang)
    await m.answer(text, reply_markup=kb(rows) if rows else None)


@dp.message(Command("alerts"))
@dp.message(btn_filter("btn_alerts"))
async def h_alerts(m: Message, state: FSMContext):
    await state.clear()
    lang = await get_lang(m.from_user.id)
    rows = await db.list_alerts(m.from_user.id)
    if not rows:
        await m.answer(t(lang, "alerts_empty"))
        return
    for aid, name, target, direction in rows:
        key = "alert_line_below" if direction == "below" else "alert_line_above"
        await m.answer(t(lang, key, name=html.escape(name), p=money(target)),
                       reply_markup=kb([[btn(t(lang, "btn_delete"), f"d:{aid}")]]))


@dp.message(Command("deals"))
@dp.message(btn_filter("btn_deals"))
async def h_deals(m: Message, state: FSMContext):
    await state.clear()
    lang = await get_lang(m.from_user.id)
    if not market.ITEMS:
        await m.answer(t(lang, "loading"))
        return
    deals = market.top_deals(10)
    if not deals:
        await m.answer(t(lang, "deals_empty"))
        return
    rows = [[btn(f"-{dip * 100:.0f}% · {money(market.ITEMS[n]['min_price'])} · {n}"[:64],
                 f"j:{market.short_id(n)}")] for n, dip in deals]
    await m.answer(t(lang, "deals_title") + "\n\n" + t(lang, "deals_note"), reply_markup=kb(rows))


async def more_kb(uid: int, lang: str) -> InlineKeyboardMarkup:
    digest = await db.get_digest(uid)
    return kb([
        [btn(t(lang, "more_inv"), "mo:inv")],
        [btn(t(lang, "more_case"), "mo:case")],
        [btn(t(lang, "more_rate"), "mo:rate")],
        [btn(t(lang, "more_digest_on" if digest else "more_digest_off"), "mo:dg")],
        [btn(t(lang, "more_lang"), "mo:lang"), btn(t(lang, "more_help"), "mo:help")],
    ])


@dp.message(btn_filter("btn_more"))
async def h_more(m: Message, state: FSMContext):
    await state.clear()
    lang = await get_lang(m.from_user.id)
    await m.answer(t(lang, "more_title"), reply_markup=await more_kb(m.from_user.id, lang))


# =============== Holatli (FSM) xabarlar ===============
@dp.message(Form.alert_price, F.text)
async def alert_price_input(m: Message, state: FSMContext):
    lang = await get_lang(m.from_user.id)
    name = (await state.get_data()).get("name")
    it = market.ITEMS.get(name or "")
    if not it:
        await state.clear()
        await m.answer(t(lang, "skin_gone"))
        return
    try:
        target = float(m.text.replace(",", ".").replace("$", "").strip())
    except ValueError:
        await m.answer(t(lang, "alert_bad_price"))
        return
    cur = it["min_price"]
    if not (0 < target < 1_000_000):
        await m.answer(t(lang, "alert_bad_price"))
        return
    if abs(target - cur) / cur < 0.005:
        await m.answer(t(lang, "alert_same"))
        return
    direction = "below" if target < cur else "above"
    text = await create_alert(m.from_user.id, name, round(target, 2), direction, lang)
    await state.clear()
    await m.answer(text or t(lang, "alert_limit", n=cfg.MAX_ALERTS_PER_USER))


@dp.message(Form.inventory, F.text)
async def inventory_input(m: Message, state: FSMContext):
    lang = await get_lang(m.from_user.id)
    if not market.ITEMS:
        await m.answer(t(lang, "loading"))
        return
    wait = await m.answer(t(lang, "inv_wait"))
    steamid = await market.resolve_steamid(m.text)
    if not steamid:
        await wait.edit_text(t(lang, "inv_bad"))
        return
    counts, status = await market.fetch_inventory(steamid)
    await state.clear()
    if status != "ok":
        key = {"private": "inv_private", "rate": "inv_rate"}.get(status, "inv_error")
        await wait.edit_text(t(lang, key))
        return
    if not counts:
        await wait.edit_text(t(lang, "inv_empty"))
        return
    total, rows, unpriced = market.value_inventory(counts)
    rate = await market.get_usd_uzs()
    text = t(lang, "inv_result", n=sum(counts.values()), total=money_uzs(total, rate, lang),
             unpriced=t(lang, "inv_unpriced", n=unpriced) if unpriced else "")
    if rows:
        text += "\n\n" + t(lang, "inv_top") + "\n" + "\n".join(
            f"{cnt}× {html.escape(name)} — {money(price)}" for _, name, cnt, price in rows[:10])
    await wait.edit_text(text)


# =============== Qidiruv (oddiy matn) ===============
@dp.message(F.text & ~F.text.startswith("/"))
async def on_text(m: Message):
    lang = await get_lang(m.from_user.id)
    if not market.ITEMS:
        await m.answer(t(lang, "loading"))
        return
    query = m.text.strip()
    names = market.search(query)
    await db.bump_search(query.lower())
    if not names:
        await m.answer(t(lang, "not_found"))
        return
    rows = [[btn(f"{money(market.ITEMS[n]['min_price'])} · {n}"[:64], f"i:{market.short_id(n)}")] for n in names]
    await m.answer(t(lang, "found_n", n=len(names)), reply_markup=kb(rows))


# =============== Til tanlash ===============
@dp.callback_query(F.data.startswith("lg:"))
async def cb_lang(c: CallbackQuery):
    lang = c.data.split(":")[1]
    if lang not in ("uz", "ru", "en"):
        await c.answer()
        return
    await db.set_lang(c.from_user.id, lang)
    await c.message.answer(t(lang, "welcome"), reply_markup=main_menu(lang))
    try:
        await c.message.delete()
    except Exception:
        pass
    await c.answer(t(lang, "lang_set"))


# =============== Qo'shimcha menyu ===============
@dp.callback_query(F.data.startswith("mo:"))
async def cb_more(c: CallbackQuery, state: FSMContext):
    action = c.data.split(":")[1]
    uid = c.from_user.id
    lang = await get_lang(uid)
    if action == "inv":
        await state.set_state(Form.inventory)
        await c.message.answer(t(lang, "inv_ask"))
        await c.answer()
    elif action == "case":
        await show_cases(c, lang, 0)
    elif action == "rate":
        rate = await market.get_usd_uzs()
        if rate:
            src = t(lang, "rate_src_cbu" if market.FX["src"] == "cbu" else "rate_src_er")
            await c.message.answer(t(lang, "rate_text", rate=f"{rate:,.2f}".replace(",", " "), src=src))
        else:
            await c.message.answer(t(lang, "rate_unavail"))
        await c.answer()
    elif action == "dg":
        on = not await db.get_digest(uid)
        await db.set_digest(uid, on)
        try:
            await c.message.edit_reply_markup(reply_markup=await more_kb(uid, lang))
        except TelegramBadRequest:
            pass
        await c.answer(t(lang, "digest_enabled" if on else "digest_disabled"), show_alert=True)
    elif action == "lang":
        await c.message.answer(t("uz", "choose_lang"), reply_markup=lang_kb())
        await c.answer()
    elif action == "help":
        await c.message.answer(t(lang, "help"))
        await c.answer()
    else:
        await c.answer()


# =============== Keys kalkulyatori ===============
def case_names() -> list[str]:
    names = [n for n in market.CRATES if n in market.ITEMS]
    names.sort(key=lambda n: market.ITEMS[n].get("quantity") or 0, reverse=True)
    return names


async def show_cases(c: CallbackQuery, lang: str, page: int) -> None:
    names = case_names()
    if not names:
        await c.answer(t(lang, "case_nodata"), show_alert=True)
        return
    total = max(1, -(-len(names) // cfg.PAGE_SIZE))
    page = min(max(page, 0), total - 1)
    chunk = names[page * cfg.PAGE_SIZE:(page + 1) * cfg.PAGE_SIZE]
    rows = [[btn(f"{money(market.ITEMS[n]['min_price'])} · {n}"[:64], f"cc:{market.short_id(n)}")] for n in chunk]
    nav = []
    if page > 0:
        nav.append(btn("◀️", f"cs:{page - 1}"))
    nav.append(btn(f"{page + 1}/{total}", "noop"))
    if page < total - 1:
        nav.append(btn("▶️", f"cs:{page + 1}"))
    rows.append(nav)
    await safe_edit(c, t(lang, "case_pick"), rows)
    await c.answer()


@dp.callback_query(F.data.startswith("cs:"))
async def cb_cases_page(c: CallbackQuery):
    await show_cases(c, await get_lang(c.from_user.id), int(c.data.split(":")[1]))


@dp.callback_query(F.data.startswith("cc:"))
async def cb_case_calc(c: CallbackQuery):
    lang = await get_lang(c.from_user.id)
    name = market.IDS.get(c.data.split(":")[1])
    res = market.case_ev(name) if name else None
    if not res:
        await c.answer(t(lang, "case_nodata"), show_alert=True)
        return
    tiers = "\n".join(
        t(lang, "case_tier", label=x["label"], pct=f"{x['prob'] * 100:.2f}".rstrip("0").rstrip("."),
          avg=money(x["avg"]), k=x["found"], n=x["total"]) for x in res["tiers"])
    text = t(lang, "case_result", name=html.escape(name), case=money(res["case"]), key=money(res["key"]),
             cost=money(res["cost"]), ev=money(res["ev"]), ratio=f"{res['ratio']:.0f}%", tiers=tiers)
    await c.message.answer(text)
    await c.answer()


# =============== Kategoriyalar ===============
def sub_title(lang: str, cat: str, sub: str) -> str:
    if cat == "w":
        gi, wi = map(int, sub.split("."))
        return f"🔫 {market.WEAPONS[gi][1][wi]}"
    if cat == "k" and sub != "x":
        return f"🔪 {market.KNIVES[int(sub)]}"
    if cat == "g" and sub != "x":
        return f"🧤 {market.GLOVES[int(sub)]}"
    return t(lang, f"cat_{cat}")


async def show_list(c: CallbackQuery, lang: str, cat: str, sub: str, sort: str, page: int) -> None:
    if not market.ITEMS:
        await c.answer(t(lang, "loading"), show_alert=True)
        return
    names = market.sort_names(market.category_items(cat, sub), sort)
    total = max(1, -(-len(names) // cfg.PAGE_SIZE))
    page = min(max(page, 0), total - 1)
    chunk = names[page * cfg.PAGE_SIZE:(page + 1) * cfg.PAGE_SIZE]
    rows = [[btn(f"{money(market.ITEMS[n]['min_price'])} · {n}"[:64], f"j:{market.short_id(n)}")] for n in chunk]
    nav = []
    if page > 0:
        nav.append(btn("◀️", f"l:{cat}:{sub}:{sort}:{page - 1}"))
    nav.append(btn(f"{page + 1}/{total}", "noop"))
    if page < total - 1:
        nav.append(btn("▶️", f"l:{cat}:{sub}:{sort}:{page + 1}"))
    rows.append(nav)
    next_sort = {"q": "a", "a": "d", "d": "q"}[sort]
    rows.append([btn(t(lang, "btn_sort", sort=t(lang, f"sort_{sort}")), f"l:{cat}:{sub}:{next_sort}:0")])
    if cat == "w":
        back = f"c:w:{sub.split('.')[0]}"
    elif cat in ("k", "g"):
        back = f"c:{cat}"
    else:
        back = "cr"
    rows.append([btn(t(lang, "btn_back"), back)])
    title = sub_title(lang, cat, sub)
    if names:
        text = t(lang, "list_header", title=title, n=len(names), sort=t(lang, f"sort_{sort}"))
    else:
        text = t(lang, "list_empty", title=title)
    await safe_edit(c, text, rows)
    await c.answer()


@dp.callback_query(F.data == "cr")
async def cb_cats_root(c: CallbackQuery):
    lang = await get_lang(c.from_user.id)
    await safe_edit(c, t(lang, "pick_cat"), cats_rows(lang))
    await c.answer()


@dp.callback_query(F.data == "noop")
async def cb_noop(c: CallbackQuery):
    await c.answer()


@dp.callback_query(F.data.startswith("c:"))
async def cb_cat_menu(c: CallbackQuery):
    lang = await get_lang(c.from_user.id)
    parts = c.data.split(":")
    cat = parts[1]
    back_root = [btn(t(lang, "btn_back"), "cr")]
    if cat == "w" and len(parts) == 2:
        rows = grid([btn(t(lang, key), f"c:w:{i}") for i, (key, _) in enumerate(market.WEAPONS)])
        await safe_edit(c, t(lang, "pick_group"), rows + [back_root])
    elif cat == "w":
        gi = int(parts[2])
        key, weapons = market.WEAPONS[gi]
        rows = grid([btn(w, f"l:w:{gi}.{wi}:q:0") for wi, w in enumerate(weapons)], 3)
        rows.append([btn(t(lang, "btn_back"), "c:w")])
        await safe_edit(c, t(lang, "pick_weapon", g=t(lang, key)), rows)
    elif cat in ("k", "g"):
        lst = market.KNIVES if cat == "k" else market.GLOVES
        rows = [[btn(t(lang, "btn_all"), f"l:{cat}:x:q:0")]]
        rows += grid([btn(s, f"l:{cat}:{i}:q:0") for i, s in enumerate(lst)])
        await safe_edit(c, t(lang, "pick_type", cat=t(lang, f"cat_{cat}")), rows + [back_root])
    else:
        await show_list(c, lang, cat, "x", "q", 0)
        return
    await c.answer()


@dp.callback_query(F.data.startswith("l:"))
async def cb_cat_list(c: CallbackQuery):
    _, cat, sub, sort, page = c.data.split(":")
    await show_list(c, await get_lang(c.from_user.id), cat, sub, sort, int(page))


# =============== Skin kartochkasi tugmalari ===============
async def _name_from(c: CallbackQuery, lang: str, idx: int = 1):
    name = market.IDS.get(c.data.split(":")[idx])
    if not name or name not in market.ITEMS:
        await c.answer(t(lang, "skin_gone"), show_alert=True)
        return None
    return name


@dp.callback_query(F.data.startswith("i:"))
@dp.callback_query(F.data.startswith("j:"))
async def cb_open_item(c: CallbackQuery):
    lang = await get_lang(c.from_user.id)
    name = await _name_from(c, lang)
    if name:
        await send_detail(c.message, name, lang, c.from_user.id)
        await c.answer()


@dp.callback_query(F.data.startswith("r:"))
async def cb_refresh(c: CallbackQuery):
    lang = await get_lang(c.from_user.id)
    name = await _name_from(c, lang)
    if not name:
        return
    market.STEAM_CACHE.pop(name, None)
    text = await detail_text(name, lang)
    markup = detail_kb(name, lang, await db.is_fav(c.from_user.id, name))
    try:
        if c.message.photo:
            await c.message.edit_caption(caption=text, reply_markup=markup)
        else:
            await c.message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
    except TelegramBadRequest as e:
        if "not modified" not in str(e):
            log.warning("Yangilashda xato: %s", e)
    await c.answer(t(lang, "refreshed"))


@dp.callback_query(F.data.startswith("fv:"))
async def cb_fav(c: CallbackQuery):
    lang = await get_lang(c.from_user.id)
    name = await _name_from(c, lang)
    if not name:
        return
    uid = c.from_user.id
    if not await db.is_fav(uid, name) and await db.count_favs(uid) >= cfg.MAX_FAVORITES:
        await c.answer(t(lang, "fav_limit", n=cfg.MAX_FAVORITES), show_alert=True)
        return
    added = await db.toggle_fav(uid, name)
    try:
        await c.message.edit_reply_markup(reply_markup=detail_kb(name, lang, added))
    except TelegramBadRequest:
        pass
    await c.answer(t(lang, "fav_added" if added else "fav_removed"))


@dp.callback_query(F.data.startswith("am:"))
async def cb_alert_menu(c: CallbackQuery):
    lang = await get_lang(c.from_user.id)
    if not await _name_from(c, lang):
        return
    try:
        await c.message.edit_reply_markup(reply_markup=alert_kb(c.data.split(":")[1], lang))
    except TelegramBadRequest:
        pass
    await c.answer(t(lang, "alert_hint"))


@dp.callback_query(F.data.startswith("ab:"))
async def cb_alert_back(c: CallbackQuery):
    lang = await get_lang(c.from_user.id)
    name = await _name_from(c, lang)
    if not name:
        return
    try:
        await c.message.edit_reply_markup(
            reply_markup=detail_kb(name, lang, await db.is_fav(c.from_user.id, name)))
    except TelegramBadRequest:
        pass
    await c.answer()


@dp.callback_query(F.data.startswith("a:"))
async def cb_alert_set(c: CallbackQuery):
    lang = await get_lang(c.from_user.id)
    name = await _name_from(c, lang)
    if not name:
        return
    spec = c.data.split(":")[2]
    direction = "below" if spec[0] == "b" else "above"
    pct = int(spec[1:])
    cur = market.ITEMS[name]["min_price"]
    target = round(cur * (1 - pct / 100) if direction == "below" else cur * (1 + pct / 100), 2)
    text = await create_alert(c.from_user.id, name, target, direction, lang)
    await c.answer(text or t(lang, "alert_limit", n=cfg.MAX_ALERTS_PER_USER), show_alert=True)
    if text:
        try:
            await c.message.edit_reply_markup(
                reply_markup=detail_kb(name, lang, await db.is_fav(c.from_user.id, name)))
        except TelegramBadRequest:
            pass


@dp.callback_query(F.data.startswith("ap:"))
async def cb_alert_custom(c: CallbackQuery, state: FSMContext):
    lang = await get_lang(c.from_user.id)
    name = await _name_from(c, lang)
    if not name:
        return
    await state.set_state(Form.alert_price)
    await state.update_data(name=name)
    await c.message.answer(t(lang, "alert_ask_price", cur=money(market.ITEMS[name]["min_price"])))
    await c.answer()


@dp.callback_query(F.data.startswith("d:"))
async def cb_alert_delete(c: CallbackQuery):
    lang = await get_lang(c.from_user.id)
    await db.delete_alert(int(c.data.split(":")[1]), c.from_user.id)
    try:
        await c.message.edit_text(t(lang, "alert_deleted"))
    except TelegramBadRequest:
        pass
    await c.answer()


@dp.callback_query(F.data.startswith("ch:"))
async def cb_chart(c: CallbackQuery):
    lang = await get_lang(c.from_user.id)
    name = await _name_from(c, lang)
    if not name:
        return
    await db.track(name)
    pts = await db.get_history(name, 30)
    if len(pts) < 2 or pts[-1][0] - pts[0][0] < 3600:
        await c.answer(t(lang, "chart_nodata"), show_alert=True)
        return
    await c.answer()
    png = await asyncio.to_thread(market.make_chart, name, pts)
    days = max(1, round((pts[-1][0] - pts[0][0]) / 86400))
    await c.message.answer_photo(BufferedInputFile(png, filename="chart.png"),
                                 caption=t(lang, "chart_caption", name=html.escape(name), days=days))


# =============== Fon vazifalari ===============
async def check_alerts(bot: Bot) -> None:
    langs: dict[int, str] = {}
    for aid, uid, name, target, direction in await db.all_alerts():
        it = market.ITEMS.get(name)
        if not it:
            continue
        cur = it["min_price"]
        if not (cur <= target if direction == "below" else cur >= target):
            continue
        if uid not in langs:
            langs[uid] = await get_lang(uid)
        key = "alert_fired_below" if direction == "below" else "alert_fired_above"
        text = t(langs[uid], key, name=html.escape(name), p=money(cur), t=money(target))
        if it.get("item_page"):
            text += f'\n<a href="{it["item_page"]}">Skinport</a>'
        try:
            await bot.send_message(uid, text)
        except TelegramForbiddenError:
            pass  # foydalanuvchi botni bloklagan
        except Exception as e:
            log.warning("Signal yuborilmadi (%s): %s", uid, e)
        await db.delete_alert(aid)


async def build_digest(uid: int, lang: str) -> str | None:
    names = [n for n in await db.list_favs(uid) if n in market.ITEMS]
    lines = []
    if names:
        lines.append(t(lang, "digest_title"))
        for n in names[:20]:
            cur = market.ITEMS[n]["min_price"]
            old = await db.price_at(n, int(time.time()) - 24 * 3600)
            if old:
                arrow = "▲" if cur > old else "▼" if cur < old else "▬"
                lines.append(f"{arrow} {html.escape(n)}: {money(cur)} ({(cur / old - 1) * 100:+.1f}%)")
            else:
                lines.append(f"• {html.escape(n)}: {money(cur)}")
    else:
        deals = market.top_deals(3)
        if not deals:
            return None
        lines.append(t(lang, "digest_none_fav"))
        for n, dip in deals:
            lines.append(f"• {html.escape(n)}: {money(market.ITEMS[n]['min_price'])} (-{dip * 100:.0f}%)")
    n_alerts = await db.count_alerts(uid)
    if n_alerts:
        lines += ["", t(lang, "digest_alerts", n=n_alerts)]
    return "\n".join(lines)


async def send_digests(bot: Bot) -> None:
    now_local = datetime.now(cfg.UZ_TZ)
    if now_local.hour != cfg.DIGEST_HOUR or not market.ITEMS:
        return
    today = now_local.strftime("%Y-%m-%d")
    if await db.kv_get("digest_date") == today:
        return
    await db.kv_set("digest_date", today)
    for uid, lang in await db.digest_users():
        try:
            text = await build_digest(uid, lang)
            if text:
                await bot.send_message(uid, text)
        except TelegramForbiddenError:
            pass
        except Exception as e:
            log.warning("Kunlik xabar yuborilmadi (%s): %s", uid, e)
        await asyncio.sleep(0.05)


async def post_channel(bot: Bot) -> None:
    if not cfg.CHANNEL_ID or not market.ITEMS:
        return
    last = await db.kv_get("channel_last")
    if last and time.time() - float(last) < cfg.CHANNEL_POST_HOURS * 3600:
        return
    fresh = []
    for n, dip in market.top_deals(40):
        if not await db.recently_posted(n, 24):
            fresh.append((n, dip))
        if len(fresh) == 5:
            break
    if not fresh:
        return
    lang = cfg.CHANNEL_LANG if cfg.CHANNEL_LANG in ("uz", "ru", "en") else "uz"
    lines = [t(lang, "channel_title"), ""]
    for n, dip in fresh:
        it = market.ITEMS[n]
        label = f'<a href="{it["item_page"]}">{html.escape(n)}</a>' if it.get("item_page") else html.escape(n)
        lines.append(t(lang, "channel_line", name=label, p=money(it["min_price"]), pct=f"{dip * 100:.0f}"))
    if BOT_USERNAME:
        lines += ["", t(lang, "channel_footer", bot=BOT_USERNAME)]
    text = "\n".join(lines)
    img = market.find_image(fresh[0][0])
    sent = False
    if img:
        try:
            await bot.send_photo(cfg.CHANNEL_ID, img, caption=text)
            sent = True
        except Exception as e:
            log.warning("Kanalga rasm yuborilmadi: %s", e)
    if not sent:
        await bot.send_message(cfg.CHANNEL_ID, text, disable_web_page_preview=True)
    for n, _ in fresh:
        await db.mark_posted(n)
    await db.kv_set("channel_last", str(time.time()))


async def background(bot: Bot) -> None:
    while True:
        try:
            await market.refresh_items()
            names = await db.tracked_names()
            await db.record_prices({n: market.ITEMS[n]["min_price"] for n in names if n in market.ITEMS})
            await check_alerts(bot)
        except Exception as e:
            log.error("Yangilashda xato: %s", e)
        for job in (send_digests, post_channel):
            try:
                await job(bot)
            except Exception as e:
                log.error("%s xato: %s", job.__name__, e)
        try:
            today = datetime.now(cfg.UZ_TZ).strftime("%Y-%m-%d")
            if await db.kv_get("prune_date") != today:
                await db.prune_history()
                await db.kv_set("prune_date", today)
        except Exception as e:
            log.warning("Tozalashda xato: %s", e)
        await asyncio.sleep(cfg.REFRESH_SECONDS)


async def images_loop() -> None:
    while True:
        await market.load_images()
        await asyncio.sleep(86400 if market.IMAGES else 600)


async def main() -> None:
    global BOT_USERNAME
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not cfg.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN topilmadi. .env faylini tekshiring.")
    await db.init_db()
    session = aiohttp.ClientSession(headers={"User-Agent": "cs2-price-bot/2.0"})
    market.set_session(session)
    market.load_items_cache()
    if not market.ITEMS:
        await market.load_fallback_items()
    bot = Bot(cfg.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    BOT_USERNAME = (await bot.get_me()).username or ""
    await bot.set_my_commands([
        BotCommand(command="start", description="Bosh menyu / Меню / Menu"),
        BotCommand(command="fav", description="⭐ Sevimlilar / Избранное / Favorites"),
        BotCommand(command="alerts", description="🔔 Signallar / Сигналы / Alerts"),
        BotCommand(command="deals", description="🏆 Takliflar / Выгодно / Deals"),
        BotCommand(command="lang", description="🌐 Til / Язык / Language"),
        BotCommand(command="help", description="ℹ️ Yordam / Помощь / Help"),
    ])
    tasks = [asyncio.create_task(background(bot)), asyncio.create_task(images_loop())]
    try:
        await dp.start_polling(bot)
    finally:
        for task in tasks:
            task.cancel()
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
