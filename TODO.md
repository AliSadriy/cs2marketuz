# CS2MarketUZ Mini App — TODO

- [x] **Mini App katalogi ishlashi** — foydalanuvchi Telegram ichida qidiruv paneli, kategoriyalar va skin kartalarini ko‘rsin; karta skin rasmi, nomi, eng past narx va narx manbasini ko‘rsatsin.
- [x] **Skin tafsilotlari ishlashi** — skin nomi, market narxlari, so‘mdagi taxminiy qiymat, 24 soatlik o‘zgarish va rasmiy market havolalari chiqsin.
- [x] **Telegram autentifikatsiyasi ishlashi** — API Telegram `initData` ni serverda tekshirsin; frontend foydalanuvchi ID sini o‘zi yuborib ishonmasin.
- [x] **Botdan Mini App ochilishi** — bot menyusida Mini App tugmasi bo‘lsin va URL konfiguratsiya orqali boshqarilsin.
- [x] **Sevimlilar ulanishi** — foydalanuvchi skinni Mini App’dan sevimliga qo‘sha/o‘chira olsin va bu mavjud SQLite jadvallarida saqlansin.
- [x] **Test rejimi mavjud bo‘lishi** — lokal testda Telegram initData bo‘lmasa, faqat demo foydalanuvchi bilan ishlasin; production rejimida imzosiz so‘rovlar rad etilsin.
- [x] **Marketplace ma’lumotlar modeli tayyor bo‘lishi** — listing, order, payment, trade, ledger va audit tushunchalari uchun migratsiyaga tayyor sxema yozilsin; real to‘lov ulanmasin.
- [ ] **Savdo holatlari xavfsiz bo‘lishi** — listing va order holatlari ruxsatsiz o‘zgarmasin; trade tasdiqlanmasdan buyurtma yakunlanmasin.
- [x] **Avtomatlashtirilgan tekshiruvlar** — Python compile, API health, auth validation va frontend asset mavjudligi tekshirilsin.
