# CS2MarketUZ Mini App — amalga oshirish rejasi

## Maqsad
@cs2marketuz_bot uchun bepul lokal ishlab chiqiladigan, keyinchalik VPS’ga ko‘chiriladigan Telegram Mini App yaratish. Dastlab katalog va narx taqqoslash; keyingi bosqichda xavfsiz P2P savdo oqimi.

## Tanlangan yo‘l
- **Plain-local development**: boshlang‘ich mablag‘ talab qilmaydi.
- Mavjud Python bot, `market.py`, `db.py` va SQLite bazasi qayta ishlatiladi.
- Frontend: oddiy HTML/CSS/JavaScript, qo‘shimcha build xarajatisiz.
- Backend: mavjud `aiohttp` asosida API.
- Hozircha real to‘lov, Steam login paroli yoki avtomatik trade bajarilmaydi.

## Bosqichlar
1. **Poydevor**: Mini App frontend, API server, Telegram `initData` tekshiruvi, skin katalogi va tafsilot endpointlari.
2. **Bot integratsiyasi**: bot menyusiga Mini App tugmasi, HTTPS URL konfiguratsiyasi.
3. **Foydalanuvchi funksiyalari**: sevimlilar, narx signallari, profil va inventar.
4. **Marketplace modeli**: seller/buyer, listing, order, escrow holatlari, komissiya va audit jurnali.
5. **Topshirish jarayoni**: faqat Steam trade offer yoki qo‘lda tasdiqlanadigan oqim; Steam paroli saqlanmaydi.
6. **To‘lov**: keyinroq litsenziyalangan to‘lov provayderi yoki Telegram Payments. Pul yechish, refund va nizolar qoidalari alohida yoziladi.
7. **Admin va test**: moderatsiya, fraud cheklovlari, holat mashinasi, avtomatlashtirilgan testlar.

## Savdo uchun rejalashtirilgan ma’lumot modeli
- `users`: Telegram foydalanuvchisi va roli (`buyer`, `seller`, `admin`)
- `listings`: sotuvdagi skin, narx, holat (`draft`, `active`, `reserved`, `sold`, `cancelled`)
- `orders`: xaridor, listing, summa, holat (`created`, `paid`, `awaiting_trade`, `delivered`, `disputed`, `refunded`)
- `payments`: provayder transaction ID, summa, valyuta, status
- `trades`: Steam trade offer ID, yuboruvchi/qabul qiluvchi, status
- `ledger`: komissiya, seller tushumi, refund va harakatlar
- `audit_log`: kim, qachon, qaysi holatni o‘zgartirdi

## Dizayn
- **Movement**: dark gaming marketplace / terminal-inspired dashboard.
- **Principles**: tezkor skan qilish, raqamlar birinchi o‘rinda, ixcham mobil UI, ishonchli holat belgilar.
- **Color philosophy**: grafit fon, sovuq ko‘k asosiy aksent, foydali narxlar uchun yashil, ogohlantirish uchun amber; CS2 estetikasini saqlagan holda ortiqcha neon ishlatilmaydi.
- **Layout**: mobil-first, sticky header va pastki navigatsiya; katalog kartalari, tafsilotda narx manbalari paneli.
- **Signature elements**: narx manbasi chip’lari, yashil “best price” belgisi, monospaced narxlar.
- **Interaction**: bir bosishda qidiruv, sevimliga qo‘shish, Telegram native close/back tugmalariga moslashuv.
- **Animation**: 150–220ms transition, loading skeleton, ortiqcha effektlarsiz.
- **Typography**: Inter/system sans-serif; narxlar uchun ui-monospace.
- **Brand essence**: O‘zbek CS2 o‘yinchilari uchun bozor narxini tez tekshirish va keyinchalik xavfsiz oldi-sotdi qilish joyi. Shaxsiyat: tezkor, shaffof, amaliy.
- **Voice**: qisqa, aniq, savdo xavflarini yashirmaydigan. Misol: “Eng past narxni ko‘ring.” / “Trade tasdiqlanmaguncha buyurtma yakunlanmaydi.”
- **Wordmark**: `CS2` blok belgisi + `MARKETUZ` monospaced wordmark.
- **Signature color**: `#55a7ff` sovuq ko‘k.

## Muhim xavfsizlik qarorlari
- Telegram `initData` server tomonda HMAC bilan tekshiriladi.
- Bot tokeni, Steam paroli va maxfiy API kalitlari frontendga chiqmaydi.
- Savdo holatlari faqat ruxsat etilgan transitionlar orqali o‘zgaradi.
- To‘lovni o‘zimiz “qabul qildik” deb belgilamaymiz; faqat provayder webhook’i asos bo‘ladi.
- Real pul bilan test qilinmaydi; avval sandbox/mock oqimi ishlatiladi.
