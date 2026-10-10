# CS2 Skin Narx Boti

Telegram bot: skin qidirish, Skinport va Steam narxlarini solishtirish, narx tushganda signal.

## Ishga tushirish
1. Telegramda @BotFather ga boring, `/newbot` orqali bot yarating va tokenni oling.
2. Python 3.10+ o'rnatilgan bo'lsin, so'ng:
   ```
   pip install -r requirements.txt
   cp .env.example .env      # tokenni .env ichiga yozing
   export $(cat .env | xargs)
   python bot.py
   ```
3. Botga `/start` yuboring va `ak-47 redline` deb yozib ko'ring.

## Doimiy ishlatish (VPS, systemd)
`/etc/systemd/system/cs2bot.service`:
```
[Unit]
Description=CS2 bot
After=network.target

[Service]
WorkingDirectory=/opt/cs2-bot
EnvironmentFile=/opt/cs2-bot/.env
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```
`sudo systemctl enable --now cs2bot`

## Eslatmalar
- Skinport narxlari har 5 daqiqada yangilanadi (API limiti uchun).
- Steam narxlari so'rov bo'yicha olinadi va 10 daqiqa keshlanadi; Steam tez-tez limit qo'yadi.
- Keyingi bosqich: kanal/obuna, ko'proq bozorlar (CSFloat, DMarket), so'ng marketplace.

## Mini App lokal test
Mini App API va interfeysini lokal ishga tushirish:
```bash
MINIAPP_DEV_MODE=1 MINIAPP_HOST=127.0.0.1 MINIAPP_PORT=8080 python api_server.py
```
So'ng brauzerda `http://127.0.0.1:8080/` manzilini oching. `MINIAPP_DEV_MODE=1` faqat lokal test uchun; productionda Telegram `initData` tekshiruvi majburiy bo'lishi kerak.

Bot menyusida Mini App tugmasini ko'rsatish uchun `.env` fayliga HTTPS manzil yozing:
```env
MINIAPP_URL=https://sizning-domeningiz.example/
```
Telegram Mini App uchun oddiy `http://` manzil qabul qilinmaydi; lokal testda yuqoridagi HTTPS preview URL'dan foydalanish mumkin.

Kelajakdagi savdo marketplace modeli `marketplace_schema.sql` faylida tayyorlangan. U listing, order, payment, trade, ledger va audit jadvallarini o'z ichiga oladi, lekin hozircha real to'lov yoki avtomatik trade bajarilmaydi.

## Bot va Mini App API'ni birga doimiy ishlatish
Lokal yoki o'zingizning doimiy kompyuteringizda ikkalasini birga ishga tushiring:
```bash
chmod +x run_all.sh
./run_all.sh
```
Bot `logs/bot.log`, API esa `logs/miniapp.log` fayliga yoziladi. Jarayonlardan biri to'xtasa, supervisor uni taxminan 3 soniyadan keyin qayta ishga tushiradi. To'xtatish: `Ctrl+C`.

VPS'da `cs2marketuz.service.example` faylini `/etc/systemd/system/cs2marketuz.service` nomi bilan joylab, `WorkingDirectory`, `EnvironmentFile` va `ExecStart` yo'llarini serverdagi haqiqiy loyiha papkasiga moslang:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cs2marketuz
sudo systemctl status cs2marketuz
sudo journalctl -u cs2marketuz -f
```
`MINIAPP_HOST=0.0.0.0` va haqiqiy HTTPS domen/reverse proxy production uchun kerak bo'ladi; `MINIAPP_DEV_MODE=0` bo'lishi shart.
