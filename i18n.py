"""Tarjimalar: o'zbekcha (uz), ruscha (ru), inglizcha (en)."""

T: dict[str, dict[str, str]] = {}


def _a(key: str, uz: str, ru: str, en: str) -> None:
    T[key] = {"uz": uz, "ru": ru, "en": en}


def t(lang: str, key: str, /, **kw) -> str:
    entry = T[key]
    s = entry.get(lang) or entry["uz"]
    return s.format(**kw) if kw else s


def variants(key: str) -> set[str]:
    """Tugma matnining barcha tillardagi variantlari (tugmani aniqlash uchun)."""
    return set(T[key].values())


# ---------- Til ----------
_a("choose_lang",
   "🌐 Tilni tanlang / Выберите язык / Choose your language",
   "🌐 Tilni tanlang / Выберите язык / Choose your language",
   "🌐 Tilni tanlang / Выберите язык / Choose your language")
_a("lang_set", "✅ Til o'zgartirildi: O'zbekcha", "✅ Язык изменён: Русский", "✅ Language set: English")

# ---------- Asosiy menyu ----------
_a("btn_search", "🔍 Skin qidirish", "🔍 Поиск скина", "🔍 Search skin")
_a("btn_cats", "📂 Kategoriyalar", "📂 Категории", "📂 Categories")
_a("btn_fav", "⭐ Sevimlilar", "⭐ Избранное", "⭐ Favorites")
_a("btn_alerts", "🔔 Signallarim", "🔔 Мои сигналы", "🔔 My alerts")
_a("btn_deals", "🏆 Takliflar", "🏆 Выгодные цены", "🏆 Best deals")
_a("btn_more", "🧰 Qo'shimcha", "🧰 Ещё", "🧰 More")
_a("btn_app", "🛒 Mini App", "🛒 Mini App", "🛒 Mini App")

_a("welcome",
   "Salom! 👋 Men <b>CS2 skin narx botiman</b>.\n\n"
   "Skin nomini yozing, masalan: <code>ak-47 redline</code> yoki <code>awp asiimov</code>.\n"
   "Men Skinport, DMarket va Steam narxlarini solishtirib beraman, narx o'zgarganda esa xabar yuboraman.",
   "Привет! 👋 Я <b>бот цен на скины CS2</b>.\n\n"
   "Напишите название скина, например: <code>ak-47 redline</code> или <code>awp asiimov</code>.\n"
   "Я сравню цены Skinport, DMarket и Steam и сообщу, когда цена изменится.",
   "Hi! 👋 I'm a <b>CS2 skin price bot</b>.\n\n"
   "Type a skin name, e.g. <code>ak-47 redline</code> or <code>awp asiimov</code>.\n"
   "I compare Skinport, DMarket and Steam prices and notify you when a price changes.")

_a("help",
   "<b>Qanday ishlatiladi</b>\n"
   "1. Skin nomini yozing (ingliz tilida) yoki 📂 Kategoriyalar tugmasini bosing.\n"
   "2. Ro'yxatdan skinni tanlang.\n"
   "3. 🔔 bilan narx tushganda yoki oshganda signal qo'ying, ⭐ bilan sevimlilarga qo'shing, "
   "📈 bilan narx grafigini ko'ring.\n\n"
   "<b>Buyruqlar</b>\n"
   "/start — bosh menyu\n/fav — sevimlilar\n/alerts — signallarim\n"
   "/deals — eng yaxshi takliflar\n/lang — tilni o'zgartirish\n/help — yordam\n\n"
   "⚠️ Narxlar ma'lumot uchun. Savdoni faqat rasmiy bozorlarda qiling, begona odamlarga "
   "Steam login/parolingizni bermang.",
   "<b>Как пользоваться</b>\n"
   "1. Напишите название скина (по-английски) или нажмите 📂 Категории.\n"
   "2. Выберите скин из списка.\n"
   "3. С помощью 🔔 поставьте сигнал на падение или рост цены, ⭐ добавляет в избранное, "
   "📈 показывает график цены.\n\n"
   "<b>Команды</b>\n"
   "/start — главное меню\n/fav — избранное\n/alerts — мои сигналы\n"
   "/deals — выгодные цены\n/lang — сменить язык\n/help — помощь\n\n"
   "⚠️ Цены носят справочный характер. Торгуйте только на официальных площадках и никому не "
   "передавайте логин/пароль от Steam.",
   "<b>How to use</b>\n"
   "1. Type a skin name (in English) or tap 📂 Categories.\n"
   "2. Pick a skin from the list.\n"
   "3. Use 🔔 to set a price drop/rise alert, ⭐ to add it to favorites and "
   "📈 to see the price chart.\n\n"
   "<b>Commands</b>\n"
   "/start — main menu\n/fav — favorites\n/alerts — my alerts\n"
   "/deals — best deals\n/lang — change language\n/help — help\n\n"
   "⚠️ Prices are for information only. Trade on official markets only and never share "
   "your Steam login/password.")

# ---------- Qo'shimcha menyu ----------
_a("more_title", "🧰 Qo'shimcha xizmatlar:", "🧰 Дополнительно:", "🧰 More tools:")
_a("more_inv", "💼 Inventar narxi", "💼 Стоимость инвентаря", "💼 Inventory value")
_a("more_case", "📦 Keys kalkulyatori", "📦 Калькулятор кейсов", "📦 Case calculator")
_a("more_rate", "💱 Dollar kursi", "💱 Курс доллара", "💱 USD rate")
_a("more_lang", "🌐 Til", "🌐 Язык", "🌐 Language")
_a("more_help", "ℹ️ Yordam", "ℹ️ Помощь", "ℹ️ Help")
_a("more_digest_on", "🗞 Kunlik xabar: yoqilgan ✅", "🗞 Ежедневная сводка: вкл ✅", "🗞 Daily digest: on ✅")
_a("more_digest_off", "🗞 Kunlik xabar: o'chiq", "🗞 Ежедневная сводка: выкл", "🗞 Daily digest: off")
_a("digest_enabled",
   "✅ Kunlik xabar yoqildi. Har kuni 09:00 da (Toshkent vaqti) sevimli skinlaringiz narxini yuboraman.",
   "✅ Ежедневная сводка включена. Каждый день в 09:00 (по Ташкенту) буду присылать цены ваших избранных скинов.",
   "✅ Daily digest enabled. Every day at 09:00 (Tashkent time) I'll send your favorite skins' prices.")
_a("digest_disabled", "Kunlik xabar o'chirildi.", "Ежедневная сводка отключена.", "Daily digest disabled.")

# ---------- Qidiruv ----------
_a("search_prompt",
   "Skin nomini yozing, masalan: <code>karambit doppler</code>",
   "Напишите название скина, например: <code>karambit doppler</code>",
   "Type a skin name, e.g. <code>karambit doppler</code>")
_a("loading", "Ma'lumotlar yuklanmoqda, biroz kuting ⏳", "Данные загружаются, подождите немного ⏳",
   "Loading data, please wait a moment ⏳")
_a("not_found",
   "Hech narsa topilmadi 😕 Nomini inglizcha yozib ko'ring (masalan: <code>m4a4 howl</code>).",
   "Ничего не найдено 😕 Попробуйте написать название по-английски (например: <code>m4a4 howl</code>).",
   "Nothing found 😕 Try the English name (e.g. <code>m4a4 howl</code>).")
_a("found_n", "Topildi: {n} ta natija. Tanlang 👇", "Найдено результатов: {n}. Выберите 👇",
   "Found {n} results. Choose 👇")
_a("skin_gone", "Skin topilmadi, qayta qidiring.", "Скин не найден, повторите поиск.",
   "Skin not found, please search again.")

# ---------- Skin kartochkasi ----------
_a("som", "so'm", "сум", "UZS")
_a("lbl_sold", "sotuvda: {q} ta", "в продаже: {q} шт.", "listed: {q}")
_a("lbl_median", "📊 Skinport o'rtacha: {p}", "📊 Skinport, средняя: {p}", "📊 Skinport median: {p}")
_a("lbl_24h", "📈 24 soatda: {pct}", "📈 За 24 часа: {pct}", "📈 24h change: {pct}")
_a("lbl_best", "🏆 Eng arzon: <b>{src}</b> — {p}{extra}", "🏆 Дешевле всего: <b>{src}</b> — {p}{extra}",
   "🏆 Cheapest: <b>{src}</b> — {p}{extra}")
_a("lbl_cheaper", " (Skinport'dan {pct}% arzon)", " (на {pct}% дешевле Skinport)", " ({pct}% cheaper than Skinport)")
_a("lbl_steam_diff", "↔️ Steam eng arzon real narxdan <b>{pct}</b> farq qiladi.",
   "↔️ Steam отличается от самой низкой реальной цены на <b>{pct}</b>.",
   "↔️ Steam differs from the lowest real-money price by <b>{pct}</b>.")
_a("lbl_steam_wallet",
   "💼 Steam'da sotsangiz hamyonga taxminan <b>{p}</b> tushadi (Steam hamyonidagi pulni naqdlashtirib bo'lmaydi).",
   "💼 При продаже в Steam на кошелёк придёт примерно <b>{p}</b> (деньги Steam нельзя вывести).",
   "💼 Selling on Steam nets about <b>{p}</b> in wallet funds (Steam wallet money can't be cashed out).")
_a("lbl_note", "<i>Narxlar komissiyasiz ro'yxat narxi.</i>", "<i>Цены указаны без учёта комиссий.</i>",
   "<i>Prices are listing prices before fees.</i>")
_a("btn_alert_menu", "🔔 Signal", "🔔 Сигнал", "🔔 Alert")
_a("btn_fav_add", "☆ Sevimli", "☆ В избранное", "☆ Favorite")
_a("btn_fav_del", "⭐ Sevimlida", "⭐ В избранном", "⭐ Favorited")
_a("btn_chart", "📈 Grafik", "📈 График", "📈 Chart")
_a("btn_refresh", "🔄 Yangilash", "🔄 Обновить", "🔄 Refresh")
_a("btn_back", "⬅️ Orqaga", "⬅️ Назад", "⬅️ Back")
_a("refreshed", "Yangilandi ✅", "Обновлено ✅", "Updated ✅")

# ---------- Signallar ----------
_a("alert_hint", "Narx qancha o'zgarganda xabar beray?", "При каком изменении цены сообщить?",
   "How much should the price change before I notify you?")
_a("alert_btn_custom", "✏️ Narx kiritish", "✏️ Своя цена", "✏️ Custom price")
_a("alert_set_below", "✅ Signal qo'yildi: narx {p} dan pasaysa xabar beraman.",
   "✅ Сигнал установлен: сообщу, когда цена упадёт ниже {p}.",
   "✅ Alert set: I'll notify you when the price drops to {p} or below.")
_a("alert_set_above", "✅ Signal qo'yildi: narx {p} dan oshsa xabar beraman.",
   "✅ Сигнал установлен: сообщу, когда цена поднимется выше {p}.",
   "✅ Alert set: I'll notify you when the price rises to {p} or above.")
_a("alert_limit", "Maksimum {n} ta signal qo'yish mumkin.", "Максимум сигналов: {n}.", "Maximum {n} alerts allowed.")
_a("alert_ask_price",
   "Maqsadli narxni dollarda yozing (hozirgi narx: {cur}). Masalan: <code>25.5</code>\n"
   "Narx hozirgidan past bo'lsa, pasayganda; baland bo'lsa, oshganda xabar beraman.",
   "Напишите целевую цену в долларах (сейчас: {cur}). Например: <code>25.5</code>\n"
   "Если цена ниже текущей — сообщу при падении, если выше — при росте.",
   "Send your target price in USD (now: {cur}). For example: <code>25.5</code>\n"
   "If it's below the current price I'll alert you when it drops, if above — when it rises.")
_a("alert_bad_price", "Narxni raqam bilan yozing, masalan: <code>25.5</code>",
   "Напишите цену числом, например: <code>25.5</code>", "Please send the price as a number, e.g. <code>25.5</code>")
_a("alert_same", "Bu narx hozirgi narxga juda yaqin. Boshqa narx yozing.",
   "Эта цена почти равна текущей. Напишите другую.", "That's too close to the current price. Send a different one.")
_a("alerts_empty", "Sizda hali signal yo'q. Skin qidirib, 🔔 tugmasini bosing.",
   "У вас пока нет сигналов. Найдите скин и нажмите 🔔.", "You have no alerts yet. Find a skin and tap 🔔.")
_a("alert_line_below", "🔔 <b>{name}</b>\nNarx {p} dan pasaysa xabar beraman.",
   "🔔 <b>{name}</b>\nСообщу, когда цена упадёт до {p}.", "🔔 <b>{name}</b>\nI'll notify you when the price drops to {p}.")
_a("alert_line_above", "🔔 <b>{name}</b>\nNarx {p} dan oshsa xabar beraman.",
   "🔔 <b>{name}</b>\nСообщу, когда цена поднимется до {p}.", "🔔 <b>{name}</b>\nI'll notify you when the price rises to {p}.")
_a("btn_delete", "🗑 O'chirish", "🗑 Удалить", "🗑 Delete")
_a("alert_deleted", "🗑 Signal o'chirildi.", "🗑 Сигнал удалён.", "🗑 Alert deleted.")
_a("alert_fired_below", "🔔 <b>Narx tushdi!</b>\n{name}\nHozir: <b>{p}</b> (siz belgilagan: {t})",
   "🔔 <b>Цена упала!</b>\n{name}\nСейчас: <b>{p}</b> (ваш порог: {t})",
   "🔔 <b>Price dropped!</b>\n{name}\nNow: <b>{p}</b> (your target: {t})")
_a("alert_fired_above", "🔔 <b>Narx ko'tarildi!</b>\n{name}\nHozir: <b>{p}</b> (siz belgilagan: {t})",
   "🔔 <b>Цена выросла!</b>\n{name}\nСейчас: <b>{p}</b> (ваш порог: {t})",
   "🔔 <b>Price rose!</b>\n{name}\nNow: <b>{p}</b> (your target: {t})")

# ---------- Sevimlilar ----------
_a("fav_added", "⭐ Sevimlilarga qo'shildi", "⭐ Добавлено в избранное", "⭐ Added to favorites")
_a("fav_removed", "Sevimlilardan olib tashlandi", "Удалено из избранного", "Removed from favorites")
_a("fav_limit", "Maksimum {n} ta sevimli skin.", "Максимум избранных скинов: {n}.", "Maximum {n} favorite skins.")
_a("fav_empty", "Sevimlilar ro'yxati bo'sh. Skinni ochib, ☆ tugmasini bosing.",
   "Избранное пусто. Откройте скин и нажмите ☆.", "Your favorites are empty. Open a skin and tap ☆.")
_a("fav_title", "⭐ <b>Sevimlilar</b> ({n} ta)", "⭐ <b>Избранное</b> ({n})", "⭐ <b>Favorites</b> ({n})")

# ---------- Grafik ----------
_a("chart_nodata",
   "Grafik uchun ma'lumot hali yetarli emas. Bot bu skin narxini kuzata boshladi, bir necha soatdan so'ng qayta urinib ko'ring 📈",
   "Для графика пока мало данных. Бот начал следить за ценой этого скина, попробуйте через несколько часов 📈",
   "Not enough data for a chart yet. The bot has started tracking this skin, try again in a few hours 📈")
_a("chart_caption", "📈 {name}\nOxirgi {days} kun, Skinport (USD)", "📈 {name}\nЗа {days} дн., Skinport (USD)",
   "📈 {name}\nLast {days} days, Skinport (USD)")

# ---------- Takliflar ----------
_a("deals_title",
   "🏆 <b>Eng yaxshi takliflar</b>\nSkinport'da hozirgi narxi o'rtacha narxdan sezilarli arzon skinlar:",
   "🏆 <b>Выгодные цены</b>\nСкины, которые сейчас на Skinport заметно дешевле средней цены:",
   "🏆 <b>Best deals</b>\nSkins currently priced well below their Skinport median:")
_a("deals_empty", "Hozircha mos takliflar topilmadi.", "Пока подходящих предложений нет.", "No matching deals right now.")
_a("deals_note", "<i>Eslatma: float va pattern narxga ta'sir qiladi, sotib olishdan oldin skinni tekshiring.</i>",
   "<i>Учтите: float и паттерн влияют на цену, проверяйте скин перед покупкой.</i>",
   "<i>Note: float and pattern affect price, check the exact item before buying.</i>")

# ---------- Inventar ----------
_a("inv_ask",
   "💼 Steam profilingiz havolasini yuboring (masalan: <code>https://steamcommunity.com/id/nom</code>) yoki SteamID64 raqamini.\n"
   "Profil va inventar <b>ochiq</b> (Public) bo'lishi kerak. Parol yoki trade-link yubormang!",
   "💼 Отправьте ссылку на ваш профиль Steam (например: <code>https://steamcommunity.com/id/name</code>) или SteamID64.\n"
   "Профиль и инвентарь должны быть <b>открытыми</b> (Public). Не отправляйте пароль или trade-ссылку!",
   "💼 Send your Steam profile link (e.g. <code>https://steamcommunity.com/id/name</code>) or SteamID64.\n"
   "Your profile and inventory must be <b>public</b>. Never send a password or trade link!")
_a("inv_wait", "⏳ Inventar tekshirilmoqda...", "⏳ Проверяю инвентарь...", "⏳ Checking inventory...")
_a("inv_bad", "Profil topilmadi. Havolani tekshirib, qayta yuboring.",
   "Профиль не найден. Проверьте ссылку и отправьте снова.", "Profile not found. Check the link and send it again.")
_a("inv_private",
   "Inventar yopiq yoki Steam javob bermadi. Steam profilingiz maxfiylik sozlamalarida inventarni «Ochiq» qiling.",
   "Инвентарь закрыт или Steam не ответил. В настройках приватности профиля Steam откройте инвентарь.",
   "The inventory is private or Steam didn't respond. Set your inventory to Public in Steam privacy settings.")
_a("inv_rate", "Steam hozir so'rovlarni cheklayapti. Bir necha daqiqadan so'ng urinib ko'ring.",
   "Steam сейчас ограничивает запросы. Попробуйте через несколько минут.",
   "Steam is rate-limiting requests right now. Try again in a few minutes.")
_a("inv_error", "Inventarni olib bo'lmadi. Keyinroq urinib ko'ring.", "Не удалось получить инвентарь. Попробуйте позже.",
   "Couldn't load the inventory. Please try later.")
_a("inv_empty", "Inventarda CS2 buyumlari topilmadi.", "В инвентаре нет предметов CS2.", "No CS2 items found in the inventory.")
_a("inv_result",
   "💼 <b>Inventar narxi</b>\nBuyumlar: {n} ta\nUmumiy qiymat (Skinport eng arzon narxlari): <b>{total}</b>{unpriced}",
   "💼 <b>Стоимость инвентаря</b>\nПредметов: {n}\nОбщая стоимость (минимальные цены Skinport): <b>{total}</b>{unpriced}",
   "💼 <b>Inventory value</b>\nItems: {n}\nTotal value (lowest Skinport prices): <b>{total}</b>{unpriced}")
_a("inv_unpriced", "\nNarxi topilmagan: {n} ta (hisobga olinmagan)", "\nБез цены: {n} (не учтено)",
   "\nNo price found: {n} (not counted)")
_a("inv_top", "<b>Eng qimmat buyumlar:</b>", "<b>Самые дорогие предметы:</b>", "<b>Most valuable items:</b>")

# ---------- Keys kalkulyatori ----------
_a("case_pick", "📦 Keysni tanlang:", "📦 Выберите кейс:", "📦 Choose a case:")
_a("case_nodata", "Keys ma'lumotlari hali yuklanmagan. Bir ozdan so'ng urinib ko'ring.",
   "Данные по кейсам ещё не загружены. Попробуйте чуть позже.", "Case data hasn't loaded yet. Please try again shortly.")
_a("case_result",
   "📦 <b>{name}</b>\n\nKeys narxi: {case}\nKalit: {key}\n<b>Jami xarajat: {cost}</b>\n\n"
   "Kutilgan o'rtacha yutuq (EV): <b>{ev}</b>\nEV / xarajat: <b>{ratio}</b>\n\n{tiers}\n\n"
   "<i>Hisob taxminiy: Skinport'dagi eng arzon narxlar, float va StatTrak hisobga olinmagan, "
   "sotishdagi komissiya ushlanmagan. Odatda keys ochish zarar keltiradi.</i>",
   "📦 <b>{name}</b>\n\nЦена кейса: {case}\nКлюч: {key}\n<b>Итого затраты: {cost}</b>\n\n"
   "Ожидаемый средний выигрыш (EV): <b>{ev}</b>\nEV / затраты: <b>{ratio}</b>\n\n{tiers}\n\n"
   "<i>Расчёт приблизительный: минимальные цены Skinport, float и StatTrak не учтены, "
   "комиссия при продаже не вычтена. Обычно открытие кейсов убыточно.</i>",
   "📦 <b>{name}</b>\n\nCase price: {case}\nKey: {key}\n<b>Total cost: {cost}</b>\n\n"
   "Expected average return (EV): <b>{ev}</b>\nEV / cost: <b>{ratio}</b>\n\n{tiers}\n\n"
   "<i>Rough estimate: lowest Skinport prices, float and StatTrak ignored, selling fees not deducted. "
   "Opening cases usually loses money.</i>")
_a("case_tier", "• {label}: {pct}% → {avg} ({k}/{n})", "• {label}: {pct}% → {avg} ({k}/{n})",
   "• {label}: {pct}% → {avg} ({k}/{n})")

# ---------- Kurs ----------
_a("rate_text", "💱 1 USD = <b>{rate}</b> so'm\n<i>Manba: {src}</i>", "💱 1 USD = <b>{rate}</b> сум\n<i>Источник: {src}</i>",
   "💱 1 USD = <b>{rate}</b> UZS\n<i>Source: {src}</i>")
_a("rate_src_cbu", "O'zbekiston Markaziy banki", "Центральный банк Узбекистана", "Central Bank of Uzbekistan")
_a("rate_src_er", "bozor kursi (zaxira manba)", "рыночный курс (резервный источник)", "market rate (backup source)")
_a("rate_unavail", "Kursni hozir olib bo'lmadi.", "Курс сейчас недоступен.", "The rate is unavailable right now.")

# ---------- Kunlik xabar va kanal ----------
_a("digest_title", "🗞 <b>Kunlik xabar</b> — sevimli skinlaringiz:", "🗞 <b>Ежедневная сводка</b> — ваши избранные скины:",
   "🗞 <b>Daily digest</b> — your favorite skins:")
_a("digest_none_fav", "🗞 <b>Kunlik xabar</b>\nSevimli skinlaringiz yo'q, shuning uchun bugungi eng yaxshi takliflar:",
   "🗞 <b>Ежедневная сводка</b>\nИзбранного нет, поэтому вот лучшие предложения на сегодня:",
   "🗞 <b>Daily digest</b>\nYou have no favorites yet, so here are today's best deals:")
_a("digest_alerts", "🔔 Faol signallar: {n} ta", "🔔 Активных сигналов: {n}", "🔔 Active alerts: {n}")
_a("channel_title", "🏆 <b>Bugungi eng yaxshi takliflar</b> (Skinport)", "🏆 <b>Лучшие предложения дня</b> (Skinport)",
   "🏆 <b>Today's best deals</b> (Skinport)")
_a("channel_line", "• {name}\n   {p} · o'rtachadan -{pct}%", "• {name}\n   {p} · на {pct}% ниже средней",
   "• {name}\n   {p} · {pct}% below median")
_a("channel_footer", "🤖 Narx signallari va solishtirish: @{bot}", "🤖 Сигналы цен и сравнение: @{bot}",
   "🤖 Price alerts and comparison: @{bot}")

# ---------- Kategoriyalar ----------
_a("cat_w", "🔫 Qurollar", "🔫 Оружие", "🔫 Weapons")
_a("cat_k", "🔪 Pichoqlar", "🔪 Ножи", "🔪 Knives")
_a("cat_g", "🧤 Qo'lqoplar", "🧤 Перчатки", "🧤 Gloves")
_a("cat_s", "🏷 Stikerlar", "🏷 Наклейки", "🏷 Stickers")
_a("cat_c", "📦 Keyslar", "📦 Кейсы", "📦 Cases")
_a("pick_cat", "Kategoriyani tanlang 👇", "Выберите категорию 👇", "Choose a category 👇")
_a("pick_group", "🔫 Qurol turini tanlang:", "🔫 Выберите тип оружия:", "🔫 Choose a weapon type:")
_a("pick_weapon", "🔫 {g} — qurolni tanlang:", "🔫 {g} — выберите оружие:", "🔫 {g} — choose a weapon:")
_a("pick_type", "{cat} — turini tanlang:", "{cat} — выберите вид:", "{cat} — choose a type:")
_a("btn_all", "📋 Hammasi", "📋 Все", "📋 All")
_a("g_rifles", "Miltiqlar", "Винтовки", "Rifles")
_a("g_snipers", "Snayperlar", "Снайперские", "Snipers")
_a("g_pistols", "Pistoletlar", "Пистолеты", "Pistols")
_a("g_smg", "Avtomatlar (SMG)", "Пистолеты-пулемёты", "SMGs")
_a("g_heavy", "Og'ir qurollar", "Тяжёлое оружие", "Heavy")
_a("sort_q", "🔥 Mashhurlik", "🔥 Популярность", "🔥 Popularity")
_a("sort_a", "💲 Arzonidan", "💲 Сначала дешёвые", "💲 Cheapest first")
_a("sort_d", "💲 Qimmatidan", "💲 Сначала дорогие", "💲 Priciest first")
_a("btn_sort", "↕️ Tartib: {sort}", "↕️ Сортировка: {sort}", "↕️ Sort: {sort}")
_a("list_header", "<b>{title}</b>\nTopildi: {n} ta · {sort}", "<b>{title}</b>\nНайдено: {n} · {sort}",
   "<b>{title}</b>\nFound: {n} · {sort}")
_a("list_empty", "<b>{title}</b>\nBu bo'limda hozircha skin topilmadi.", "<b>{title}</b>\nВ этом разделе пока ничего нет.",
   "<b>{title}</b>\nNothing found in this section yet.")
